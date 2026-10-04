from dataclasses import replace
import tempfile
from pathlib import Path
import unittest

from roostoo_bot.backtest import Candle
from roostoo_bot.engine import BotEngine
from roostoo_bot.portfolio import strategy_targets
from roostoo_bot.portfolio_backtest import BAR_US, research_settings, simulate_portfolio
from test_engine import FakeClient
from roostoo_bot.pullback_research import PERIODS, assess


class PullbackTests(unittest.TestCase):
    def setUp(self):
        self.settings = research_settings(strategy="pullback", fast_window=4, slow_window=12)
        self.prior = [90] * 8 + [100, 100.2, 99.8, 100]

    def signal(self, price, state, bar=12, prior=None):
        return strategy_targets({p:(prior or self.prior) + [price] for p in self.settings.pairs}, state, self.settings, bar)["BTC/USD"]

    def test_entry_requires_pullback_trend_and_cost_hurdle(self):
        self.assertEqual(self.signal(99, {}), .35)
        self.assertEqual(self.signal(99.7, {}), 0)  # insufficient distance after costs
        self.assertEqual(self.signal(99, {}, prior=[110]*8+self.prior[-4:]), 0)

    def test_recovery_target_is_frozen_and_exit_does_not_reenter(self):
        state = {}
        self.signal(99, state)
        self.assertEqual(state["pullback_entries"]["BTC/USD"]["target"], 100)
        self.assertEqual(self.signal(99.5, state, 13), .35)
        self.assertEqual(self.signal(100, state, 14), 0)
        self.assertNotIn("BTC/USD", state["pullback_entries"])

    def test_time_and_trend_exit(self):
        state = {}
        self.signal(99, state)
        self.assertEqual(self.signal(99, state, 16), 0)
        self.assertEqual(self.signal(99, state, 17), .35)
        self.assertEqual(self.signal(89, state, 18), 0)

    def test_research_configuration_decides_only_every_fifteen_minutes(self):
        settings = replace(self.settings, decision_every_bars=3)
        history = {p:self.prior+[99] for p in settings.pairs}
        self.assertIsNone(strategy_targets(history, {}, settings, 13))
        self.assertEqual(strategy_targets(history, {}, settings, 15)["BTC/USD"], .35)

    def test_closed_candle_engine_and_simulator_execute_same_orders(self):
        with tempfile.TemporaryDirectory() as directory:
            now = [1790812800.0]
            start = int(now[0] * 1e6)
            closes = self.prior + [99, 99.5, 100.5, 100, 100, 100]
            rows = [Candle(start+i*BAR_US, closes[max(0,i-1)], close) for i,close in enumerate(closes)]
            settings = replace(self.settings, signal_source="binance", data_dir=Path(directory), slippage_rate=0,
                               dry_run=False, live_trading_enabled=True)
            data = {p:rows for p in settings.pairs}
            _, _, expected = simulate_portfolio(data, settings, start_index=13, liquidate=False)
            self.assertGreaterEqual(len(expected), 4)
            def observed(pairs, count, boundary):
                index = int((boundary * 1e6 - start) // BAR_US)
                return {p:closes[max(0,index-count):index] for p in pairs}
            client = FakeClient(now)
            engine = BotEngine(client, settings, clock=lambda:now[0], market_data=observed)
            for index in range(13, len(rows)):
                now[0] = rows[index].open_time_us / 1e6
                client.price = rows[index].open
                engine.run_once()
            self.assertEqual([(p,s,float(q)) for p,s,q in client.orders],
                             [(t["pair"],t["side"],t["quantity"]) for t in expected])

    def test_future_perturbation_cannot_change_earlier_pullback_fills(self):
        start = 1790812800000000
        prices = self.prior + [99, 99.5, 100.5, 100, 100, 100]
        rows = [Candle(start+i*BAR_US, price, price) for i,price in enumerate(prices)]
        data = {p:rows for p in self.settings.pairs}
        _, _, original = simulate_portfolio(data, self.settings)
        changed = rows[:16] + [Candle(start+i*BAR_US, 10000, 10000) for i in range(16,len(rows))]
        _, _, perturbed = simulate_portfolio({p:changed for p in self.settings.pairs}, self.settings)
        before = lambda trades:[t for t in trades if t["timestamp_us"] < start+16*BAR_US]
        self.assertTrue(before(original))
        self.assertEqual(before(original), before(perturbed))

    def test_missing_or_duplicate_results_cannot_pass_research_gate(self):
        with self.assertRaises(ValueError):
            assess([])

    def test_research_gate_rejects_losing_month_or_insufficient_activity(self):
        rows = [dict(strategy="pullback",period=p,cost=c,total_return=.01,max_drawdown=.02,active_days_utc=9)
                for p,_,_ in PERIODS for c in ("base","stress")]
        self.assertTrue(assess(rows)["advance_to_sealed_holdout"])
        self.assertFalse(assess(rows)["strategy_approved_for_live"])
        rows[1]["total_return"] = -.001
        self.assertFalse(assess(rows)["advance_to_sealed_holdout"])
        rows[1]["total_return"] = .01
        for row in rows[4:]:
            row["active_days_utc"] = 7
        self.assertFalse(assess(rows)["advance_to_sealed_holdout"])
