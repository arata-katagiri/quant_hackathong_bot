from copy import deepcopy
from dataclasses import replace
import tempfile
from pathlib import Path
import unittest

from roostoo_bot.client import OrderOutcomeUnknown
from roostoo_bot.engine import BotEngine
from roostoo_bot.portfolio_backtest import research_settings


class FakeClient:
    def __init__(self, now):
        self.now = now
        self.orders = []
        self.pending = 0
        self.outcome = "FILLED"
        self.stale = False
        self.price = 120
        self.wallet = {"USD": {"Free": 100000, "Lock": 0}, "BTC": {"Free": 0, "Lock": 0}, "ETH": {"Free": 0, "Lock": 0}}

    def ticker(self):
        return {"ServerTime": (self.now[0] - (100 if self.stale else 0)) * 1000, "Data": {p: {"MaxBid": self.price, "MinAsk": self.price} for p in ("BTC/USD", "ETH/USD")}}

    def exchange_info(self):
        return {"IsRunning": True, "TradePairs": {p: {"AmountPrecision": 5 if p == "BTC/USD" else 4, "MiniOrder": 1, "CanTrade": True} for p in ("BTC/USD", "ETH/USD")}}

    def balance(self):
        return {"Wallet": deepcopy(self.wallet)}

    def pending_count(self):
        return {"TotalPending": self.pending}

    def place_market_order(self, pair, side, quantity):
        self.orders.append((pair, side, quantity))
        if self.outcome == "UNKNOWN":
            raise OrderOutcomeUnknown("simulated lost response")
        qty = float(quantity)
        if self.outcome == "FILLED":
            self.wallet["USD"]["Free"] += qty * self.price * (-1.001 if side == "BUY" else .999)
            self.wallet[pair.split("/")[0]]["Free"] += qty * (1 if side == "BUY" else -1)
        return {"OrderDetail": {"OrderID": len(self.orders), "Pair": pair, "Side": side, "Quantity": qty, "FilledQuantity": qty if self.outcome == "FILLED" else qty / 2, "FilledAverPrice": self.price, "Status": self.outcome}}

    def query_order(self, order_id):
        pair, side, qty = self.orders[int(order_id) - 1]
        return {"OrderMatched": [{"OrderID": int(order_id), "Pair": pair, "Side": side, "Quantity": float(qty), "FilledQuantity": float(qty) / 2, "FilledAverPrice": self.price, "Status": "PARTIALLY_FILLED"}]}


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.now = [1790812800.0]
        self.settings = research_settings(data_dir=Path(self.temporary.name), fast_window=1, slow_window=2, signal_source="roostoo")
        self.client = FakeClient(self.now)

    def tearDown(self):
        self.temporary.cleanup()

    def engine(self, live=False):
        settings = replace(self.settings, dry_run=not live, live_trading_enabled=live)
        engine = BotEngine(self.client, settings, clock=lambda: self.now[0])
        return engine

    def warm(self, engine):
        engine.store.save({"version": 2, "prices": {p: [100, 110] for p in self.settings.pairs}, "history_bar": int(self.now[0] // 300) - 1, "risk": {}})

    def test_dry_run_never_calls_submit_and_same_bar_is_idempotent(self):
        engine = self.engine()
        self.warm(engine)
        self.assertEqual(engine.run_once(), "ok")
        self.assertEqual(engine.run_once(), "held")
        self.assertEqual(self.client.orders, [])

    def test_unknown_submit_blocks_after_restart(self):
        engine = self.engine(live=True)  # pure fake client, no network or real credentials
        self.warm(engine)
        self.client.outcome = "UNKNOWN"
        with self.assertRaises(OrderOutcomeUnknown):
            engine.run_once()
        self.assertIn("inflight", engine.store.load())
        self.now[0] += 300
        self.assertEqual(self.engine(live=True).run_once(), "blocked")
        self.assertEqual(len(self.client.orders), 1)

    def test_partial_fill_prevents_more_orders_until_terminal(self):
        engine = self.engine(live=True)
        self.warm(engine)
        self.client.outcome = "PARTIALLY_FILLED"
        self.assertEqual(engine.run_once(), "blocked")
        self.now[0] += 300
        self.assertEqual(self.engine(live=True).run_once(), "blocked")
        self.assertEqual(len(self.client.orders), 1)

    def test_existing_pending_orders_block(self):
        engine = self.engine(live=True)
        self.warm(engine)
        self.client.pending = 1
        self.assertEqual(engine.run_once(), "blocked")
        self.assertFalse(self.client.orders)

    def test_incomplete_fill_report_keeps_order_unresolved(self):
        engine = self.engine(live=True)
        state = {"version": 2, "inflight": {"order_id": "1", "pair": "BTC/USD", "side": "BUY", "quantity": "1"}}
        engine.store.save(state)
        detail = {"OrderID": 1, "Pair": "BTC/USD", "Side": "BUY", "Quantity": 1, "FilledQuantity": 1, "Status": "FILLED"}
        with self.assertRaisesRegex(ValueError, "fill price"):
            engine._detail(state, detail)
        self.assertIn("inflight", engine.store.load())

    def test_stale_quote_does_not_advance_state_or_trade(self):
        engine = self.engine(live=True)
        self.warm(engine)
        self.client.stale = True
        with self.assertRaises(ValueError):
            engine.run_once()
        self.assertNotIn("last_bar", engine.store.load())
        self.assertFalse(self.client.orders)

    def test_history_gap_restarts_warmup(self):
        engine = self.engine()
        self.warm(engine)
        self.now[0] += 600
        self.assertEqual(engine.run_once(), "held")
        self.assertEqual(len(engine.store.load()["prices"]["BTC/USD"]), 1)

    def test_live_simulated_fills_refresh_cash_for_second_asset(self):
        engine = self.engine(live=True)
        self.warm(engine)
        engine.run_once()
        self.assertEqual(len(self.client.orders), 2)
        self.assertGreater(self.client.wallet["USD"]["Free"], 29000)
        self.assertNotIn("inflight", engine.store.load())

    def test_concurrent_engine_lock(self):
        first, second = self.engine(), self.engine()
        with first.store.lock():
            with self.assertRaises(RuntimeError):
                second.run_once()

    def test_closed_history_bootstraps_without_waiting_for_new_samples(self):
        settings = replace(self.settings, signal_source="binance")
        history = lambda *args: {p:[100, 110, 120] for p in self.settings.pairs}
        engine = BotEngine(self.client, settings, clock=lambda:self.now[0], market_data=history)
        self.assertEqual(engine.run_once(), "ok")
        self.assertFalse(self.client.orders)
        self.assertEqual(len(engine.store.load()["prices"]["BTC/USD"]), 3)

    def test_candle_feed_failure_blocks_strategy_but_allows_risk_exit(self):
        from roostoo_bot.market_data import MarketDataError
        calls = []
        def unavailable(*args):
            calls.append(args)
            raise MarketDataError("fixture outage")
        settings = replace(self.settings, signal_source="binance", dry_run=False, live_trading_enabled=True)
        engine = BotEngine(self.client, settings, clock=lambda:self.now[0], market_data=unavailable)
        self.assertEqual(engine.run_once(), "blocked")
        state = engine.store.load()
        state["risk"]["drawdown_halted"] = True
        engine.store.save(state)
        self.client.wallet["BTC"]["Free"] = 1
        self.now[0] += 300
        self.assertEqual(engine.run_once(), "ok")
        self.assertEqual(self.client.orders[0][1], "SELL")
        self.assertEqual(len(calls), 1)  # a latched risk exit never waits on signal data

    def test_simulator_order_sequence_matches_engine_with_next_open_equal_to_prior_close(self):
        from roostoo_bot.backtest import Candle
        from roostoo_bot.portfolio_backtest import BAR_US, simulate_portfolio
        self.settings = replace(self.settings, slippage_rate=0)
        engine = self.engine(live=True)
        start = int(self.now[0] * 1e6)
        closes = [100, 102, 104, 106, 108, 105, 102, 100, 103, 106, 109, 110]
        candles = [Candle(start + i * BAR_US, closes[max(0, i - 1)], close) for i, close in enumerate(closes)]
        _, _, simulated = simulate_portfolio({p:candles for p in self.settings.pairs}, self.settings, liquidate=False)
        for i, price in enumerate(closes[:-1]):
            self.now[0] = start / 1e6 + (i + 1) * 300
            self.client.price = price
            engine.run_once()
        actual = [(p, s, float(q)) for p,s,q in self.client.orders]
        expected = [(t["pair"],t["side"],t["quantity"]) for t in simulated]
        self.assertEqual(actual, expected)

    def test_candle_engine_matches_fresh_portfolio_start_and_risk_state(self):
        from roostoo_bot.backtest import Candle
        from roostoo_bot.portfolio_backtest import BAR_US, simulate_portfolio
        start = int(self.now[0] * 1e6)
        closes = [100 + (i % 30) * .2 for i in range(350)]
        rows = [Candle(start+i*BAR_US, closes[max(0,i-1)], close) for i,close in enumerate(closes)]
        for strategy in ("baseline", "buffered_trend", "breakout"):
            with self.subTest(strategy=strategy), tempfile.TemporaryDirectory() as directory:
                self.client = FakeClient(self.now)
                settings = replace(self.settings, strategy=strategy, fast_window=2, slow_window=6,
                                   signal_source="binance", data_dir=Path(directory), slippage_rate=0,
                                   dry_run=False, live_trading_enabled=True)
                data = {p:rows for p in settings.pairs}
                _, _, simulated = simulate_portfolio(data, settings, start_index=10, liquidate=False)
                def observed(pairs, count, boundary):
                    index = int((boundary * 1e6 - start) // BAR_US)
                    return {p:closes[max(0,index-count):index] for p in pairs}
                engine = BotEngine(self.client, settings, clock=lambda:self.now[0], market_data=observed)
                for index in range(10, len(rows)):
                    self.now[0] = rows[index].open_time_us / 1e6
                    self.client.price = rows[index].open
                    engine.run_once()
                actual = [(p,s,float(q)) for p,s,q in self.client.orders]
                expected = [(t["pair"],t["side"],t["quantity"]) for t in simulated]
                self.assertEqual(actual, expected)
