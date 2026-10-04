from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from roostoo_bot.backtest import Candle
from roostoo_bot.basket_research import PAIRS, RULES
from roostoo_bot.engine import BotEngine
from roostoo_bot.portfolio import strategy_targets
from roostoo_bot.portfolio_backtest import BAR_US, simulate_portfolio
from roostoo_bot.vol_momentum import LOOKBACK, allocation
from roostoo_bot.vol_research import PLAN_SHA256, STRATEGIES, assess, main, periods, settings


class VolatilityMomentumTests(unittest.TestCase):
    def test_flat_market_is_cash_but_volatility_control_is_invested(self):
        prices = [100.0] * (LOOKBACK + 1)
        row = allocation(prices, .14)
        self.assertEqual(row["target_weight"], 0)
        self.assertEqual(row["daily_volatility"], .005)
        self.assertEqual(allocation(prices, .14, timing=False)["target_weight"], .14)

    def test_rising_and_falling_trends_are_long_only_and_capped(self):
        for slope, expected in ((.00001, .14), (-.00001, 0)):
            prices = [100 * math.exp(slope * i) for i in range(LOOKBACK + 1)]
            self.assertAlmostEqual(allocation(prices, .14)["target_weight"], expected)

    def test_continuous_forecast_matches_hand_calculation(self):
        prices = [100.0] * LOOKBACK + [100.2]
        expected_score = sum(math.log(1.002) / (.005 * math.sqrt(d)) for d in (1, 3, 7)) / 3
        self.assertAlmostEqual(allocation(prices, .14)["target_weight"], .14 * expected_score)

    def test_volatile_market_reduces_risk_allocation(self):
        prices = [100 * math.exp(.03 if (i // 12) % 2 else 0) for i in range(LOOKBACK + 1)]
        row = allocation(prices, .14, timing=False)
        self.assertGreater(row["daily_volatility"], .02)
        self.assertAlmostEqual(row["target_weight"], .14 * .02 / row["daily_volatility"])

    def test_price_scale_and_older_prefix_do_not_change_forecast(self):
        prices = [100 * math.exp(.000003 * i) for i in range(LOOKBACK + 1)]
        expected = allocation(prices, .14)
        for changed in ([5, 10] + prices, [p * 99 for p in prices]):
            actual = allocation(changed, .14)
            for key in actual:
                self.assertAlmostEqual(actual[key], expected[key])

    def test_invalid_or_short_history_rejected(self):
        with self.assertRaises(ValueError):
            allocation([100] * LOOKBACK, .14)
        for price in (0, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                allocation([100] * LOOKBACK + [price], .14)

    def test_cadence_and_offline_safety(self):
        cfg = settings()
        history = {p: [100] * LOOKBACK + [100.2] for p in PAIRS}
        self.assertIsNone(strategy_targets(history, {}, cfg, 73))
        target = strategy_targets(history, {}, cfg, 72)
        self.assertGreater(sum(target.values()), 0)
        self.assertLessEqual(sum(target.values()), .7)
        client = Mock()
        with self.assertRaises(ValueError):
            BotEngine(client, cfg)
        client.assert_not_called()
        with self.assertRaises(ValueError):
            replace(cfg, signal_source="roostoo")
        with self.assertRaises(ValueError):
            replace(cfg, decision_every_bars=12)

    def test_frozen_plan_and_window_lengths(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(hashlib.sha256((root/"VOL_MOMENTUM_PLAN.md").read_bytes()).hexdigest(), PLAN_SHA256)
        from datetime import date
        for stage in ("screen", "validation"):
            self.assertEqual(len(periods(stage)), 10)
            for label, first, last in periods(stage):
                if "_" in label:
                    self.assertEqual((date.fromisoformat(last)-date.fromisoformat(first)).days, 14)

    def test_gates_require_complete_results_and_do_not_promote_volatility_control(self):
        rows = self.good_rows()
        self.assertTrue(assess(rows, "screen")["advance_to_validation"])
        self.assertFalse(assess(rows, "screen")["strategy_approved_for_live"])
        with self.assertRaises(ValueError):
            assess(rows[:-1], "screen")
        with self.assertRaises(ValueError):
            assess(rows + [rows[0]], "screen")
        for row in rows:
            if row["strategy"] == "vol_control":
                row["total_return"] = .02
        self.assertFalse(assess(rows, "screen")["advance_to_validation"])

    def good_rows(self):
        return [dict(period=p, strategy=s, cost=c, total_return=.01 if s == "vol_momentum" else 0,
                     max_drawdown=.02, active_days_utc=8)
                for p, _, _ in periods("screen") for s in STRATEGIES for c in ("base", "stress")]

    def test_each_profitability_activity_or_drawdown_gate_can_reject(self):
        for failure in ("quarter", "months", "windows", "activity", "drawdown"):
            rows = self.good_rows()
            for row in rows:
                if row["strategy"] != "vol_momentum" or row["cost"] != "stress":
                    continue
                period = row["period"]
                if failure == "quarter" and period == "quarter":
                    row["total_return"] = 0
                if failure == "months" and period in {"2025-01", "2025-02"}:
                    row["total_return"] = -.001
                if failure == "windows" and "_" in period:
                    row["total_return"] = -.001
                if failure == "activity" and "_" in period:
                    row["active_days_utc"] = 7
                if failure == "drawdown" and period == "quarter":
                    row["max_drawdown"] = .0801
            with self.subTest(failure=failure):
                self.assertFalse(assess(rows, "screen")["advance_to_validation"])

    def test_failed_screen_prevents_reading_validation_inputs(self):
        rows = self.good_rows()
        for row in rows:
            row["total_return"] = -.01
        with tempfile.TemporaryDirectory() as directory:
            prior = Path(directory)
            (prior/"manifest.json").write_text(json.dumps(dict(stage="screen", plan_sha256=PLAN_SHA256)))
            (prior/"results.json").write_text(json.dumps(rows))
            args = ["vol_research", "--market", str(prior/"nonexistent"), "--output", str(prior/"output"),
                    "--stage", "validation", "--prior-stage", str(prior)]
            with patch("sys.argv", args), patch("roostoo_bot.vol_research.load_candles") as loader:
                with self.assertRaisesRegex(ValueError, "validation must remain unopened"):
                    main()
                loader.assert_not_called()
            self.assertFalse((prior/"output").exists())

    def test_future_prices_do_not_change_earlier_fills_and_cash_stays_nonnegative(self):
        start = 1790812800000000
        rows = [Candle(start+i*BAR_US, 100*math.exp(.00001*i), 100*math.exp(.00001*i)) for i in range(2600)]
        data = {p: rows for p in PAIRS}
        _, curve, original = simulate_portfolio(data, settings(), rules=RULES, start_index=LOOKBACK+1)
        boundary = start+2400*BAR_US
        changed = [Candle(r.open_time_us, 1, 1) if r.open_time_us >= boundary else r for r in rows]
        _, _, perturbed = simulate_portfolio({p:changed for p in PAIRS}, settings(), rules=RULES, start_index=LOOKBACK+1)
        before = lambda trades: [t for t in trades if t["timestamp_us"] < boundary]
        self.assertTrue(before(original))
        self.assertEqual(before(original), before(perturbed))
        self.assertGreaterEqual(min(r["cash"] for r in curve), 0)
