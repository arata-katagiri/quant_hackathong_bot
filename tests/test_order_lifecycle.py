"""Offline fault injection: simulate fills, locked cash, cancellation and restart."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from roostoo_bot.client import OrderOutcomeUnknown, OrderRejected
from roostoo_bot.engine import BotEngine
from roostoo_bot.portfolio_backtest import research_settings
from test_engine import FakeClient


class LifecycleClient(FakeClient):
    def __init__(self, now):
        super().__init__(now)
        self.first_mode = "PARTIAL"
        self.reports = {}
        self.reserved_cash = {}

    def _fill(self, report, quantity):
        coin, side = report["Pair"].split("/")[0], report["Side"]
        if side == "BUY":
            self.wallet["USD"]["Free"] -= quantity * self.price * 1.001
            self.wallet[coin]["Free"] += quantity
        else:
            assert quantity <= self.wallet[coin]["Free"] + 1e-10
            self.wallet["USD"]["Free"] += quantity * self.price * .999
            self.wallet[coin]["Free"] -= quantity
        assert self.wallet["USD"]["Free"] >= -1e-7
        report["FilledQuantity"] += quantity
        report["FilledAverPrice"] = self.price if report["FilledQuantity"] else 0

    def place_market_order(self, pair, side, quantity):
        self.orders.append((pair, side, quantity))
        identifier = str(len(self.orders))
        mode = self.first_mode if identifier == "1" else "FILLED"
        if mode == "REJECTED":
            raise OrderRejected("fixture explicit rejection")
        report = dict(OrderID=identifier, Pair=pair, Side=side, Quantity=float(quantity),
                      FilledQuantity=0.0, FilledAverPrice=0.0, Status="PENDING")
        self.reports[identifier] = report
        if mode == "PARTIAL":
            assert side == "BUY"
            self._fill(report, float(quantity) / 2)
            report["Status"] = "PARTIALLY_FILLED"
            reserve = (float(quantity) - report["FilledQuantity"]) * self.price * 1.001
            self.wallet["USD"]["Free"] -= reserve
            self.wallet["USD"]["Lock"] += reserve
            self.reserved_cash[identifier] = reserve
        else:
            self._fill(report, float(quantity))
            report["Status"] = "FILLED"
            if mode == "ACCEPTED_RESPONSE_LOST":
                raise OrderOutcomeUnknown("fixture accepted order, lost response")
        return {"OrderDetail": deepcopy(report)}

    def settle(self, identifier, status):
        report = self.reports[identifier]
        reserve = self.reserved_cash.pop(identifier, 0)
        self.wallet["USD"]["Free"] += reserve
        self.wallet["USD"]["Lock"] -= reserve
        if status == "FILLED":
            self._fill(report, report["Quantity"] - report["FilledQuantity"])
        report["Status"] = status

    def pending_count(self):
        return {"TotalPending": sum(r["Status"] in {"PENDING", "PARTIALLY_FILLED"} for r in self.reports.values())}

    def query_order(self, order_id):
        return {"OrderMatched": [deepcopy(self.reports[order_id])]}


class OrderLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.now = [1790812800.0]
        self.settings = research_settings(data_dir=Path(self.directory.name), fast_window=1, slow_window=2,
                                          dry_run=False, live_trading_enabled=True)
        self.client = LifecycleClient(self.now)
        self.history = [100, 110, 120]

    def tearDown(self):
        self.directory.cleanup()

    def engine(self):
        return BotEngine(self.client, self.settings, clock=lambda: self.now[0],
                         market_data=lambda pairs, *_: {p: list(self.history) for p in pairs})

    def test_partial_buy_locks_cash_blocks_restart_then_cancellation_sells_only_acquired(self):
        self.assertEqual(self.engine().run_once(), "blocked")
        acquired = self.client.wallet["BTC"]["Free"]
        self.assertGreater(acquired, 0)
        self.assertGreater(self.client.wallet["USD"]["Lock"], 0)
        self.now[0] += 300
        self.assertEqual(self.engine().run_once(), "blocked")
        self.assertEqual(len(self.client.orders), 1)
        self.client.settle("1", "CANCELED")
        self.history = [120, 110, 100]  # changed signal exits the actual partial position
        self.now[0] += 300
        engine = self.engine()
        self.assertEqual(engine.run_once(), "ok")
        self.assertEqual([(p, s) for p, s, _ in self.client.orders], [("BTC/USD", "BUY"), ("BTC/USD", "SELL")])
        self.assertAlmostEqual(float(self.client.orders[1][2]), acquired, places=5)
        self.assertLess(self.client.wallet["BTC"]["Free"], 1e-5)
        self.assertEqual(self.client.wallet["USD"]["Lock"], 0)
        self.assertNotIn("inflight", engine.store.load())

    def test_partial_then_full_after_restart_uses_wallet_without_duplicate_btc_buy(self):
        self.engine().run_once()
        self.client.settle("1", "FILLED")
        self.now[0] += 300
        self.assertEqual(self.engine().run_once(), "ok")
        self.assertEqual([(p, s) for p, s, _ in self.client.orders], [("BTC/USD", "BUY"), ("ETH/USD", "BUY")])
        self.assertGreater(self.client.wallet["USD"]["Free"], 29000)
        self.assertEqual(self.client.wallet["USD"]["Lock"], 0)

    def test_accepted_order_with_lost_response_blocks_even_when_balance_has_changed(self):
        self.client.first_mode = "ACCEPTED_RESPONSE_LOST"
        with self.assertRaises(OrderOutcomeUnknown):
            self.engine().run_once()
        self.assertGreater(self.client.wallet["BTC"]["Free"], 0)
        self.now[0] += 300
        self.assertEqual(self.engine().run_once(), "blocked")
        self.assertEqual(len(self.client.orders), 1)
        self.assertNotIn("order_id", self.engine().store.load()["inflight"])

    def test_explicit_rejection_does_not_invent_fills_or_retry_same_bucket(self):
        self.client.first_mode = "REJECTED"
        self.assertEqual(self.engine().run_once(), "blocked")
        self.assertEqual(self.client.wallet["USD"]["Free"], 100000)
        self.assertEqual(self.client.wallet["BTC"]["Free"], 0)
        self.assertNotIn("inflight", self.engine().store.load())
        self.assertEqual(self.engine().run_once(), "held")
        self.assertEqual(len(self.client.orders), 1)

    def test_decreasing_cumulative_fill_cannot_clear_saved_order_after_restart(self):
        self.engine().run_once()
        self.client.settle("1", "CANCELED")
        self.client.reports["1"]["FilledQuantity"] = 0  # stale/contradictory terminal report
        self.now[0] += 300
        with self.assertRaisesRegex(ValueError, "decreased"):
            self.engine().run_once()
        self.assertIn("inflight", self.engine().store.load())
        self.assertEqual(len(self.client.orders), 1)

    def test_missing_fill_quantity_cannot_clear_saved_order_after_restart(self):
        self.engine().run_once()
        self.client.settle("1", "CANCELED")
        self.client.reports["1"].pop("FilledQuantity")
        self.now[0] += 300
        with self.assertRaisesRegex(ValueError, "missing FilledQuantity"):
            self.engine().run_once()
        self.assertIn("inflight", self.engine().store.load())
        self.assertEqual(len(self.client.orders), 1)

    def test_log_failure_cannot_erase_validated_fill_progress(self):
        engine = self.engine()
        for status, filled in (("PARTIALLY_FILLED", .5), ("FILLED", 1.0)):
            with self.subTest(status=status):
                state = {"version": 2, "inflight": {"order_id": "1", "pair": "BTC/USD", "side": "BUY", "quantity": "1"}}
                engine.store.save(state)
                detail = dict(OrderID="1", Pair="BTC/USD", Side="BUY", Quantity=1,
                              FilledQuantity=filled, FilledAverPrice=120, Status=status)
                with patch("roostoo_bot.engine.event", side_effect=OSError("fixture logging failure")):
                    with self.assertRaises(OSError):
                        engine._detail(state, detail)
                saved = engine.store.load()["inflight"]
                self.assertEqual(saved["filled_quantity_seen"], filled)
