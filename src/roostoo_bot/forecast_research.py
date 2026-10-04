"""Frozen six-feature ridge screen. Local archives only; no trading integration."""
from __future__ import annotations

import argparse
import calendar
import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
from statistics import fmean, pstdev
import zipfile

from .basket_research import PAIRS
from .download_data import archive_parts
from .funding_data import verified_payload
from .funding_research import DAY_US, bootstrap, payoff
from .portfolio_backtest import BAR_US
from .research import stamp
from .trade_flow import parse_rows

PLAN_SHA256 = "79639532752370666391452301efbf3dab828d6a3e9ae91bfd0ded94723d8a9b"
AMENDMENT_SHA256 = "1ac1d8124eb13d3a532607ec2d3b7a91432461bef4d68fa7a24f3e940203d70b"
MONTHS = ("2020-12", *(f"{y}-{m:02}" for y in range(2021, 2025) for m in range(1, 13)))
START, END = stamp("2022-01-01"), stamp("2025-01-01")
BREAK_EVEN = (1.0015 * 1.001) / (.9985 * .999) - 1
DIMENSIONS = 6


@dataclass(frozen=True)
class Day:
    start_us: int
    close: float | None
    entry: float | None
    quote: float
    bought: float
    missing_bars: int
    rejected_bars: int = 0


