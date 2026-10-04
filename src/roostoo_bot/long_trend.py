"""Frozen monthly-horizon long/cash rule; portfolio research only."""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import random
from statistics import fmean, median, pstdev
import zipfile

from .backtest import _parse_candle_rows
from .basket_research import PAIRS, RULES
from .forecast_research import MONTHS, load_month
from .funding_data import verified_payload
from .funding_research import DAY_US, percentile
from .portfolio_backtest import BAR_US, ScheduledTarget, research_settings, simulate_portfolio, write_report
from .research import stamp

PLAN_SHA256 = "48549f6c9f8baa0fc05491bc084ea44cf4dfd1db1ab814b7cb1d453ba8077cad"
START, END = stamp("2022-01-01"), stamp("2025-01-01")
STRATEGIES = ("long_trend", "covariance_control", "cash", "buy_hold_equal_70", "buy_hold_equal_100")


def periods():
    return [(f"trial_{i:02}", first, first+14*DAY_US)
            for i, first in enumerate(range(START, END-14*DAY_US+1, 14*DAY_US))]


def allocation(history: dict[str, list[float]], *, timing: bool = True) -> dict:
    if set(history) != set(PAIRS) or any(len(v) != 366 for v in history.values()):
        raise ValueError("long trend requires exactly 366 prior daily closes for all five assets")
    if any(not math.isfinite(p) or p <= 0 for v in history.values() for p in v):
        raise ValueError("invalid daily close")
    votes = {p: [(history[p][-1] > history[p][-1-h])-(history[p][-1] < history[p][-1-h])
                 for h in (30, 90, 365)] for p in PAIRS}
    preliminary = {p: .14*max(0.0, fmean(votes[p])) if timing else .14 for p in PAIRS}
    portfolio_returns = [math.fsum(preliminary[p]*math.log(history[p][i]/history[p][i-1]) for p in PAIRS)
                         for i in range(346, 366)]
    sigma = pstdev(portfolio_returns)
    scale = min(1.0, .0075/sigma) if sigma else 1.0
    return dict(votes=votes, preliminary=preliminary, estimated_daily_volatility=sigma,
                scale=scale, targets={p: preliminary[p]*scale for p in PAIRS})


def schedule_for(days: dict[str, dict], first: int, last: int, *, timing=True):
    if set(days) != set(PAIRS) or first % DAY_US or last % DAY_US or first >= last:
        raise ValueError("invalid long trend calendar")
    schedule, diagnostics = {}, []
    for cutoff in range(first, last, DAY_US):
        history = {p: [days[p].get(cutoff-(366-i)*DAY_US) for i in range(366)] for p in PAIRS}
        if any(v is None for values in history.values() for v in values):
            return None, dict(reason="missing_required_daily_close", cutoff_us=cutoff)
        result = allocation(history, timing=timing)
        execution = cutoff+BAR_US
        schedule[execution] = ScheduledTarget(cutoff, result["targets"])
        diagnostics.append(dict(execution_us=execution, source_cutoff_us=cutoff, **result))
    return schedule, diagnostics


def load_inputs(market: Path):
    days, prices, inputs = {}, {}, []
    for pair in PAIRS:
        days[pair], prices[pair] = {}, {}
        for month in MONTHS:
            path = market/f"{pair.split('/')[0]}USDT-5m-{month}.zip"
            payload = verified_payload(path)
            inputs.append(dict(file=path.name, sha256=hashlib.sha256(payload).hexdigest()))
            # This loader validates every field/month/order and rejects the
            # known invalid-close records without repairing or reusing them.
            for day in load_month(path):
                days[pair][day.start_us] = day.close
            if month < "2022-01":
                continue
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                with archive.open(archive.namelist()[0]) as stream:
                    for raw in csv.reader(io.TextIOWrapper(stream)):
                        if not raw or raw[0].lower() in {"open time", "open_time", "timestamp"}:
                            continue
                        unit = 1000 if int(raw[0]) < 10**15 else 1
                        timestamp = int(raw[0])*unit
                        if int(raw[6])*unit != timestamp+BAR_US-unit:
                            continue
                        candle = _parse_candle_rows([raw])[0]
                        prices[pair][timestamp] = candle
        print("validated daily closes and execution bars:", pair, flush=True)
    return days, prices, inputs


def trial_data(prices, first, last):
    times = range(first, last, BAR_US)
    if any(t not in prices[p] for p in PAIRS for t in times):
        return None
    return {p: [prices[p][t] for t in times] for p in PAIRS}


def block_intervals(candidate: list[float | None], control: list[float | None], repetitions=2000):
    if len(candidate) != 78 or len(control) != 78 or repetitions < 1:
        raise ValueError("bootstrap requires the full 78-slot calendar")
    if any((a is None) != (b is None) for a, b in zip(candidate, control)):
        raise ValueError("unpaired trial coverage")
    rng, returns, advantages = random.Random(20261002), [], []
    for _ in range(repetitions):
        indices = []
        while len(indices) < 78:
            start = rng.randrange(78)
            indices.extend((start, (start+1)%78))
        selected = [i for i in indices[:78] if candidate[i] is not None]
        if selected:
            returns.append(fmean(candidate[i] for i in selected))
            advantages.append(fmean(candidate[i]-control[i] for i in selected))
    interval = lambda values: [percentile(values, .025), percentile(values, .975)] if values else [None, None]
    return dict(repetitions=repetitions, valid_replicates=len(returns), block_trials=2, seed=20261002,
                return_interval=interval(returns), advantage_interval=interval(advantages))


