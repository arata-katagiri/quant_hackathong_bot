"""Frozen funding-to-spot predictive screen, NOT an executable portfolio."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
from statistics import fmean, median

from .backtest import Candle, load_candles
from .basket_research import PAIRS
from .funding_data import Funding, HOUR_US, MONTHS, asof, load_funding, verified_payload
from .portfolio_backtest import validate_alignment
from .research import stamp
from .vol_research import periods

PLAN_SHA256 = "3c6dfc3505108d75e80984ca4f22496e61cc48883a8ec0ada4871a3280196023"
DAY_US = 24 * HOUR_US
HORIZON_US = 8 * HOUR_US
START, END = stamp("2025-01-01"), stamp("2025-04-01")


def payoff(entry: float, exit_price: float, slip: float, fee: float = .001) -> float:
    if (any(not math.isfinite(p) or p <= 0 for p in (entry, exit_price))
            or not math.isfinite(slip) or not 0 <= slip < 1
            or not math.isfinite(fee) or not 0 <= fee < 1):
        raise ValueError("invalid isolated-return prices or costs")
    return exit_price * (1-slip) * (1-fee) / (entry * (1+slip) * (1+fee)) - 1


def panel(data: dict[str, list[Candle]], funding: dict[str, list[Funding]],
          start_us: int, end_us: int) -> list[dict]:
    validate_alignment(data, PAIRS)
    if set(funding) != set(PAIRS) or start_us % DAY_US or end_us % DAY_US or end_us <= start_us:
        raise ValueError("invalid funding universe or calendar bounds")
    indices = {p: {c.open_time_us: c.open for c in data[p]} for p in PAIRS}
    timestamps = {p: [r.timestamp_us for r in funding[p]] for p in PAIRS}
    for p in PAIRS:
        if any(a >= b for a, b in zip(timestamps[p], timestamps[p][1:])):
            raise ValueError("funding records must be strictly ordered")
        for row in funding[p]:
            if not 1 <= row.interval_hours <= 24 or not math.isfinite(row.rate) or not -1 < row.rate < 1:
                raise ValueError("invalid funding input")
    output = []
    for entry_us in range(start_us + 600_000_000, end_us-HORIZON_US, HORIZON_US):
        exit_us = entry_us + HORIZON_US
        group = []
        for pair in PAIRS:
            if entry_us not in indices[pair] or exit_us not in indices[pair]:
                raise ValueError("spot open missing at an exact entry or exit timestamp")
            entry_price, exit_price = indices[pair][entry_us], indices[pair][exit_us]
            observed = asof(funding[pair], timestamps[pair], entry_us)
            group.append({"pair": pair, "entry_us": entry_us, "exit_us": exit_us,
                          "date_utc": datetime.fromtimestamp(entry_us / 1e6, timezone.utc).date().isoformat(),
                          "funding_covered": observed is not None,
                          "funding_timestamp_us": observed.timestamp_us if observed else None,
                          "funding_interval_hours": observed.interval_hours if observed else None,
                          "funding_rate": observed.rate if observed else None,
                          "selected": observed is not None and observed.rate < 0,
                          "gross_return": payoff(entry_price, exit_price, 0, 0),
                          "base_return": payoff(entry_price, exit_price, .0005),
                          "stress_return": payoff(entry_price, exit_price, .0015)})
        controls = {cost: fmean(r[f"{cost}_return"] for r in group) for cost in ("gross", "base", "stress")}
        for row in group:
            for cost in ("gross", "base", "stress"):
                row[f"{cost}_basket_return"] = controls[cost]
                row[f"{cost}_advantage"] = row[f"{cost}_return"] - controls[cost]
            output.append(row)
    return output


def describe(rows: list[dict]) -> dict:
    chosen = [row for row in rows if row["selected"]]
    result = {"scheduled_asset_observations": len(rows),
              "funding_coverage": sum(r["funding_covered"] for r in rows)/len(rows) if rows else 0,
              "negative_observations": len(chosen),
              "opportunity_dates_utc": len({r["date_utc"] for r in chosen}),
              "negative_by_pair": {p: sum(r["pair"] == p for r in chosen) for p in PAIRS},
              "coverage_by_pair": {p: fmean(r["funding_covered"] for r in rows if r["pair"] == p)
                                   if any(r["pair"] == p for r in rows) else 0 for p in PAIRS}}
    for cost in ("gross", "base", "stress"):
        values = [r[f"{cost}_return"] for r in chosen]
        result[cost] = {"mean_return": fmean(values) if values else None,
                        "median_return": median(values) if values else None,
                        "mean_basket_advantage": fmean(r[f"{cost}_advantage"] for r in chosen) if values else None,
                        "win_fraction": fmean(v > 0 for v in values) if values else None,
                        "worst_isolated_return": min(values) if values else None}
    return result


def percentile(values: list[float], q: float) -> float:
    if not values or not 0 <= q <= 1:
        raise ValueError("invalid percentile input")
    ordered = sorted(values)
    position = (len(ordered)-1)*q
    lower, upper = math.floor(position), math.ceil(position)
    return ordered[lower] + (ordered[upper]-ordered[lower])*(position-lower)


def bootstrap(rows: list[dict], start_us: int, end_us: int, *, repetitions: int = 2000, seed: int = 20261002) -> dict:
    if start_us % DAY_US or end_us % DAY_US or end_us <= start_us or repetitions < 1:
        raise ValueError("invalid bootstrap calendar bounds or repetitions")
    number_days = (end_us-start_us)//DAY_US
    # Each date is one cluster, including all coins/slots and zero-event dates.
    daily = [[0.0, 0.0, 0] for _ in range(number_days)]
    for row in rows:
        index = (row["entry_us"]-start_us)//DAY_US
        if not 0 <= index < number_days:
            raise ValueError("bootstrap observation outside date grid")
        if row["selected"]:
            daily[index][0] += row["stress_return"]
            daily[index][1] += row["stress_advantage"]
            daily[index][2] += 1
    rng, mean_samples, advantage_samples = random.Random(seed), [], []
    for _ in range(repetitions):
        sampled_days = []
        while len(sampled_days) < number_days:
            first = rng.randrange(number_days)
            sampled_days.extend((first+j) % number_days for j in range(7))
        aggregates = [math.fsum(daily[i][k] for i in sampled_days[:number_days]) for k in range(3)]
        if aggregates[2]:
            mean_samples.append(aggregates[0]/aggregates[2])
            advantage_samples.append(aggregates[1]/aggregates[2])
    bounds = lambda values: [percentile(values, .025), percentile(values, .975)] if values else [None, None]
    return {"calendar_days": number_days, "block_days": 7, "repetitions": repetitions,
            "seed": seed, "valid_replicates": len(mean_samples),
            "stress_mean_interval": bounds(mean_samples), "stress_advantage_interval": bounds(advantage_samples)}


def assess(reports: dict, uncertainty: dict) -> dict:
    if set(reports) != {p for p, _, _ in periods("screen")}:
        raise ValueError("incomplete or unexpected funding-screen periods")
    quarter = reports["quarter"]
    positive = lambda v: isinstance(v, (int, float)) and math.isfinite(v) and v > 0
    windows = [p for p in reports if "_" in p]
    gates = {
        "funding_coverage_at_least_99_percent": quarter["funding_coverage"] >= .99 and all(v >= .99 for v in quarter["coverage_by_pair"].values()),
        "enough_observations_dates_and_assets": quarter["negative_observations"] >= 60 and quarter["opportunity_dates_utc"] >= 30 and sum(n >= 10 for n in quarter["negative_by_pair"].values()) >= 3,
        "stress_profit_and_relative_advantage_with_positive_lower_bounds": (
            positive(quarter["stress"]["mean_return"]) and positive(quarter["stress"]["mean_basket_advantage"])
            and uncertainty["valid_replicates"] >= .95*uncertainty["repetitions"]
            and positive(uncertainty["stress_mean_interval"][0]) and positive(uncertainty["stress_advantage_interval"][0])),
        "two_positive_stress_months": sum(positive(reports[m]["stress"]["mean_return"]) for m in ("2025-01", "2025-02", "2025-03")) >= 2,
        "four_windows_with_eight_opportunity_dates": sum(reports[w]["opportunity_dates_utc"] >= 8 for w in windows) >= 4,
    }
    return {"gates": gates, "signal_passed_feasibility": all(gates.values()),
            "portfolio_candidate_implemented": False, "strategy_approved_for_live": False,
            "qualification_verified": False, "validation_data_opened": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spot", type=Path, required=True)
    parser.add_argument("--funding", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if hashlib.sha256((root/"FUNDING_SIGNAL_PLAN.md").read_bytes()).hexdigest() != PLAN_SHA256:
        raise ValueError("funding signal plan fingerprint changed")
    if args.output.exists():
        raise ValueError("use a new output directory; do not overwrite research")
    paths, inputs = {}, []
    for pair in PAIRS:
        symbol = pair.split("/")[0]+"USDT"
        paths[pair] = {
            "spot": [args.spot/f"{symbol}-5m-{m}.zip" for m in MONTHS],
            "funding": [args.funding/f"{symbol}-fundingRate-{m}.zip" for m in MONTHS]}
        for kind, files in paths[pair].items():
            for path in files:
                inputs.append({"kind": kind, "file": path.name, "sha256": hashlib.sha256(verified_payload(path)).hexdigest()})
    data = {p: load_candles(files["spot"]) for p, files in paths.items()}
    funding = {p: load_funding(files["funding"]) for p, files in paths.items()}
    rows = panel(data, funding, START, END)
    reports = {label: describe([r for r in rows if stamp(first) <= r["entry_us"] and r["exit_us"] < stamp(last)])
               for label, first, last in periods("screen")}
    uncertainty = bootstrap(rows, START, END)
    verdict = assess(reports, uncertainty)
    manifest = {"created_at": datetime.now(timezone.utc).isoformat(), "plan_sha256": PLAN_SHA256,
                "screening_spot_data_previously_inspected": True, "inputs": inputs,
                "signal": "last_funding_rate < 0", "lag_seconds": 300, "horizon_seconds": 28800,
                "funding_records": {p: len(funding[p]) for p in PAIRS},
                "source_sha256": {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in sorted(root.glob("src/roostoo_bot/*.py"))}}
    args.output.mkdir(parents=True)
    (args.output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    (args.output/"observations.jsonl").write_text("".join(json.dumps(row, allow_nan=False)+"\n" for row in rows))
    result = {"reports": reports, "uncertainty": uncertainty, "verdict": verdict}
    (args.output/"results.json").write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")
    for label, report in reports.items():
        print(label, json.dumps({k: report[k] for k in ("negative_observations", "opportunity_dates_utc", "gross", "stress")}), flush=True)
    print(json.dumps(verdict, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
