from dataclasses import replace
from pathlib import Path
import hashlib
import json
import tempfile
import unittest
from unittest.mock import Mock, patch

from roostoo_bot.backtest import Candle
from roostoo_bot.basket_research import PAIRS, RULES, PERIODS, STRATEGIES, PLAN_SHA256, assess, basket_settings, main
from roostoo_bot.download_data import archive_parts
from roostoo_bot.engine import BotEngine
from roostoo_bot.portfolio_backtest import BAR_US, simulate_portfolio


class BasketTests(unittest.TestCase):
    def setUp(self):
        self.settings = basket_settings()
        self.data = {p: [Candle(1780272000000000 + i * BAR_US, 100 + i, 100 + i)
                         for i in range(30)] for p in PAIRS}

    def test_frozen_plan_fingerprint(self):
        path = Path(__file__).resolve().parents[1] / "BASKET_PLAN.md"
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), PLAN_SHA256)

    def test_offline_settings_cannot_access_engine_or_credentials(self):
        client = Mock()
        with self.assertRaisesRegex(ValueError, "cannot run"):
            BotEngine(client, self.settings)
        self.assertEqual(client.mock_calls, [])
        for kwargs in ({"api_key": "secret"}, {"secret_key": "secret"}, {"live_trading_enabled": True}):
            with self.assertRaisesRegex(ValueError, "offline research"):
                replace(self.settings, **kwargs)
        with self.assertRaises(ValueError):
            replace(self.settings, signal_source="binance")

    def test_equal_weight_benchmarks_share_cash_without_leverage(self):
        for name, total in (("buy_hold_equal_70", .7), ("buy_hold_equal_100", 1)):
            result, curve, trades = simulate_portfolio(self.data, self.settings, rules=RULES, benchmark=name)
            self.assertEqual(result["trades"], 5)
            self.assertEqual(result["forced_liquidations"], 5)
            self.assertGreaterEqual(min(r["cash"] for r in curve), 0)
            purchases = [r for r in trades if r["side"] == "BUY"]
            self.assertLessEqual(sum(t["notional"] + t["fee"] for t in purchases), 100000 * total + 1e-8)
            self.assertEqual(result["active_days_utc"], 1)

    def test_missing_rules_and_two_asset_benchmarks_rejected(self):
        with self.assertRaisesRegex(ValueError, "rules must exactly"):
            simulate_portfolio(self.data, self.settings)
        with self.assertRaisesRegex(ValueError, "exactly two assets"):
            simulate_portfolio(self.data, self.settings, rules=RULES, benchmark="buy_hold_50")

    def test_five_asset_orders_do_not_see_future_prices(self):
        settings = replace(self.settings, strategy="baseline", fast_window=1, slow_window=2)
        _, _, trades = simulate_portfolio(self.data, settings, rules=RULES)
        self.assertTrue(trades)
        boundary = self.data[PAIRS[0]][15].open_time_us
        changed = {p: [Candle(c.open_time_us, 1, 1) if c.open_time_us >= boundary else c for c in rows]
                   for p, rows in self.data.items()}
        _, _, after = simulate_portfolio(changed, settings, rules=RULES)
        self.assertEqual([t for t in trades if t["timestamp_us"] < boundary],
                         [t for t in after if t["timestamp_us"] < boundary])

    def test_gates_require_all_rows_positive_month_activity_and_drawdown(self):
        rows = [dict(period=p, cost=c, strategy=s, total_return=.01, max_drawdown=.02, active_days_utc=8)
                for p, _, _ in PERIODS["march"] for c in ("base", "stress") for s in STRATEGIES]
        self.assertTrue(assess(rows, "march")["advance_to_april"])
        with self.assertRaises(ValueError):
            assess(rows[:-1], "march")
        with self.assertRaises(ValueError):
            assess(rows + [rows[0]], "march")
        for period, field, value in (("march", "total_return", 0), ("mar01_14", "active_days_utc", 7),
                                     ("mar15_28", "max_drawdown", .0801)):
            altered = [dict(r, **{field: value}) if r["period"] == period and r["cost"] == "stress"
                       and r["strategy"] == "pullback_basket" else dict(r) for r in rows]
            self.assertFalse(assess(altered, "march")["advance_to_april"])

    def test_public_archive_names_are_validated_before_network_or_paths(self):
        self.assertEqual(archive_parts("SOLUSDT-5m-2026-03.zip"), ("SOLUSDT", "5m", "monthly"))
        self.assertEqual(archive_parts("XRPUSDT-5m-2026-03-01.zip"), ("XRPUSDT", "5m", "daily"))
        for name in ("../SOLUSDT-5m-2026-03.zip", "SOLUSDT-1m-2026-03.zip", "SOLUSDT-5m-2026-02-30.zip"):
            with self.assertRaises(ValueError):
                archive_parts(name)

    def test_failed_march_blocks_april_before_loading_any_market_data(self):
        rows = [dict(period=p, cost=c, strategy=s, total_return=-.01, max_drawdown=.02, active_days_utc=4)
                for p, _, _ in PERIODS["march"] for c in ("base", "stress") for s in STRATEGIES]
        with tempfile.TemporaryDirectory() as directory:
            prior = Path(directory)
            (prior / "manifest.json").write_text(json.dumps(dict(stage="march", plan_sha256=PLAN_SHA256)))
            (prior / "results.json").write_text(json.dumps(rows))
            args = ["basket_research", "--market", str(prior / "nonexistent"), "--output", str(prior / "output"),
                    "--stage", "april", "--prior-stage", str(prior)]
            with patch("sys.argv", args), patch("roostoo_bot.basket_research.load_candles") as loader:
                with self.assertRaisesRegex(ValueError, "April must remain unopened"):
                    main()
                loader.assert_not_called()
            self.assertFalse((prior / "output").exists())
