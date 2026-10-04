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
from roostoo_bot.funding_data import Funding, HOUR_US, LAG_US, archive_parts, asof, download, load_funding, parse_archive, verified_payload
from roostoo_bot.funding_research import DAY_US, PLAN_SHA256, START, assess, bootstrap, describe, main, panel, payoff, percentile
from roostoo_bot.portfolio_backtest import BAR_US
from roostoo_bot.vol_research import periods

NAME = "BTCUSDT-fundingRate-2025-01.zip"
HEADER = "calc_time,funding_interval_hours,last_funding_rate\n"


def packed(text, name=NAME[:-4]+".csv"):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(name, text)
    return buffer.getvalue()


class FundingResearchTests(unittest.TestCase):
    def test_schema_units_and_negative_rates(self):
        rows = parse_archive(NAME, packed(HEADER+"1735689600000,8,-0.0001\n1735718400000,4,0\n"))
        self.assertEqual(rows, [Funding(START, 8, -.0001), Funding(START+8*HOUR_US, 4, 0)])

    def test_bad_schema_timestamp_interval_rates_and_order_fail(self):
        cases = ["wrong,headers\n1,2\n", HEADER,
                 HEADER+"1735689600000000,8,0\n", HEADER+"1735689600000,0,0\n",
                 HEADER+"1735689600000,8,nan\n", HEADER+"1735689600000,8,1\n",
                 HEADER+"1733011200000,8,0\n",
                 HEADER+"1735689600000,8,0\n1735689600000,8,0\n",
                 HEADER+"1735718400000,8,0\n1735689600000,8,0\n",
                 HEADER+"1735689600000,8,0,extra\n"]
        for contents in cases:
            with self.subTest(contents=contents), self.assertRaises(ValueError):
                parse_archive(NAME, packed(contents))
        with self.assertRaises(ValueError):
            parse_archive(NAME, packed(HEADER+"1735689600000,8,0\n", name="unexpected.csv"))

    def test_archive_allowlist_and_frozen_download_months(self):
        self.assertEqual(archive_parts(NAME), ("BTCUSDT", "2025-01"))
        for name in ("../"+NAME, "DOGEUSDT-fundingRate-2025-01.zip", "BTCUSDT-fundingRate-2025-13.zip"):
            with self.assertRaises(ValueError):
                archive_parts(name)
        with patch("roostoo_bot.funding_data.urlopen") as remote:
            with self.assertRaisesRegex(ValueError, "frozen screening"):
                download(Path("unused"), "BTCUSDT-fundingRate-2025-04.zip")
            remote.assert_not_called()

    def test_checksum_and_duplicate_archive_guards(self):
        data = packed(HEADER+"1735689600000,8,-0.0001\n")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/NAME
            path.write_bytes(data)
            checksum = path.with_name(path.name+".CHECKSUM")
            checksum.write_text(hashlib.sha256(data).hexdigest()+"  "+NAME)
            self.assertEqual(verified_payload(path), data)
            self.assertEqual(len(load_funding([path])), 1)
            with self.assertRaises(ValueError):
                load_funding([path, path])
            checksum.write_text("0"*64)
            with self.assertRaises(ValueError):
                load_funding([path])

    def test_downloader_preserves_existing_data_and_checksum(self):
        data = packed(HEADER+"1735689600000,8,-0.0001\n")
        checksum = hashlib.sha256(data).hexdigest().encode()+b"  "+NAME.encode()
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with patch("roostoo_bot.funding_data.urlopen", side_effect=[io.BytesIO(checksum), io.BytesIO(data)]) as remote:
                self.assertEqual(download(folder, NAME), NAME)
                self.assertEqual(remote.call_count, 2)
            with patch("roostoo_bot.funding_data.urlopen", return_value=io.BytesIO(checksum)) as remote:
                download(folder, NAME)
                self.assertEqual(remote.call_count, 1)
            (folder/NAME).write_bytes(b"damaged")
            with patch("roostoo_bot.funding_data.urlopen", return_value=io.BytesIO(checksum)):
                with self.assertRaises(ValueError):
                    download(folder, NAME)
            self.assertEqual((folder/NAME).read_bytes(), b"damaged")

    def test_asof_publication_lag_staleness_and_interval_change(self):
        row = Funding(START, 8, -.0001)
        self.assertIsNone(asof([row], [START], START+LAG_US-1))
        self.assertEqual(asof([row], [START], START+LAG_US), row)
        self.assertEqual(asof([row], [START], START+8*HOUR_US), row)
        self.assertIsNone(asof([row], [START], START+8*HOUR_US+1))
        changed = replace(row, interval_hours=1)
        self.assertIsNone(asof([changed], [START], START+2*HOUR_US))

    def test_future_funding_cannot_change_prior_signal(self):
        before = Funding(START, 8, -.0001)
        future = Funding(START+HOUR_US, 8, .01)
        decision = START+600_000_000
        self.assertEqual(asof([before], [before.timestamp_us], decision),
                         asof([before, future], [before.timestamp_us, future.timestamp_us], decision))

    def fixture(self, days=3):
        candles = [Candle(START+i*BAR_US, 100, 100) for i in range(days*288)]
        funding = [Funding(START+i*8*HOUR_US, 8, -.0001) for i in range(days*3)]
        return {p: candles[:] for p in PAIRS}, {p: funding[:] for p in PAIRS}

    def test_cost_formula_no_funding_credit_and_zero_not_negative(self):
        self.assertAlmostEqual(payoff(100, 100, .0005), .9995*.999/(1.0005*1.001)-1)
        self.assertLess(payoff(100, 101, .0015), payoff(100, 101, .0005))
        data, funding = self.fixture()
        funding[PAIRS[0]] = [replace(row, rate=0) for row in funding[PAIRS[0]]]
        rows = panel(data, funding, START, START+3*DAY_US)
        self.assertEqual(len(rows), (9-1)*5)
        self.assertTrue(all(r["exit_us"] < START+3*DAY_US for r in rows))
        self.assertTrue(all(r["entry_us"] % (8*HOUR_US) == 600_000_000 for r in rows))
        self.assertTrue(all(not r["selected"] for r in rows if r["pair"] == PAIRS[0]))
        self.assertTrue(all(r["base_return"] < 0 and r["gross_return"] == 0 for r in rows))
        for row in rows:
            self.assertAlmostEqual(row["stress_advantage"], 0)
        report = describe(rows)
        self.assertEqual(report["negative_observations"], 8*4)
        self.assertEqual(report["opportunity_dates_utc"], 3)

    def test_missing_stale_or_future_records_are_not_backfilled(self):
        data, funding = self.fixture()
        funding[PAIRS[0]] = [Funding(START+10*DAY_US, 8, -.1)]
        rows = panel(data, funding, START, START+3*DAY_US)
        affected = [r for r in rows if r["pair"] == PAIRS[0]]
        self.assertTrue(all(not r["funding_covered"] and r["funding_rate"] is None and not r["selected"] for r in affected))
        self.assertEqual(describe(rows)["coverage_by_pair"][PAIRS[0]], 0)

    def test_future_price_change_only_changes_labels_not_signals(self):
        data, funding = self.fixture()
        original = panel(data, funding, START, START+3*DAY_US)
        boundary = START+2*DAY_US
        modified = {p: [replace(c, open=80, close=80) if c.open_time_us >= boundary else c for c in series]
                    for p, series in data.items()}
        changed = panel(modified, funding, START, START+3*DAY_US)
        keys = ("pair", "entry_us", "funding_timestamp_us", "funding_rate", "selected")
        self.assertEqual([[r[k] for k in keys] for r in original], [[r[k] for k in keys] for r in changed])
        self.assertEqual([r for r in original if r["exit_us"] < boundary], [r for r in changed if r["exit_us"] < boundary])

    def test_bad_alignment_bounds_and_payoffs_rejected(self):
        data, funding = self.fixture()
        data[PAIRS[0]].pop(10)
        with self.assertRaises(ValueError):
            panel(data, funding, START, START+3*DAY_US)
        for arguments in ((0, 100, .0005), (100, math.nan, .0005), (100, 100, -.1)):
            with self.assertRaises(ValueError):
                payoff(*arguments)

    def test_block_bootstrap_deterministic_and_keeps_coin_cluster(self):
        rows = []
        for day in range(14):
            rows.extend([dict(entry_us=START+day*DAY_US, selected=True, stress_return=.01, stress_advantage=.02),
                         dict(entry_us=START+day*DAY_US, selected=True, stress_return=-.01, stress_advantage=-.02)])
        result = bootstrap(rows, START, START+14*DAY_US, repetitions=100)
        self.assertEqual(result, bootstrap(rows, START, START+14*DAY_US, repetitions=100))
        self.assertEqual(result["stress_mean_interval"], [0, 0])
        self.assertEqual(result["stress_advantage_interval"], [0, 0])
        self.assertEqual(result["valid_replicates"], 100)
        self.assertEqual(percentile([0, 10], .25), 2.5)

    def test_empty_event_days_and_replicates_not_reported_as_zero_edge(self):
        result = bootstrap([], START, START+14*DAY_US, repetitions=100)
        self.assertEqual(result["calendar_days"], 14)
        self.assertEqual(result["valid_replicates"], 0)
        self.assertEqual(result["stress_mean_interval"], [None, None])
        report = describe([])
        self.assertIsNone(report["stress"]["mean_return"])

    def test_sparse_event_bootstrap_keeps_zero_event_calendar_dates(self):
        rows = [dict(entry_us=START, selected=True, stress_return=.01, stress_advantage=.02)]
        result = bootstrap(rows, START, START+90*DAY_US, repetitions=200)
        self.assertGreater(result["valid_replicates"], 0)
        self.assertLess(result["valid_replicates"], 200)
        self.assertEqual(result["calendar_days"], 90)
        for value in result["stress_mean_interval"]:
            self.assertAlmostEqual(value, .01)

    def good_reports(self):
        return {p: dict(funding_coverage=1, coverage_by_pair=dict.fromkeys(PAIRS, 1),
                        negative_observations=100, opportunity_dates_utc=30,
                        negative_by_pair=dict.fromkeys(PAIRS, 20),
                        stress=dict(mean_return=.01, mean_basket_advantage=.005))
                for p, _, _ in periods("screen")}

    def test_all_gates_required_and_pass_is_not_portfolio_approval(self):
        uncertainty = dict(valid_replicates=2000, repetitions=2000,
                           stress_mean_interval=[.001, .02], stress_advantage_interval=[.001, .01])
        good = self.good_reports()
        result = assess(good, uncertainty)
        self.assertTrue(result["signal_passed_feasibility"])
        self.assertFalse(result["strategy_approved_for_live"])
        self.assertFalse(result["portfolio_candidate_implemented"])
        for failure in ("coverage", "count", "dates", "assets", "lower_bound", "months", "activity", "valid_replicates"):
            reports, intervals = self.good_reports(), json.loads(json.dumps(uncertainty))
            quarter = reports["quarter"]
            if failure == "coverage":
                quarter["coverage_by_pair"][PAIRS[0]] = .98
            if failure == "count":
                quarter["negative_observations"] = 59
            if failure == "dates":
                quarter["opportunity_dates_utc"] = 29
            if failure == "assets":
                quarter["negative_by_pair"] = dict.fromkeys(PAIRS, 9)
            if failure == "lower_bound":
                intervals["stress_mean_interval"][0] = 0
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
        good.pop("quarter")
        with self.assertRaises(ValueError):
            assess(good, uncertainty)

    def test_plan_hash_and_no_overwrite_guard_precedes_input_reads(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(hashlib.sha256((root/"FUNDING_SIGNAL_PLAN.md").read_bytes()).hexdigest(), PLAN_SHA256)
        with tempfile.TemporaryDirectory() as directory:
            argv = ["funding_research", "--spot", "nonexistent", "--funding", "nonexistent", "--output", directory]
            with patch("sys.argv", argv), patch("roostoo_bot.funding_research.verified_payload") as loader:
                with self.assertRaisesRegex(ValueError, "new output directory"):
                    main()
                loader.assert_not_called()
