from copy import deepcopy
import unittest

from roostoo_bot.attribution import attribute


class AttributionTests(unittest.TestCase):
    def setUp(self):
        self.trades = [dict(pair="BTC/USD",side="BUY",quantity=2,price=101,notional=202,fee=2),
                       dict(pair="BTC/USD",side="SELL",quantity=2,price=108.9,notional=217.8,fee=2.5)]
        self.summary = dict(initial_equity=1000,final_equity=1011.3,fees=4.5)

    def test_fixed_fill_decomposition_reconciles_exactly(self):
        result = attribute(self.summary,self.trades,.01)
        self.assertAlmostEqual(result["same_trades_price_pnl"],20)
        self.assertAlmostEqual(result["modeled_slippage"],4.2)
        self.assertAlmostEqual(result["fees"],4.5)
        self.assertAlmostEqual(result["net_pnl"],11.3)

    def test_open_positions_cannot_be_mistaken_for_losses(self):
        with self.assertRaisesRegex(ValueError,"liquidated"):
            attribute(self.summary,self.trades[:1],.01)

    def test_corrupt_notional_or_equity_is_rejected(self):
        bad = deepcopy(self.trades)
        bad[0]["notional"] = 201
        with self.assertRaisesRegex(ValueError,"notional"):
            attribute(self.summary,bad,.01)
        with self.assertRaisesRegex(ValueError,"final equity"):
            attribute(dict(self.summary,final_equity=1100),self.trades,.01)

    def test_cash_is_zero_for_every_component(self):
        result = attribute(dict(initial_equity=1000,final_equity=1000,fees=0),[],.0015)
        for field in ("same_trades_price_pnl","modeled_slippage","fees","net_pnl"):
            self.assertEqual(result[field],0)
