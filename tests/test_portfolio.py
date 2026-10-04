from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
import math
import unittest

from roostoo_bot.portfolio import PairRules, Quote, balances, equity, next_order, strategy_targets, update_risk
from roostoo_bot.portfolio_backtest import research_settings


class PortfolioTests(unittest.TestCase):
    def setUp(self):
        self.settings = research_settings()
        self.quotes = {"BTC/USD": Quote(100, 100.1), "ETH/USD": Quote(10, 10.01)}
        self.rules = {"BTC/USD": PairRules(5, 1), "ETH/USD": PairRules(4, 1)}

    def test_cash_cap_includes_costs_reserve_and_locked_cash(self):
        wallet = balances({"USD": {"Free": 200, "Lock": 800}}, self.settings.pairs)
        intent = next_order(wallet, self.quotes, self.rules, {"BTC/USD": .35, "ETH/USD": .35}, replace(self.settings, min_trade_usd=1, rebalance_band=0))
        price = self.quotes[intent.pair].ask
        cost = float(intent.quantity) * price * (1 + self.settings.slippage_rate) * (1 + self.settings.fee_rate)
        self.assertLessEqual(cost, 190)
        self.assertGreater(cost, 189)

    def test_full_exit_ignores_band_and_local_minimum(self):
        wallet = balances({"USD": {"Free": 100000}, "BTC": {"Free": .02}}, self.settings.pairs)
        intent = next_order(wallet, self.quotes, self.rules, dict.fromkeys(self.settings.pairs, 0), self.settings)
        self.assertEqual(intent.side, "SELL")
        self.assertEqual(intent.quantity, "0.02000")

    def test_locked_position_is_valued_and_never_sold(self):
        wallet = balances({"USD": {"Free": 1000}, "BTC": {"Free": .1, "Lock": 2}}, self.settings.pairs)
        intent = next_order(wallet, self.quotes, self.rules, dict.fromkeys(self.settings.pairs, 0), self.settings)
        self.assertEqual(float(intent.quantity), .1)
        self.assertAlmostEqual(equity(wallet, self.quotes), 1000 + 2.1 * 100.05)

    def test_precision_and_exchange_minimum(self):
        self.assertEqual(self.rules["ETH/USD"].floor(.123456789), Decimal(".1234"))
        wallet = balances({"USD": {"Free": 1000}, "BTC": {"Free": .001}}, self.settings.pairs)
        self.assertIsNone(next_order(wallet, self.quotes, self.rules, dict.fromkeys(self.settings.pairs, 0), self.settings))

    def test_daily_stop_latches_but_rolls_at_hkt_midnight(self):
        ts = datetime(2026, 6, 1, 15, tzinfo=timezone.utc).timestamp()
        state = {}
        self.assertEqual(update_risk(state, 1000, ts, self.settings), "ok")
        self.assertEqual(update_risk(state, 960, ts + 60, self.settings), "daily_loss_limit")
        self.assertEqual(update_risk(state, 990, ts + 120, self.settings), "daily_loss_limit")
        self.assertEqual(update_risk(state, 990, ts + 3600, self.settings), "ok")

    def test_drawdown_stop_survives_new_day(self):
        state = {}
        update_risk(state, 1000, 1780000000, self.settings)
        self.assertEqual(update_risk(state, 900, 1780000300, self.settings), "drawdown_limit")
        self.assertEqual(update_risk(state, 1000, 1780086400, self.settings), "drawdown_limit")

    def test_buffered_trend_requires_entry_buffer_and_has_hysteresis(self):
        settings = replace(self.settings, strategy="buffered_trend", fast_window=1, slow_window=2, signal_buffer=.005)
        state = {}
        near = {p: [100, 100, 100.5] for p in settings.pairs}
        self.assertEqual(strategy_targets(near, state, settings, 1)["BTC/USD"], 0)
        up = {p: [100, 100, 102] for p in settings.pairs}
        self.assertEqual(strategy_targets(up, state, settings, 2)["BTC/USD"], .35)
        self.assertEqual(strategy_targets(near, state, settings, 3)["BTC/USD"], .35)

    def test_invalid_wallet_and_quote_fail_closed(self):
        with self.assertRaises(ValueError):
            Quote(math.nan, 100)
        with self.assertRaises(ValueError):
            Quote(101, 100)
        with self.assertRaises(ValueError):
            balances({"USD": {"Free": 100}, "DOGE": {"Free": 1}}, self.settings.pairs)

    def test_settings_reject_nonfinite_and_overallocation(self):
        with self.assertRaises(ValueError):
            replace(self.settings, max_asset_weight=.6)
        with self.assertRaises(ValueError):
            replace(self.settings, min_trade_usd=float("nan"))
