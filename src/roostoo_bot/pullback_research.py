"""One predeclared pullback hypothesis; public local data only, no credentials."""
from __future__ import annotations
import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .backtest import load_candles
from .portfolio_backtest import research_settings, simulate_portfolio, write_report
from .research import stamp

PERIODS = (
    ("january", "2026-01-01", "2026-02-01"),
    ("february", "2026-02-01", "2026-03-01"),
    ("jan01_14", "2026-01-01", "2026-01-15"),
    ("jan15_28", "2026-01-15", "2026-01-29"),
    ("feb01_14", "2026-02-01", "2026-02-15"),
    ("feb15_28", "2026-02-15", "2026-03-01"),
)


def assess(results: list[dict]) -> dict:
    candidate = [row for row in results if row["strategy"] == "pullback"]
    rows = {(r["period"],r["cost"]):r for r in candidate}
    expected = {(p,c) for p,_,_ in PERIODS for c in ("base","stress")}
    if set(rows) != expected or len(candidate) != len(expected):
        raise ValueError("predeclared candidate results are incomplete or duplicated")
    windows = [p for p,_,_ in PERIODS[2:]]
    active = {cost:sum(rows[(p,cost)]["active_days_utc"] >= 8 for p in windows) for cost in ("base","stress")}
    gates = {
        "both_months_positive_under_stress": all(rows[(p,"stress")]["total_return"] > 0 for p in ("january","february")),
        "all_windows_drawdown_at_most_8_percent": all(rows[(p,c)]["max_drawdown"] <= .08 for p in windows for c in ("base","stress")),
        "at_least_three_windows_with_8_active_dates": min(active.values()) >= 3,
    }
    return {"advance_to_sealed_holdout": all(gates.values()), "gates": gates,
            "windows_with_8_active_utc_dates": active, "strategy_approved_for_live": False,
            "qualification_verified": False, "unopened_holdout": ["2026-03", "2026-04"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/pullback_research"))
    args = parser.parse_args()
    paths, inputs = {}, []
    for pair,symbol in (("BTC/USD","BTCUSDT"),("ETH/USD","ETHUSDT")):
        paths[pair] = [args.market / f"{symbol}-5m-{month}.zip" for month in ("2025-12","2026-01","2026-02")]
        for path in paths[pair]:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if path.with_name(path.name+".CHECKSUM").read_text().split()[0] != digest:
                raise ValueError("historical input checksum mismatch")
            inputs.append({"file":path.name,"sha256":digest})
    settings = research_settings(strategy="pullback", fast_window=144, slow_window=576, decision_every_bars=3)
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {"created_at":datetime.now(timezone.utc).isoformat(),"inputs":inputs,
                "plan_sha256":hashlib.sha256(Path("PULLBACK_PLAN.md").read_bytes()).hexdigest(),
                "simulation_version":"boundary-decisions-v3",
                "source_sha256":{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path("src/roostoo_bot").glob("*.py"))},
                "settings":{k:v for k,v in asdict(settings).items() if k not in {"api_key","secret_key","data_dir"}}}
    (args.output/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    data = {p:load_candles(files) for p,files in paths.items()}
    times = [c.open_time_us for c in data["BTC/USD"]]
    positions = {timestamp:i for i,timestamp in enumerate(times)}
    positions[times[-1]+300_000_000] = len(times)
    results = []
    for period,first,last in PERIODS:
        for cost,slippage in (("base",.0005),("stress",.0015)):
            for strategy in ("pullback","cash","buy_hold_35","buy_hold_50"):
                summary,curve,trades = simulate_portfolio(data,replace(settings,slippage_rate=slippage),
                    start_index=positions[stamp(first)],end_index=positions[stamp(last)],
                    benchmark=None if strategy=="pullback" else strategy)
                row = dict(period=period,cost=cost,strategy=strategy,**summary)
                results.append(row)
                write_report(args.output/period/strategy/cost,row,curve,trades)
                if strategy=="pullback":
                    print(f"{period} {cost}: return={summary['total_return']:.2%}, dd={summary['max_drawdown']:.2%}, turnover={summary['turnover']:.2f}, active_UTC={summary['active_days_utc']}",flush=True)
    verdict = assess(results)
    (args.output/"results.json").write_text(json.dumps(results,indent=2,allow_nan=False)+"\n")
    (args.output/"verdict.json").write_text(json.dumps(verdict,indent=2)+"\n")
    print(json.dumps(verdict,indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
