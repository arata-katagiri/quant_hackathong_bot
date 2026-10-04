from dataclasses import replace
from datetime import date
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
from roostoo_bot.relative_research import PLAN_SHA256, STRATEGIES, assess, main, periods, settings
from roostoo_bot.relative_strength import LOOKBACK, allocation


def prices(last=110, peak=115):
    result = [100.0] * (LOOKBACK + 1)
    result[12] = peak
    result[-1] = last
    return result


class RelativeStrengthTests(unittest.TestCase):
    def test_ranks_by_proximity_to_high_not_raw_return(self):
        history = {"A/USD": prices(110, 115), "B/USD": prices(108, 108),
                   "C/USD": prices(120, 150), "D/USD": prices(99, 100)}
        result = allocation(history, .14)
        self.assertEqual(result["ranked_eligible"], ["B/USD", "A/USD", "C/USD"])
        self.assertEqual(result["targets"], {"A/USD": .14, "B/USD": .14, "C/USD": 0, "D/USD": 0})
        self.assertAlmostEqual(result["diagnostics"]["A/USD"]["score"], 110/115)

    def test_flat_falling_and_single_eligible_keep_unused_cash(self):
        self.assertEqual(sum(allocation({p: prices(100, 100) for p in PAIRS}, .14)["targets"].values()), 0)
        self.assertEqual(sum(allocation({p: prices(99, 100) for p in PAIRS}, .14)["targets"].values()), 0)
        result = allocation({"A/USD": prices(), "B/USD": prices(99, 100)}, .14)
        self.assertEqual(result["targets"], {"A/USD": .14, "B/USD": 0})

    def test_breadth_control_matches_target_gross_but_not_selection(self):
        history = {p: prices() for p in PAIRS}
        ranked, control = allocation(history, .14), allocation(history, .14, ranking=False)
        self.assertAlmostEqual(sum(ranked["targets"].values()), .28)
        self.assertAlmostEqual(sum(control["targets"].values()), .28)
        self.assertEqual(sum(v > 0 for v in ranked["targets"].values()), 2)
        for value in control["targets"].values():
            self.assertAlmostEqual(value, .056)

    def test_ties_are_alphabetical_and_input_order_independent(self):
        history = {p: prices() for p in PAIRS}
        result = allocation(history, .14)
        self.assertEqual(result["ranked_eligible"], sorted(PAIRS))
        self.assertEqual(result, allocation(dict(reversed(list(history.items()))), .14))

    def test_scale_prefix_and_non_hourly_closes_do_not_change_signal(self):
        history = {"A/USD": prices(), "B/USD": prices(108, 108)}
        expected = allocation(history, .14)
        scaled = {p: [17*v for v in row] for p, row in history.items()}
        prefixed = {p: [9999, 1] + row for p, row in history.items()}
        sampled = {p: row[:] for p, row in history.items()}
        sampled["A/USD"][13] = 9999
        for transformed in (scaled, prefixed, sampled):
            self.assertEqual(allocation(transformed, .14), expected)

    def test_short_invalid_history_and_invalid_caps_rejected(self):
        for history in ({}, {"A/USD": [100]*LOOKBACK}, {"A/USD": prices(0)},
                        {"A/USD": prices(float("nan"))}, {"A/USD": prices(float("inf"))}):
            with self.assertRaises(ValueError):
                allocation(history, .14)
        for cap in (0, -.1, float("nan"), .51):
            with self.assertRaises(ValueError):
                allocation({"A/USD": prices()}, cap)

    def test_daily_cadence_and_both_offline_only_branches(self):
        history = {p: prices() for p in PAIRS}
        for strategy in ("relative_strength", "breadth_control"):
            cfg = replace(settings(), strategy=strategy)
            self.assertIsNone(strategy_targets(history, {}, cfg, 72))
            state = {}
            targets = strategy_targets(history, state, cfg, 288)
            self.assertEqual(targets, state["relative_strength"]["targets"])
            self.assertAlmostEqual(sum(targets.values()), .28)
            with self.assertRaises(ValueError):
                replace(cfg, signal_source="roostoo")
            with self.assertRaises(ValueError):
                replace(cfg, decision_every_bars=72)
            with self.assertRaises(ValueError):
                replace(cfg, api_key="nonempty")
            client = Mock()
            with self.assertRaises(ValueError):
                BotEngine(client, cfg)
            self.assertEqual(client.mock_calls, [])

    def test_frozen_plan_and_exact_fourteen_day_windows(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(hashlib.sha256((root/"RELATIVE_STRENGTH_PLAN.md").read_bytes()).hexdigest(), PLAN_SHA256)
        for stage in ("screen", "validation"):
            self.assertEqual(len(periods(stage)), 10)
            for label, first, last in periods(stage):
                if "_" in label:
                    self.assertEqual((date.fromisoformat(last)-date.fromisoformat(first)).days, 14)

    def good_rows(self):
        return [dict(period=p, strategy=s, cost=c, total_return=.01 if s == "relative_strength" else 0,
                     max_drawdown=.02, active_days_utc=8)
                for p, _, _ in periods("screen") for s in STRATEGIES for c in ("base", "stress")]

    def test_complete_gates_and_control_cannot_be_promoted(self):
        rows = self.good_rows()
        verdict = assess(rows, "screen")
        self.assertTrue(verdict["advance_to_validation"])
        self.assertTrue(verdict["screening_data_previously_inspected"])
        self.assertFalse(verdict["strategy_approved_for_live"])
        for bad_rows in (rows[:-1], rows+[rows[0]]):
            with self.assertRaises(ValueError):
                assess(bad_rows, "screen")
        for row in rows:
            if row["strategy"] == "breadth_control":
                row["total_return"] = .02
        self.assertFalse(assess(rows, "screen")["advance_to_validation"])

    def test_nonfinite_or_invalid_metrics_do_not_pass(self):
        for key, value in (("max_drawdown", float("nan")), ("max_drawdown", -.1),
                           ("total_return", float("inf")), ("total_return", -1.01),
                           ("active_days_utc", True), ("active_days_utc", -1)):
            rows = self.good_rows()
            rows[0][key] = value
            with self.assertRaises(ValueError):
                assess(rows, "screen")

    def test_each_gate_can_reject_under_stress_alone(self):
        for failure in ("quarter", "months", "windows", "activity", "drawdown"):
            rows = self.good_rows()
            for row in rows:
                if row["strategy"] != "relative_strength" or row["cost"] != "stress":
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

    def test_failed_screen_seals_validation_before_data_access(self):
        rows = self.good_rows()
        for row in rows:
            row["total_return"] = -.01
        with tempfile.TemporaryDirectory() as directory:
            prior = Path(directory)
            (prior/"manifest.json").write_text(json.dumps(dict(stage="screen", plan_sha256=PLAN_SHA256)))
            (prior/"results.json").write_text(json.dumps(rows))
            args = ["relative_research", "--market", str(prior/"nonexistent"), "--output", str(prior/"output"),
                    "--stage", "validation", "--prior-stage", str(prior)]
            with patch("sys.argv", args), patch("roostoo_bot.relative_research.load_candles") as loader:
                with self.assertRaisesRegex(ValueError, "validation must remain unopened"):
                    main()
                loader.assert_not_called()
            self.assertFalse((prior/"output").exists())

    def test_future_prices_do_not_change_earlier_fills_and_cash_nonnegative(self):
        start = 1735689600000000
        rows = [Candle(start+i*BAR_US, 100*math.exp(.00001*i), 100*math.exp(.00001*i)) for i in range(3500)]
        _, curve, original = simulate_portfolio({p: rows for p in PAIRS}, settings(), rules=RULES, start_index=LOOKBACK+1)
        boundary = start+3000*BAR_US
        changed = [Candle(r.open_time_us, 1, 1) if r.open_time_us >= boundary else r for r in rows]
        _, _, perturbed = simulate_portfolio({p: changed for p in PAIRS}, settings(), rules=RULES, start_index=LOOKBACK+1)
        before = lambda trades: [t for t in trades if t["timestamp_us"] < boundary]
        self.assertTrue(before(original))
        self.assertEqual(before(original), before(perturbed))
        self.assertGreaterEqual(min(r["cash"] for r in curve), 0)
        for trade in original:
            if not trade["forced"]:
                self.assertEqual(trade["timestamp_us"] % (BAR_US*288), 0)

    def test_28_percent_buy_hold_benchmark_is_costed_and_not_rebalanced(self):
        rows = [Candle(1735689600000000+i*BAR_US, 100, 100) for i in range(300)]
        summary, curve, trades = simulate_portfolio({p: rows for p in PAIRS}, settings(), rules=RULES,
                                                    benchmark="buy_hold_equal_28")
        self.assertEqual(summary["trades"], 5)
        self.assertEqual(summary["forced_liquidations"], 5)
        self.assertEqual(summary["active_days_utc"], 1)
        expected_cost = sum(float(rule.floor(5600 / (100*1.0005*1.001))) * 100*1.0005*1.001
                            for rule in RULES.values())
        self.assertAlmostEqual(sum(t["notional"]+t["fee"] for t in trades if t["side"] == "BUY"), expected_cost)
        self.assertLess(summary["final_equity"], 100000)
        self.assertGreater(summary["final_equity"], 99900)
        self.assertGreaterEqual(min(r["cash"] for r in curve), 72000)