def assess(rows, excluded):
    names = {p for p, _, _ in periods()}
    excluded_names = [r["period"] for r in excluded]
    if len(set(excluded_names)) != len(excluded_names) or not set(excluded_names) <= names:
        raise ValueError("invalid exclusions")
    expected = {(p, s, c) for p in names-set(excluded_names) for s in STRATEGIES for c in ("base", "stress")}
    keyed = {(r["period"], r["strategy"], r["cost"]): r for r in rows}
    if len(keyed) != len(rows) or set(keyed) != expected:
        raise ValueError("incomplete, duplicate or unexpected trial results")
    result = dict(scheduled_trials=78, usable_trials=78-len(excluded), excluded_trials=len(excluded), costs={})
    for cost in ("base", "stress"):
        selected = [r for r in rows if r["strategy"] == "long_trend" and r["cost"] == cost]
        arrays = [[keyed[(p, s, cost)]["total_return"] if (p, s, cost) in keyed else None for p, _, _ in periods()]
                  for s in ("long_trend", "covariance_control")]
        uncertainty = block_intervals(*arrays)
        years = {str(y): [r for r in selected if datetime.fromtimestamp(r["start_us"]/1e6, timezone.utc).year == y]
                 for y in (2022, 2023, 2024)}
        means = {y: fmean(r["total_return"] for r in group) if group else None for y, group in years.items()}
        positive = lambda x: x is not None and math.isfinite(x) and x > 0
        mean = fmean(r["total_return"] for r in selected) if selected else None
        control_mean = fmean(v for v in arrays[1] if v is not None) if selected else None
        gates = dict(coverage=len(selected) >= 75,
            profit_and_advantage=positive(mean) and mean > control_mean
                and uncertainty["valid_replicates"] >= .95*uncertainty["repetitions"]
                and positive(uncertainty["return_interval"][0]) and positive(uncertainty["advantage_interval"][0]),
            two_positive_years=sum(positive(v) for v in means.values()) >= 2,
            profitable_windows=sum(r["total_return"] > 0 for r in selected) >= 52,
            active_windows=sum(r["active_days_utc"] >= 8 for r in selected) >= 52,
            drawdown=bool(selected) and all(r["max_drawdown"] <= .08 for r in selected))
        result["costs"][cost] = dict(mean_return=mean, median_return=median(r["total_return"] for r in selected) if selected else None,
            control_mean_return=control_mean, mean_turnover=fmean(r["turnover"] for r in selected) if selected else None,
            worst_drawdown=max((r["max_drawdown"] for r in selected), default=None),
            positive_windows=sum(r["total_return"] > 0 for r in selected), active_utc_windows=sum(r["active_days_utc"] >= 8 for r in selected),
            active_hkt_windows=sum(r["active_days_hkt"] >= 8 for r in selected), year_means=means,
            uncertainty=uncertainty, gates=gates)
    result.update(screen_passed=all(all(v["gates"].values()) for v in result["costs"].values()),
                  strategy_approved=False, reserved_validation_opened=False, qualification_verified=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if hashlib.sha256((root/"LONG_TREND_PLAN.md").read_bytes()).hexdigest() != PLAN_SHA256:
        raise ValueError("long trend plan changed")
    if args.output.exists():
        raise ValueError("use a new output directory")
    days, prices, inputs = load_inputs(args.market)
    cfg = research_settings(api_key="", secret_key="", signal_source="offline", pairs=PAIRS,
        strategy="cash", fast_window=1, slow_window=2, max_asset_weight=.14, rebalance_band=.0025)
    args.output.mkdir(parents=True)
    manifest = dict(created_at=datetime.now(timezone.utc).isoformat(), plan_sha256=PLAN_SHA256, inputs=inputs,
        settings={k:v for k,v in asdict(cfg).items() if k not in {"api_key", "secret_key", "data_dir"}},
        rules={p:asdict(r) for p,r in RULES.items()},
        source_sha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.glob("src/roostoo_bot/*.py"))})
    (args.output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    rows, excluded = [], []
    for period, first, last in periods():
        data = trial_data(prices, first, last)
        candidate, diagnostics = schedule_for(days, first, last)
        if data is None or candidate is None:
            excluded.append(dict(period=period, start_us=first, end_exclusive_us=last,
                reason="missing_execution_bar" if data is None else diagnostics["reason"]))
            print(period, "excluded:", excluded[-1]["reason"], flush=True)
            continue
        control, control_diagnostics = schedule_for(days, first, last, timing=False)
        (args.output/f"{period}_schedule.json").write_text(json.dumps(dict(candidate=diagnostics, control=control_diagnostics),indent=2)+"\n")
        for cost, slip in (("base", .0005), ("stress", .0015)):
            for strategy in STRATEGIES:
                schedule = candidate if strategy == "long_trend" else control if strategy == "covariance_control" else None
                summary, curve, trades = simulate_portfolio(data, replace(cfg, slippage_rate=slip), rules=RULES,
                    target_schedule=schedule, benchmark=None if schedule is not None else strategy)
                row = dict(period=period, strategy=strategy, cost=cost, **summary)
                rows.append(row)
                write_report(args.output/period/strategy/cost, row, curve, trades)
                if strategy == "long_trend":
                    print(period, cost, f"return={summary['total_return']:.2%} dd={summary['max_drawdown']:.2%} active={summary['active_days_utc']}",flush=True)
        (args.output/"results.json").write_text(json.dumps(rows, indent=2, allow_nan=False)+"\n")
        (args.output/"excluded.json").write_text(json.dumps(excluded, indent=2)+"\n")
    verdict = assess(rows, excluded)
    (args.output/"excluded.json").write_text(json.dumps(excluded, indent=2)+"\n")
    (args.output/"verdict.json").write_text(json.dumps(verdict, indent=2, allow_nan=False)+"\n")
    print(json.dumps(verdict, indent=2),flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
