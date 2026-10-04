"""Frozen five-asset pullback experiment. Local archives only; never load .env."""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .backtest import load_candles
from .portfolio import PairRules
from .portfolio_backtest import research_settings, simulate_portfolio, write_report
from .research import stamp

PAIRS = ("BTC/USD", "ETH/USD", "XRP/USD", "BNB/USD", "SOL/USD")
RULES = {p: PairRules(precision, 1.0) for p, precision in zip(PAIRS, (5, 4, 1, 3, 3))}
PLAN_SHA256 = "961c92ccdf145f8dfa756ce05b2c1f331aea6bee8200fbf6c29a68aecd1c5898"
PERIODS = {
    "march": (("march", "2026-03-01", "2026-04-01"),
              ("mar01_14", "2026-03-01", "2026-03-15"),
              ("mar15_28", "2026-03-15", "2026-03-29")),
    "april": (("april", "2026-04-01", "2026-05-01"),
              ("apr01_14", "2026-04-01", "2026-04-15"),
              ("apr15_28", "2026-04-15", "2026-04-29")),
}
STRATEGIES = ("pullback_basket", "cash", "buy_hold_equal_70", "buy_hold_equal_100")


def basket_settings():
    return research_settings(api_key="", secret_key="", signal_source="offline", pairs=PAIRS,
                             strategy="pullback", max_asset_weight=.14, fast_window=144,
                             slow_window=576, decision_every_bars=3)


def assess(rows: list[dict], stage: str) -> dict:
    expected = {(p, c, s) for p, _, _ in PERIODS[stage]
                for c in ("base", "stress") for s in STRATEGIES}
    keyed = {(r["period"], r["cost"], r["strategy"]): r for r in rows}
    if len(rows) != len(expected) or set(keyed) != expected:
        raise ValueError("basket results are incomplete, duplicated or outside the frozen plan")
    candidate = {(p, c): r for (p, c, s), r in keyed.items() if s == "pullback_basket"}
    windows = [p for p, _, _ in PERIODS[stage][1:]]
    gates = {
        "full_month_positive_base_and_stress": all(candidate[(stage, c)]["total_return"] > 0 for c in ("base", "stress")),
        "all_periods_drawdown_at_most_8_percent": all(r["max_drawdown"] <= .08 for r in candidate.values()),
        "both_windows_8_active_utc_dates_base_and_stress": all(candidate[(p, c)]["active_days_utc"] >= 8 for p in windows for c in ("base", "stress")),
    }
    return {"stage": stage, "gates": gates, "stage_passed": all(gates.values()),
            "advance_to_april": stage == "march" and all(gates.values()),
            "strategy_approved_for_live": False, "qualification_verified": False,
            "activity_is_only_a_fill_date_proxy": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage", choices=list(PERIODS), default="march")
    parser.add_argument("--prior-stage", type=Path, help="March report directory, required before April")
    args = parser.parse_args()
    plan = Path(__file__).resolve().parents[2] / "BASKET_PLAN.md"
    if hashlib.sha256(plan.read_bytes()).hexdigest() != PLAN_SHA256:
        raise ValueError("frozen plan was changed; do not silently re-run a different experiment")
    if args.output.exists():
        raise ValueError("use a new output directory; never overwrite a research record")
    if args.stage == "april":
        if args.prior_stage is None:
            raise ValueError("April requires a passing March report")
        prior = json.loads((args.prior_stage / "manifest.json").read_text())
        if prior["plan_sha256"] != PLAN_SHA256 or prior["stage"] != "march":
            raise ValueError("prior stage does not belong to this frozen experiment")
        if not assess(json.loads((args.prior_stage / "results.json").read_text()), "march")["advance_to_april"]:
            raise ValueError("March failed: April must remain unopened")
    months = ("2026-02", "2026-03") if args.stage == "march" else ("2026-03", "2026-04")
    inputs, paths = [], {}
    for pair in PAIRS:
        symbol = pair.split("/")[0] + "USDT"
        paths[pair] = [args.market / f"{symbol}-5m-{m}.zip" for m in months]
        for path in paths[pair]:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if path.with_name(path.name + ".CHECKSUM").read_text().split()[0] != digest:
                raise ValueError("historical input checksum mismatch")
            inputs.append({"file": path.name, "sha256": digest})
    settings = basket_settings()
    manifest = {"created_at": datetime.now(timezone.utc).isoformat(), "stage": args.stage,
                "plan_sha256": PLAN_SHA256, "inputs": inputs,
                "source_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in sorted(plan.parent.glob("src/roostoo_bot/*.py"))},
                "rules_snapshot_date": "2026-10-01", "rules": {p: asdict(r) for p, r in RULES.items()},
                "settings": {k: v for k, v in asdict(settings).items() if k not in {"api_key", "secret_key", "data_dir"}}}
    args.output.mkdir(parents=True)
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    data = {p: load_candles(files) for p, files in paths.items()}
    times = [c.open_time_us for c in data[PAIRS[0]]]
    positions = {t: i for i, t in enumerate(times)}
    positions[times[-1] + 300_000_000] = len(times)
    results = []
    for period, first, last in PERIODS[args.stage]:
        for cost, slippage in (("base", .0005), ("stress", .0015)):
            for strategy in STRATEGIES:
                summary, curve, trades = simulate_portfolio(
                    data, replace(settings, slippage_rate=slippage), rules=RULES,
                    start_index=positions[stamp(first)], end_index=positions[stamp(last)],
                    benchmark=None if strategy == "pullback_basket" else strategy)
                row = dict(period=period, cost=cost, strategy=strategy, **summary)
                results.append(row)
                write_report(args.output / period / strategy / cost, row, curve, trades)
                if strategy == "pullback_basket":
                    print(f"{period} {cost}: return={summary['total_return']:.2%}, dd={summary['max_drawdown']:.2%}, turnover={summary['turnover']:.2f}, active_UTC={summary['active_days_utc']}", flush=True)
    verdict = assess(results, args.stage)
    (args.output / "results.json").write_text(json.dumps(results, indent=2, allow_nan=False) + "\n")
    (args.output / "verdict.json").write_text(json.dumps(verdict, indent=2) + "\n")
    print(json.dumps(verdict, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
