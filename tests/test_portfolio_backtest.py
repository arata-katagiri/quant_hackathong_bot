from dataclasses import replace
import unittest
from roostoo_bot.backtest import Candle
from roostoo_bot.portfolio_backtest import BAR_US, research_settings, simulate_portfolio

START = 1780272000000000


def candles(prices):
    return [Candle(START + i * BAR_US, price, price) for i, price in enumerate(prices)]


class PortfolioBacktestTests(unittest.TestCase):
    def setUp(self):
        self.settings = research_settings(fast_window=1, slow_window=2)
        self.data = {p: candles([100 + i for i in range(50)]) for p in self.settings.pairs}

    def test_two_assets_share_one_cash_account(self):
        result, curve, trades = simulate_portfolio(self.data, self.settings, liquidate=False)
        self.assertGreater(result["trades"], 1)
        self.assertGreaterEqual(min(p["cash"] for p in curve), 0)
        self.assertLessEqual(max(p["exposure"] for p in curve), .78)
        self.assertEqual(trades[0]["timestamp_us"], START + 3 * BAR_US)

    def test_future_prices_cannot_change_earlier_orders(self):
        _, _, original = simulate_portfolio(self.data, self.settings)
        changed = {p: rows[:25] + candles([10000] * 25) for p, rows in self.data.items()}
        for pair in changed:
            changed[pair][25:] = [Candle(START + i * BAR_US, 10000, 10000) for i in range(25, 50)]
        _, _, perturbed = simulate_portfolio(changed, self.settings)
        before = lambda rows: [t for t in rows if t["timestamp_us"] < START + 25 * BAR_US]
        self.assertEqual(before(original), before(perturbed))

    def test_costs_and_end_liquidation_are_charged(self):
        cost, _, _ = simulate_portfolio(self.data, self.settings, benchmark="buy_hold_50")
        free, _, _ = simulate_portfolio(self.data, replace(self.settings, fee_rate=0, slippage_rate=0), benchmark="buy_hold_50")
        self.assertLess(cost["final_equity"], free["final_equity"])
        self.assertEqual(cost["forced_liquidations"], 2)
        self.assertEqual(cost["trades"], 2)
        self.assertEqual(cost["active_days_hkt"], 1)

    def test_timestamp_mismatch_is_rejected(self):
        self.data["ETH/USD"][10] = Candle(START + 11 * BAR_US, 100, 100)
        with self.assertRaises(ValueError):
            simulate_portfolio(self.data, self.settings)

    def test_risk_stop_liquidates_and_latches(self):
        data = {p: candles([100, 101, 102, 103, 104, 80] + [110] * 30) for p in self.settings.pairs}
        result, _, trades = simulate_portfolio(data, self.settings)
        self.assertTrue(result["drawdown_halted"])
        self.assertTrue(any(t["reason"] == "drawdown_limit" and t["side"] == "SELL" for t in trades))
        first_stop = min(t["timestamp_us"] for t in trades if t["reason"] == "drawdown_limit")
        self.assertFalse(any(t["side"] == "BUY" and t["timestamp_us"] > first_stop for t in trades))

    def test_cash_has_zero_return_and_undefined_ratios(self):
        result, _, trades = simulate_portfolio(self.data, self.settings, benchmark="cash")
        self.assertEqual(result["total_return"], 0)
        self.assertIsNone(result["sharpe_daily"])
        self.assertFalse(trades)

    def test_warmup_does_not_inherit_hypothetical_active_signal(self):
        settings = replace(self.settings, strategy="buffered_trend", fast_window=2, slow_window=4)
        # Earlier momentum would have switched on hysteresis, but a new engine
        # starts flat and the latest ratio is below its entry buffer.
        prices = [100, 100, 100, 100, 102, 103, 103, 103.1, 103.1, 103.1, 103.1]
        data = {p:candles(prices) for p in settings.pairs}
        _, _, trades = simulate_portfolio(data, settings, start_index=8, liquidate=False)
        self.assertFalse(trades)
