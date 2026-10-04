from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from roostoo_bot.client import OrderOutcomeUnknown
from roostoo_bot.execution_probe import ExecutionProbe
from roostoo_bot.portfolio_backtest import research_settings


class ProbeClient:
    api_key = "offline"
    def __init__(self):
        self.now = 1790829600
        self.cash, self.btc = 50000.0, 0.0
        self.orders, self.calls, self.canceled = {}, [], []
        self.buy_mode, self.unknown_side = "FILLED", None

    def balance(self):
        return {"Wallet":{"USD":{"Free":self.cash},"BTC":{"Free":self.btc}}}

    def pending_count(self):
        return {"TotalPending":sum(r["Status"] not in {"FILLED","CANCELED"} for r in self.orders.values())}

    def exchange_info(self):
        return {"IsRunning":True,"TradePairs":{"BTC/USD":{"CanTrade":True,"PricePrecision":2,"AmountPrecision":5,"MiniOrder":1}}}

    def ticker(self, pair):
        return {"ServerTime":self.now*1000,"Data":{pair:{"MaxBid":100000,"MinAsk":100000}}}

    def place_limit_order(self, pair, side, quantity, price):
        self.calls.append((side,quantity,price))
        if self.unknown_side == side:
            raise OrderOutcomeUnknown("fixture response loss")
        filled = float(quantity) * ({"FILLED":1,"PARTIALLY_FILLED":.5,"PENDING":0}[self.buy_mode])
        self.btc += filled
        self.cash -= filled*100000*1.001
        return self.record(pair,side,quantity,filled,self.buy_mode)

    def place_market_order(self, pair, side, quantity):
        self.calls.append((side,quantity,None))
        if self.unknown_side == side:
            raise OrderOutcomeUnknown("fixture response loss")
        filled = float(quantity)
        assert filled <= self.btc + 1e-12
        self.btc -= filled
        self.cash += filled*100000*.999
        return self.record(pair,side,quantity,filled,"FILLED")

    def record(self, pair, side, quantity, filled, status):
        identifier = str(len(self.calls))
        detail = {"OrderID":identifier,"Pair":pair,"Side":side,"Quantity":float(quantity),"FilledQuantity":filled,
                  "FilledAverPrice":100000 if filled else 0,"Status":status,"CommissionCoin":"USD",
                  "CommissionChargeValue":filled*100,"CommissionPercent":.001}
        self.orders[identifier] = detail
        return {"OrderDetail":deepcopy(detail)}

    def query_order(self, order_id):
        return {"OrderMatched":[deepcopy(self.orders[order_id])]}

    def cancel_order(self, order_id):
        self.canceled.append(order_id)
        self.orders[order_id]["Status"] = "CANCELED"
        return {"CanceledList":[order_id]}


class ExecutionProbeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.settings = research_settings(data_dir=Path(self.directory.name))
        self.client = ProbeClient()

    def tearDown(self):
        self.directory.cleanup()

    def probe(self):
        return ExecutionProbe(self.client,self.settings,approved=True,clock=lambda:self.client.now)

    def test_explicit_approval_is_required(self):
        with self.assertRaises(ValueError):
            ExecutionProbe(self.client,self.settings,approved=False)
        self.assertFalse(self.client.calls)

    def test_one_capped_buy_and_acquired_only_sale_then_idempotent_finish(self):
        result = self.probe().run()
        self.assertEqual([r[0] for r in self.client.calls],["BUY","SELL"])
        self.assertLessEqual(float(self.client.calls[0][1])*float(self.client.calls[0][2]),9)
        self.assertEqual(result["bought_btc"],result["sold_btc"])
        self.assertAlmostEqual(result["remaining_btc"],0)
        self.assertEqual(self.probe().run(),result)
        self.assertEqual(len(self.client.calls),2)

    def test_unknown_buy_response_never_retries_after_restart(self):
        self.client.unknown_side = "BUY"
        with self.assertRaises(OrderOutcomeUnknown):
            self.probe().run()
        with self.assertRaisesRegex(ValueError,"never resubmit"):
            self.probe().run()
        self.assertEqual(len(self.client.calls),1)

    def test_unknown_sell_never_repeats_either_leg(self):
        self.client.unknown_side = "SELL"
        with self.assertRaises(OrderOutcomeUnknown):
            self.probe().run()
        with self.assertRaisesRegex(ValueError,"never resubmit"):
            self.probe().run()
        self.assertEqual(len(self.client.calls),2)

    def test_partial_buy_is_canceled_and_only_its_fill_is_sold(self):
        self.client.buy_mode = "PARTIALLY_FILLED"
        result = self.probe().run()
        self.assertEqual(self.client.canceled,["1"])
        self.assertEqual(float(self.client.calls[1][1]),float(self.client.calls[0][1])*.5)
        self.assertAlmostEqual(result["remaining_btc"],0)

    def test_unfilled_buy_is_canceled_without_extra_orders(self):
        self.client.buy_mode = "PENDING"
        result = self.probe().run()
        self.assertEqual(self.client.canceled,["1"])
        self.assertEqual(len(self.client.calls),1)
        self.assertIsNone(result["sell"])

    def test_existing_btc_blocks_probe_without_submission(self):
        self.client.btc = .0001
        with self.assertRaisesRegex(ValueError,"no initial BTC"):
            self.probe().run()
        self.assertFalse(self.client.calls)

    def test_stale_terminal_report_cannot_erase_a_previous_partial_fill(self):
        probe = self.probe()
        state = {"version": 2, "buy": {"order_id": "1", "quantity": "0.00008", "price": "100100"}}
        detail = dict(OrderID="1", Pair="BTC/USD", Side="BUY", Quantity=.00008,
                      FilledQuantity=.00004, FilledAverPrice=100000, Status="PARTIALLY_FILLED")
        probe.record(state, "buy", detail)
        restored = self.probe().store.load()
        with self.assertRaisesRegex(ValueError, "decreased"):
            self.probe().record(restored, "buy", dict(detail, FilledQuantity=0, Status="CANCELED"))
        self.assertEqual(self.probe().store.load()["buy"]["detail"]["filled_quantity"], .00004)
        self.assertFalse(self.client.calls)