def load_month(path: Path) -> list[Day]:
    symbol, _, kind = archive_parts(path.name)
    if kind != "monthly" or symbol not in {p.split('/')[0]+'USDT' for p in PAIRS}:
        raise ValueError("unexpected forecast archive")
    month = path.stem[-7:]
    if month not in MONTHS:
        raise ValueError("archive outside frozen forecast period")
    start = stamp(month+"-01")
    count = calendar.monthrange(int(month[:4]), int(month[5:]))[1]
    groups = [[] for _ in range(count)]
    rejected = [0 for _ in range(count)]
    previous = start-BAR_US
    with zipfile.ZipFile(io.BytesIO(verified_payload(path))) as archive:
        if archive.namelist() != [path.stem+".csv"] or archive.infolist()[0].file_size > 50_000_000:
            raise ValueError("unexpected forecast archive contents")
        with archive.open(archive.infolist()[0]) as source:
            for raw in csv.reader(io.TextIOWrapper(source, encoding="utf-8")):
                if not raw or raw[0].lower() in {"open time", "open_time", "timestamp"}:
                    continue
                if len(raw) != 12:
                    raise ValueError("unexpected forecast schema")
                timestamp = int(raw[0])
                timestamp *= 1000 if timestamp < 10**15 else 1
                if timestamp % BAR_US or not start <= timestamp < start+count*DAY_US or timestamp <= previous:
                    raise ValueError("out-of-month, duplicate or unordered forecast bar")
                previous = timestamp
                try:
                    row = parse_rows([raw])[0]
                except ValueError as error:
                    if str(error) != "invalid kline close timestamp":
                        raise
                    # Validate remaining fields without ever admitting this bar.
                    # The substitute is ONLY a validation aid, not repaired data.
                    unit = 1000 if int(raw[0]) < 10**15 else 1
                    checked = raw[:]
                    checked[6] = str((timestamp+BAR_US-unit)//unit)
                    parse_rows([checked])
                    rejected[(timestamp-start)//DAY_US] += 1
                    continue
                groups[(row.open_time_us-start)//DAY_US].append((row, float(raw[1]), float(raw[4])))
    days = []
    for offset, group in enumerate(groups):
        boundary = start+offset*DAY_US
        days.append(Day(boundary,
            next((close for row, _, close in group if row.open_time_us == boundary+DAY_US-BAR_US), None),
            next((price for row, price, _ in group if row.open_time_us == boundary+BAR_US), None),
            math.fsum(row.total_quote for row, _, _ in group),
            math.fsum(row.taker_buy_quote for row, _, _ in group), 288-len(group), rejected[offset]))
    return days


def features(history: list[Day], cutoff: int) -> list[float] | None:
    if len(history) != 31 or any(d.start_us != cutoff-(31-i)*DAY_US for i, d in enumerate(history)):
        raise ValueError("feature requires 31 contiguous prior days")
    if any(d.missing_bars or d.close is None or d.quote <= 0 for d in history):
        return None
    if any(not math.isfinite(v) or v <= 0 for d in history for v in (d.close, d.quote)):
        raise ValueError("invalid daily price or volume")
    if any(not math.isfinite(d.bought) or not 0 <= d.bought <= d.quote for d in history):
        raise ValueError("invalid daily buy volume")
    closes = [d.close for d in history]
    daily_returns = [math.log(b/a) for a, b in zip(closes[-21:-1], closes[-20:])]
    return [math.log(closes[-1]/closes[-1-h]) for h in (1, 7, 30)] + [
        pstdev(daily_returns), math.log(history[-1].quote/fmean(d.quote for d in history[-21:-1])),
        (2*history[-1].bought-history[-1].quote)/history[-1].quote]


def observations(data: dict[str, list[Day]]) -> list[dict]:
    if set(data) != set(PAIRS):
        raise ValueError("forecast data must match fixed universe")
    times = [d.start_us for d in data[PAIRS[0]]]
    if len(times) < 33 or any(b-a != DAY_US for a, b in zip(times, times[1:])):
        raise ValueError("missing or duplicated daily calendar rows")
    if any([d.start_us for d in data[p]] != times for p in PAIRS):
        raise ValueError("unaligned daily calendar")
    rows = []
    for i in range(31, len(times)-1):
        group = []
        for pair in PAIRS:
            days = data[pair]
            first, last = days[i].entry, days[i+1].entry
            covered = first is not None and last is not None
            row = dict(pair=pair, entry_us=times[i]+BAR_US, exit_us=times[i+1]+BAR_US,
                       feature_cutoff_us=times[i], x=features(days[i-31:i], times[i]),
                       date_utc=datetime.fromtimestamp(times[i]/1e6, timezone.utc).date().isoformat())
            for cost, slip, fee in (("gross", 0, 0), ("base", .0005, .001), ("stress", .0015, .001)):
                row[cost+"_return"] = payoff(first, last, slip, fee) if covered else None
            group.append(row)
        group_covered = all(r["gross_return"] is not None for r in group)
        for row in group:
            row["basket_covered"] = group_covered
            for cost in ("gross", "base", "stress"):
                basket = fmean(r[cost+"_return"] for r in group) if group_covered else None
                row[cost+"_advantage"] = row[cost+"_return"]-basket if group_covered else None
            rows.append(row)
    return rows


def solve(matrix: list[list[float]], target: list[float]) -> list[float]:
    n = len(target)
    if not n or len(matrix) != n or any(len(row) != n for row in matrix):
        raise ValueError("invalid ridge matrix")
    augmented = [list(row)+[y] for row, y in zip(matrix, target)]
    if any(not math.isfinite(v) for row in augmented for v in row):
        raise ValueError("nonfinite ridge matrix")
    for i in range(n):
        pivot = max(range(i, n), key=lambda j: abs(augmented[j][i]))
        augmented[i], augmented[pivot] = augmented[pivot], augmented[i]
        divisor = augmented[i][i]
        if abs(divisor) < 1e-12:
            raise ValueError("singular ridge matrix")
        augmented[i] = [v/divisor for v in augmented[i]]
        for j in range(n):
            if j != i:
                multiplier = augmented[j][i]
                augmented[j] = [a-multiplier*b for a, b in zip(augmented[j], augmented[i])]
    return [row[-1] for row in augmented]


@dataclass(frozen=True)
class Model:
    means: list[float]
    scales: list[float]
    coefficients: list[float]
    intercept: float
    training_mean: float

    def standardized(self, x: list[float]) -> list[float]:
        if len(x) != len(self.means) or any(not math.isfinite(v) for v in x):
            raise ValueError("invalid prediction feature vector")
        return [max(-5, min(5, (v-m)/s)) for v, m, s in zip(x, self.means, self.scales)]

    def predict(self, x: list[float]) -> float:
        return self.intercept+math.fsum(a*b for a, b in zip(self.standardized(x), self.coefficients))


def fit(xs: list[list[float]], ys: list[float]) -> Model:
    if not xs or len(xs) != len(ys) or any(len(x) != DIMENSIONS for x in xs):
        raise ValueError("invalid training dimensions")
    if any(not math.isfinite(v) for x in xs for v in x) or any(not math.isfinite(y) for y in ys):
        raise ValueError("nonfinite training observation")
    means = [fmean(x[j] for x in xs) for j in range(DIMENSIONS)]
    scales = [pstdev(x[j] for x in xs) for j in range(DIMENSIONS)]
    scales = [s if s >= 1e-12 else 1.0 for s in scales]
    model = Model(means, scales, [], 0.0, fmean(ys))
    zs = [model.standardized(x) for x in xs]
    center = [fmean(z[j] for z in zs) for j in range(DIMENSIONS)]
    clipped = [max(-.2, min(.2, y)) for y in ys]
    target_mean = fmean(clipped)
    covariance = [[fmean((z[j]-center[j])*(z[k]-center[k]) for z in zs)+(.1 if j == k else 0)
                   for k in range(DIMENSIONS)] for j in range(DIMENSIONS)]
    rhs = [fmean((z[j]-center[j])*(y-target_mean) for z, y in zip(zs, clipped)) for j in range(DIMENSIONS)]
    coefficients = solve(covariance, rhs)
    return Model(means, scales, coefficients, target_mean-math.fsum(a*b for a, b in zip(center, coefficients)), model.training_mean)


def training_rows(rows: list[dict], fit_us: int) -> list[dict]:
    return [r for r in rows if stamp("2021-01-01") <= r["entry_us"] and r["exit_us"] < fit_us
            and r["x"] is not None and r["gross_return"] is not None]


def forecast(rows: list[dict], start: int = START, end: int = END) -> tuple[list[dict], dict]:
    output, models = [], {}
    for row in rows:
        if not start <= row["entry_us"] or not row["exit_us"] < end:
            continue
        month = row["date_utc"][:7]
        fit_us = stamp(month+"-01")
        if month not in models:
            training = training_rows(rows, fit_us)
            dates = len({r["date_utc"] for r in training})
            model = fit([r["x"] for r in training], [r["gross_return"] for r in training]) if len(training) >= 1500 and dates >= 300 else None
            models[month] = dict(fit_us=fit_us, count=len(training), dates=dates,
                                 max_training_exit_us=max((r["exit_us"] for r in training), default=None),
                                 model=asdict(model) if model else None)
        record = models[month]
        model = Model(**record["model"]) if record["model"] else None
        prediction = model.predict(row["x"]) if model and row["x"] is not None else None
        scorable = prediction is not None and row["gross_return"] is not None and row["basket_covered"]
        output.append(dict(row, forecast=prediction, fit_us=fit_us, scorable=scorable,
                           training_mean=model.training_mean if model else None,
                           signal=bool(prediction is not None and prediction > BREAK_EVEN),
                           selected=bool(scorable and prediction > BREAK_EVEN)))
    return output, models


def periods() -> list[tuple[str, int, int]]:
    output = [("full", START, END)]
    for year in range(2022, 2025):
        output.append((str(year), stamp(f"{year}-01-01"), stamp(f"{year+1}-01-01")))
        for month in range(1, 13):
            prefix = f"{year}-{month:02}"
            next_month = f"{year+1}-01-01" if month == 12 else f"{year}-{month+1:02}-01"
            output.append((prefix, stamp(prefix+"-01"), stamp(next_month)))
            for day in (1, 15):
                first = stamp(prefix+f"-{day:02}")
                output.append((prefix+f"_{day:02}_{day+13:02}", first, first+14*DAY_US))
    return output


def describe(rows: list[dict]) -> dict:
    selected, scored = [r for r in rows if r["selected"]], [r for r in rows if r["scorable"]]
    result = dict(scheduled=len(rows), scorable=len(scored), coverage=len(scored)/len(rows) if rows else 0,
                  selected=len(selected), dates=len({r["date_utc"] for r in selected}),
                  selected_by_pair={p: sum(r["pair"] == p for r in selected) for p in PAIRS},
                  coverage_by_pair={p: fmean(r["scorable"] for r in rows if r["pair"] == p)
                                    if any(r["pair"] == p for r in rows) else 0 for p in PAIRS})
    for cost in ("gross", "base", "stress"):
        result[cost] = dict(mean=fmean(r[cost+"_return"] for r in selected) if selected else None,
                            advantage=fmean(r[cost+"_advantage"] for r in selected) if selected else None,
                            wins=fmean(r[cost+"_return"] > 0 for r in selected) if selected else None,
                            worst=min((r[cost+"_return"] for r in selected), default=None))
    result["mse"] = {key: fmean((r[key]-r["gross_return"])**2 for r in scored) if scored else None
                     for key in ("forecast", "training_mean")}
    result["mse"]["zero"] = fmean(r["gross_return"]**2 for r in scored) if scored else None
    return result


def assess(reports: dict, uncertainty: dict) -> dict:
    if set(reports) != {name for name, _, _ in periods()}:
        raise ValueError("incomplete forecast reports")
    full = reports["full"]
    positive = lambda v: v is not None and math.isfinite(v) and v > 0
    years = [reports[str(y)] for y in range(2022, 2025)]
    gates = dict(
        coverage=full["coverage"] >= .95 and all(v >= .95 for v in full["coverage_by_pair"].values()) and all(r["coverage"] >= .9 for r in years),
        sample_size=full["selected"] >= 300 and full["dates"] >= 150 and sum(v >= 50 for v in full["selected_by_pair"].values()) >= 3,
        stress_profit_and_advantage=positive(full["stress"]["mean"]) and positive(full["stress"]["advantage"])
            and uncertainty["valid_replicates"] >= .95*uncertainty["repetitions"]
            and positive(uncertainty["stress_mean_interval"][0]) and positive(uncertainty["stress_advantage_interval"][0]),
        years_and_months=sum(positive(r["stress"]["mean"]) for r in years) >= 2
            and sum(positive(r["stress"]["mean"]) for p, r in reports.items() if len(p) == 7) >= 24,
        activity=sum(r["dates"] >= 8 for p, r in reports.items() if "_" in p) >= 48,
        forecast_error=sum(r["mse"]["forecast"] is not None and r["mse"]["forecast"] < r["mse"]["training_mean"] for r in years) >= 2)
    return dict(gates=gates, signal_passed=all(gates.values()), portfolio_implemented=False,
                strategy_approved=False, reserved_validation_opened=False, qualification_verified=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if hashlib.sha256((root/"FORECAST_PLAN.md").read_bytes()).hexdigest() != PLAN_SHA256:
        raise ValueError("forecast plan changed")
    if hashlib.sha256((root/"FORECAST_DATA_AMENDMENT.md").read_bytes()).hexdigest() != AMENDMENT_SHA256:
        raise ValueError("forecast data amendment changed")
    if args.output.exists():
        raise ValueError("use a new output directory")
    inputs, data = [], {}
    for pair in PAIRS:
        data[pair] = []
        for month in MONTHS:
            path = args.market/f"{pair.split('/')[0]}USDT-5m-{month}.zip"
            inputs.append(dict(file=path.name, sha256=hashlib.sha256(verified_payload(path)).hexdigest()))
            data[pair].extend(load_month(path))
        print("validated", pair, "daily rows=", len(data[pair]), flush=True)
    rows, models = forecast(observations(data))
    reports = {name: describe([r for r in rows if first <= r["entry_us"] and r["exit_us"] < last])
               for name, first, last in periods()}
    uncertainty = bootstrap(rows, START, END)
    verdict = assess(reports, uncertainty)
    manifest = dict(created_at=datetime.now(timezone.utc).isoformat(), plan_sha256=PLAN_SHA256,
        amendment_sha256=AMENDMENT_SHA256, inputs=inputs,
        missing_bars={p: sum(d.missing_bars for d in days) for p, days in data.items()},
        rejected_bars={p: sum(d.rejected_bars for d in days) for p, days in data.items()},
        absent_bars={p: sum(d.missing_bars-d.rejected_bars for d in days) for p, days in data.items()},
        incomplete_days={p: sum(bool(d.missing_bars) for d in days) for p, days in data.items()},
        source_sha256={str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in sorted(root.glob("src/roostoo_bot/*.py"))})
    args.output.mkdir(parents=True)
    for name, value in (("manifest", manifest), ("models", models),
                        ("results", dict(reports=reports, uncertainty=uncertainty, verdict=verdict))):
        (args.output/f"{name}.json").write_text(json.dumps(value, indent=2, allow_nan=False)+"\n")
    (args.output/"observations.jsonl").write_text("".join(json.dumps(r, allow_nan=False)+"\n" for r in rows))
    for p in ("full", "2022", "2023", "2024"):
        print(p, json.dumps(reports[p]), flush=True)
    print(json.dumps(verdict, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
