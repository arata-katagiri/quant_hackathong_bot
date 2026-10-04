from dataclasses import replace
import hashlib
import io
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from roostoo_bot.backtest import Candle
from roostoo_bot.basket_research import PAIRS
from roostoo_bot.funding_research import DAY_US, START
from roostoo_bot.portfolio_backtest import BAR_US
from roostoo_bot.trade_flow import PLAN_SHA256, TradeFlow, assess, describe, imbalance, load_trade_flow, main, panel, parse_rows
from roostoo_bot.vol_research import periods


def raw_row(timestamp=START, unit=1):
    return [str(timestamp//unit), "100", "101", "99", "100", "10",
            str((timestamp+BAR_US-unit)//unit), "1000", "4", "6", "600", "0"]


class TradeFlowTests(unittest.TestCase):
    def test_parse_quote_volume_and_both_timestamp_units(self):
        expected = TradeFlow(START, 1000, 600)
        self.assertEqual(parse_rows([raw_row()]), [expected])
        self.assertEqual(parse_rows([raw_row(unit=1000)]), [expected])

    def test_invalid_fields_rejected(self):
        for index, value in ((5, "-1"), (7, "nan"), (10, "inf"), (9, "11"),
                             (10, "1001"), (8, "-1"), (8, "0"), (6, str(START)),
                             (5, "0"), (9, "0")):
            row = raw_row()
            row[index] = value
            with self.subTest(index=index, value=value), self.assertRaises(ValueError):
                parse_rows([row])
        with self.assertRaises(ValueError):
            parse_rows([raw_row()[:-1]])

    def test_rounding_tolerance_is_small_and_explicit(self):
        row = raw_row()
        row[9], row[10] = "10.000000005", "1000.000000005"
        self.assertEqual(parse_rows([row])[0].taker_buy_quote, 1000)
        row[10] = "1000.000001"
        with self.assertRaises(ValueError):
            parse_rows([row])

    def archive(self, folder, rows):
        path = Path(folder)/"BTCUSDT-5m-2025-01.zip"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(path.stem+".csv", "\n".join(",".join(row) for row in rows)+"\n")
        path.with_name(path.name+".CHECKSUM").write_text(hashlib.sha256(path.read_bytes()).hexdigest())
        return path

    def test_archive_checksums_continuity_and_duplicate_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.archive(directory, [raw_row(), raw_row(START+BAR_US)])
            self.assertEqual(len(load_trade_flow([path])), 2)
            with self.assertRaises(ValueError):
                load_trade_flow([path, path])
            path = self.archive(directory, [raw_row(), raw_row(START+2*BAR_US)])
            with self.assertRaises(ValueError):
                load_trade_flow([path])
            path.with_name(path.name+".CHECKSUM").write_text("0"*64)
            with self.assertRaises(ValueError):
                load_trade_flow([path])

    def window(self, bought=600, total=1000):
        return [TradeFlow(START-DAY_US+i*BAR_US, total, bought) for i in range(288)]

    def test_imbalance_sign_zero_and_missing_volume(self):
        self.assertAlmostEqual(imbalance(self.window(), START), .2)
        self.assertAlmostEqual(imbalance(self.window(400), START), -.2)
        self.assertEqual(imbalance(self.window(500), START), 0)
        self.assertIsNone(imbalance(self.window(0, 0), START))

    def test_aggregate_quote_weighting_not_mean_of_bar_ratios(self):
        rows = self.window(0, 0)
        rows[0] = replace(rows[0], total_quote=100, taker_buy_quote=80)
        rows[1] = replace(rows[1], total_quote=900, taker_buy_quote=360)
        self.assertAlmostEqual(imbalance(rows, START), -.12)

    def test_feature_rejects_gap_future_or_incomplete_day(self):
        good = self.window()
        changed = good[:]
        changed[-1] = replace(changed[-1], open_time_us=START)
        for rows in (good[:-1], changed, list(reversed(good))):
            with self.assertRaises(ValueError):
                imbalance(rows, START)
        changed = good[:]
        changed[0] = replace(changed[0], total_quote=math.nan)
        with self.assertRaises(ValueError):
            imbalance(changed, START)

    def fixture(self):
        candles = [Candle(START-DAY_US+i*BAR_US, 100, 100) for i in range(4*288)]
        flows = [TradeFlow(c.open_time_us, 1000, 600) for c in candles]
        return {p: candles[:] for p in PAIRS}, {p: flows[:] for p in PAIRS}

    def test_current_bar_and_future_flow_excluded_from_prior_decision(self):
        data, flows = self.fixture()
        original = panel(data, flows, START, START+3*DAY_US)
        flows[PAIRS[0]][288] = TradeFlow(START, 1e9, 0)
        changed = panel(data, flows, START, START+3*DAY_US)
        prior = lambda rows: [r for r in rows if r["entry_us"] == START+BAR_US]
        self.assertEqual(prior(original), prior(changed))
        later = next(r for r in changed if r["pair"] == PAIRS[0] and r["entry_us"] == START+DAY_US+BAR_US)
        self.assertFalse(later["selected"])
        self.assertEqual(later["feature_end_exclusive_us"]+BAR_US, later["entry_us"])

    def test_payoffs_controls_exact_boundaries_and_no_april_label(self):
        data, flows = self.fixture()
        rows = panel(data, flows, START, START+3*DAY_US)
        self.assertEqual(len(rows), 2*5)
        self.assertTrue(all(r["exit_us"]-r["entry_us"] == DAY_US for r in rows))
        self.assertTrue(all(r["exit_us"] < START+3*DAY_US for r in rows))
        self.assertTrue(all(r["selected"] and r["base_return"] < 0 and r["stress_return"] < r["base_return"] for r in rows))
        for r in rows:
            self.assertAlmostEqual(r["base_advantage"], 0)
        self.assertEqual(describe(rows)["opportunity_dates_utc"], 2)

    def test_future_prices_change_labels_not_signal(self):
        data, flows = self.fixture()
        original = panel(data, flows, START, START+3*DAY_US)
        boundary = START+DAY_US+BAR_US
        changed_data = {p: [replace(c, open=80, close=80) if c.open_time_us >= boundary else c for c in rows]
                        for p, rows in data.items()}
        changed = panel(changed_data, flows, START, START+3*DAY_US)
        keys = ("pair", "entry_us", "feature_end_exclusive_us", "imbalance", "selected")
        self.assertEqual([[r[k] for k in keys] for r in original], [[r[k] for k in keys] for r in changed])
        self.assertNotEqual(original[0]["base_return"], changed[0]["base_return"])

    def test_zero_volume_missing_not_balanced_and_alignment_guard(self):
        data, flows = self.fixture()
        flows[PAIRS[0]] = [replace(row, total_quote=0, taker_buy_quote=0) for row in flows[PAIRS[0]]]
        rows = panel(data, flows, START, START+3*DAY_US)
        first = [r for r in rows if r["pair"] == PAIRS[0]]
        self.assertTrue(all(r["imbalance"] is None and not r["selected"] and not r["flow_covered"] for r in first))
        self.assertEqual(describe(rows)["coverage_by_pair"][PAIRS[0]], 0)
        flows[PAIRS[0]].pop(100)
        with self.assertRaises(ValueError):
            panel(data, flows, START, START+3*DAY_US)

    def good_reports(self):
        return {p: dict(feature_coverage=1, coverage_by_pair=dict.fromkeys(PAIRS, 1),
                        selected_observations=100, opportunity_dates_utc=30,
                        selected_by_pair=dict.fromkeys(PAIRS, 20),
                        stress=dict(mean_return=.01, mean_basket_advantage=.005))
                for p, _, _ in periods("screen")}

    def test_gate_completeness_and_no_automatic_portfolio_approval(self):
        uncertainty = dict(valid_replicates=2000, repetitions=2000,
                           stress_mean_interval=[.001, .02], stress_advantage_interval=[.001, .01])
        result = assess(self.good_reports(), uncertainty)
        self.assertTrue(result["signal_passed_feasibility"])
        self.assertFalse(result["strategy_approved_for_live"])
        self.assertFalse(result["portfolio_candidate_implemented"])
        for failure in ("coverage", "count", "dates", "assets", "lower_bound", "months", "activity", "valid_replicates"):
            reports, intervals = self.good_reports(), json.loads(json.dumps(uncertainty))
            quarter = reports["quarter"]
            if failure == "coverage":
                quarter["coverage_by_pair"][PAIRS[0]] = .98
            if failure == "count":
                quarter["selected_observations"] = 59
            if failure == "dates":
                quarter["opportunity_dates_utc"] = 29
            if failure == "assets":
                quarter["selected_by_pair"] = dict.fromkeys(PAIRS, 9)
            if failure == "lower_bound":
                intervals["stress_advantage_interval"][0] = 0
            if failure == "months":
                for m in ("2025-01", "2025-02"):
                    reports[m]["stress"]["mean_return"] = -.01
            if failure == "activity":
                for p in reports:
                    if "_" in p:
                        reports[p]["opportunity_dates_utc"] = 7
            if failure == "valid_replicates":
                intervals["valid_replicates"] = 1899
            with self.subTest(failure=failure):
                self.assertFalse(assess(reports, intervals)["signal_passed_feasibility"])
        missing = self.good_reports()
        missing.pop("quarter")
        with self.assertRaises(ValueError):
            assess(missing, uncertainty)

    def test_plan_hash_and_overwrite_guard_before_read(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(hashlib.sha256((root/"TRADE_FLOW_PLAN.md").read_bytes()).hexdigest(), PLAN_SHA256)
        with tempfile.TemporaryDirectory() as directory:
            args = ["trade_flow", "--market", "nonexistent", "--output", directory]
            with patch("sys.argv", args), patch("roostoo_bot.trade_flow.verified_payload") as loader:
                with self.assertRaisesRegex(ValueError, "new output directory"):
                    main()
                loader.assert_not_called()
