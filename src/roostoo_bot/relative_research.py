"""Frozen relative-strength experiment on local public archives; no credentials."""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

from .backtest import load_candles
from .basket_research import PAIRS, RULES
from .portfolio_backtest import research_settings, simulate_portfolio, write_report
from .research import stamp
from .vol_research import STAGES, periods

PLAN_SHA256 = "48cc699b0d4446c7780cae0fe5c154458b07222600b0961623764b58ece23cfa"
STRATEGIES = ("relative_strength", "breadth_control", "cash", "buy_hold_equal_28", "buy_hold_equal_100")


def settings():
    return research_settings(api_key="", secret_key="", signal_source="offline", pairs=PAIRS,
                             strategy="relative_strength", max_asset_weight=.14, fast_window=288,
                             slow_window=2016, decision_every_bars=288)


def assess(rows, stage):
    expected = {(p, s, c) for p, _, _ in periods(stage) for s in STRATEGIES for c in ("base", "stress")}
    keyed = {(r["period"], r["strategy"], r["cost"]): r for r in rows}
    if len(rows) != len(expected) or set(keyed) != expected:
        raise ValueError("relative-strength results missing, duplicated or outside frozen plan")
    for row in rows:
        if (not math.isfinite(row["total_return"]) or row["total_return"] < -1
                or not math.isfinite(row["max_drawdown"]) or not 0 <= row["max_drawdown"] <= 1
                or type(row["active_days_utc"]) is not int or row["active_days_utc"] < 0):
            raise ValueError("invalid relative-strength result metrics")
    months = STAGES[stage][1]
    windows = [p for p, _, _ in periods(stage) if "_" in p]
    candidate = lambda p, c: keyed[(p, "relative_strength", c)]
    gates = {}
    for cost in ("base", "stress"):
        quarter = candidate("quarter", cost)
        gates[cost] = {
            "quarter_positive_and_above_breadth_control": quarter["total_return"] > 0 and quarter["total_return"] > keyed[("quarter", "breadth_control", cost)]["total_return"],
            "two_positive_months": sum(candidate(p, cost)["total_return"] > 0 for p in months) >= 2,
            "four_positive_windows": sum(candidate(p, cost)["total_return"] > 0 for p in windows) >= 4,
            "four_windows_with_8_active_utc_dates": sum(candidate(p, cost)["active_days_utc"] >= 8 for p in windows) >= 4,
            "all_periods_drawdown_at_most_8_percent": all(candidate(p, cost)["max_drawdown"] <= .08 for p, _, _ in periods(stage)),
        }
    passed = all(all(g.values()) for g in gates.values())
    return {"stage": stage, "gates": gates, "stage_passed": passed,
            "advance_to_validation": stage == "screen" and passed,
            "screening_data_previously_inspected": True,
            "strategy_approved_for_live": False, "qualification_verified": False,
            "april_2026_opened": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage", choices=list(STAGES), default="screen")
    parser.add_argument("--prior-stage", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if hashlib.sha256((root/"RELATIVE_STRENGTH_PLAN.md").read_bytes()).hexdigest() != PLAN_SHA256:
        raise ValueError("relative-strength research plan fingerprint changed")
    if args.output.exists():
        raise ValueError("use a new output directory; do not overwrite a research record")
    if args.stage == "validation":
        if args.prior_stage is None:
            raise ValueError("validation requires a passing screening report")
        prior = json.loads((args.prior_stage/"manifest.json").read_text())
        if prior["stage"] != "screen" or prior["plan_sha256"] != PLAN_SHA256:
            raise ValueError("incorrect prior-stage provenance")
        if not assess(json.loads((args.prior_stage/"results.json").read_text()), "screen")["advance_to_validation"]:
            raise ValueError("screen failed; validation must remain unopened")
    warmup, months, _ = STAGES[args.stage]
    inputs, paths = [], {}
    for pair in PAIRS:
        symbol = pair.split("/")[0]+"USDT"
        paths[pair] = [args.market/f"{symbol}-5m-{m}.zip" for m in (warmup, *months)]
        for path in paths[pair]:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if path.with_name(path.name+".CHECKSUM").read_text().split()[0] != digest:
                raise ValueError("archive checksum mismatch")
            inputs.append({"file": path.name, "sha256": digest})
    cfg = settings()
    args.output.mkdir(parents=True)
    manifest = {"created_at": datetime.now(timezone.utc).isoformat(), "stage": args.stage,
                "plan_sha256": PLAN_SHA256, "inputs": inputs,
                "screening_data_previously_inspected": True,
                "settings": {k:v for k,v in asdict(cfg).items() if k not in {"api_key", "secret_key", "data_dir"}},
                "rules": {p:asdict(r) for p,r in RULES.items()},
                "source_sha256": {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in sorted(root.glob("src/roostoo_bot/*.py"))}}
    (args.output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    data = {p:load_candles(files) for p,files in paths.items()}
    times = [c.open_time_us for c in data[PAIRS[0]]]
    index = {t:i for i,t in enumerate(times)}
    index[times[-1]+300_000_000] = len(times)
    results = []
    for period, first, last in periods(args.stage):
        for cost, slip in (("base", .0005), ("stress", .0015)):
            for strategy in STRATEGIES:
                is_rule = strategy in {"relative_strength", "breadth_control"}
                run_cfg = replace(cfg, slippage_rate=slip, strategy=strategy if is_rule else "relative_strength")
                summary, curve, trades = simulate_portfolio(data, run_cfg, rules=RULES,
                    start_index=index[stamp(first)], end_index=index[stamp(last)],
                    benchmark=None if is_rule else strategy)
                row = dict(period=period, cost=cost, strategy=strategy, **summary)
                results.append(row)
                write_report(args.output/period/strategy/cost, row, curve, trades)
                if strategy == "relative_strength":
                    print(f"{period} {cost}: return={summary['total_return']:.2%}, dd={summary['max_drawdown']:.2%}, turnover={summary['turnover']:.2f}, active_UTC={summary['active_days_utc']}", flush=True)
        (args.output/"results.json").write_text(json.dumps(results, indent=2, allow_nan=False)+"\n")
    verdict = assess(results, args.stage)
    (args.output/"verdict.json").write_text(json.dumps(verdict, indent=2)+"\n")
    print(json.dumps(verdict, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
