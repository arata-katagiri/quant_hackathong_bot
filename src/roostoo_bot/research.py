"""Run the predeclared portfolio experiments; never reads .env or calls an API."""
from __future__ import annotations
import argparse
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

from .backtest import load_candles
from .portfolio_backtest import research_settings, simulate_portfolio, write_report


def stamp(day: str) -> int:
    return int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp() * 1e6)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/research_v2"))
    args = parser.parse_args()
    paths = {"BTC/USD": sorted(args.market.glob("BTCUSDT-5m-*.zip")), "ETH/USD": sorted(args.market.glob("ETHUSDT-5m-*.zip"))}
    manifest = []
    for pair, files in paths.items():
        for file in files:
            actual = hashlib.sha256(file.read_bytes()).hexdigest()
            checksum = file.with_name(file.name + ".CHECKSUM")
            if not checksum.exists() or checksum.read_text().split()[0] != actual:
                raise ValueError(f"missing or invalid official checksum: {file.name}")
            manifest.append({"pair": pair, "file": file.name, "sha256": actual})
    data = {pair: load_candles(files) for pair, files in paths.items()}
    times = [c.open_time_us for c in data["BTC/USD"]]
    index = {value: i for i, value in enumerate(times)}
    index[times[-1] + 300_000_000] = len(times)
    configs = {
        "baseline": research_settings(),
        "buffered_trend": research_settings(strategy="buffered_trend", fast_window=144, slow_window=576, decision_every_bars=12),
        "breakout": research_settings(strategy="breakout", fast_window=144, slow_window=576, decision_every_bars=12),
    }
    periods = [
        ("may_holdout", "2026-05-01", "2026-06-01", "unseen_before_this_run"),
        ("june_aug_seen", "2026-06-01", "2026-09-01", "previously_inspected"),
        ("sep01_14_holdout", "2026-09-01", "2026-09-15", "unseen_before_this_run"),
        ("sep15_28_seen", "2026-09-15", "2026-09-29", "previously_inspected"),
    ]
    windows = []
    for group, first, last in (("may", "2026-05-01", "2026-06-01"), ("june_aug", "2026-06-01", "2026-09-01"), ("sep", "2026-09-01", "2026-09-29")):
        day, end = datetime.fromisoformat(first), datetime.fromisoformat(last)
        while day + timedelta(days=14) <= end:
            following = day + timedelta(days=14)
            windows.append((f"window_{group}_{day.date()}", str(day.date()), str(following.date()), "14_day_window"))
            day = following
    args.output.mkdir(parents=True, exist_ok=True)
    metadata = {"created_at": datetime.now(timezone.utc).isoformat(), "inputs": manifest,
                "simulation_version": "boundary-decisions-v3",
                "source_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path("src/roostoo_bot").glob("*.py"))},
                "configs": {name: {k:v for k,v in asdict(cfg).items() if k not in {"api_key", "secret_key", "data_dir"}} for name, cfg in configs.items()},
                "plan_sha256": hashlib.sha256(Path("EXPERIMENT_PLAN.md").read_bytes()).hexdigest()}
    (args.output / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
    all_results = []
    for period, first, last, category in periods + windows:
        start, end = index[stamp(first)], index[stamp(last)]
        candidates = [(name, cfg, None) for name, cfg in configs.items()]
        candidates.extend((name, configs["baseline"], name) for name in ("cash", "buy_hold_35", "buy_hold_50"))
        for cost_name, slippage in (("base", .0005), ("stress", .0015)):
            for name, settings, benchmark in candidates:
                result, curve, trades = simulate_portfolio(data, replace(settings, slippage_rate=slippage), start_index=start, end_index=end, benchmark=benchmark)
                entry = dict(period=period, category=category, strategy=name, cost=cost_name, **result)
                all_results.append(entry)
                if category != "14_day_window":
                    write_report(args.output / period / name / cost_name, entry, curve, trades)
                print(f"{period} {name} {cost_name}: return={result['total_return']:.2%} dd={result['max_drawdown']:.2%} turnover={result['turnover']:.2f} active_HKT={result['active_days_hkt']}", flush=True)
        (args.output / "results.json").write_text(json.dumps(all_results, indent=2, allow_nan=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
