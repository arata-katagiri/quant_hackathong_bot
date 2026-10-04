"""Frozen daily trade-imbalance screen; local data only, no trading integration."""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
from statistics import fmean, median
import zipfile

from .backtest import Candle, _parse_candle_rows, load_candles
from .basket_research import PAIRS
from .download_data import archive_parts
from .funding_data import verified_payload
from .funding_research import DAY_US, END, START, bootstrap, payoff
from .portfolio_backtest import BAR_US, validate_alignment
from .research import stamp
from .vol_research import periods

PLAN_SHA256 = "1acaeb76647241ed1087bc07198c2c07af43da188d37c1b121fe1568d2151ac1"
MONTHS = ("2024-12", "2025-01", "2025-02", "2025-03")
ROUNDING_TOLERANCE = 1e-8


@dataclass(frozen=True)
class TradeFlow:
    open_time_us: int
    total_quote: float
    taker_buy_quote: float


def _volumes(total: float, bought: float) -> tuple[float, float]:
    if (not math.isfinite(total) or not math.isfinite(bought) or min(total, bought) < 0
            or bought > total + ROUNDING_TOLERANCE):
        raise ValueError("invalid total/taker-buy volume")
    return total, min(total, bought)


def parse_rows(rows) -> list[TradeFlow]:
    output = []
    for row in rows:
        if not row or row[0].lower() in {"open time", "open_time", "timestamp"}:
            continue
        if len(row) != 12:
            raise ValueError("expected 12 Binance kline fields for trade flow")
        candle = _parse_candle_rows([row])[0]
        unit = 1000 if int(row[0]) < 10**15 else 1
        if int(row[6])*unit != candle.open_time_us + BAR_US - unit:
            raise ValueError("invalid kline close timestamp")
        base, base_buy = _volumes(float(row[5]), float(row[9]))
        quote, quote_buy = _volumes(float(row[7]), float(row[10]))
        if (base == 0) != (quote == 0) or (base_buy == 0) != (quote_buy == 0):
            raise ValueError("base/quote zero-volume mismatch")
        trade_count = int(row[8])
        if trade_count < 0 or (trade_count == 0 and base > 0):
            raise ValueError("invalid trade count")
        output.append(TradeFlow(candle.open_time_us, quote, quote_buy))
    return output


def load_trade_flow(paths: list[Path]) -> list[TradeFlow]:
    output, symbols = [], set()
    for path in paths:
        symbol, _, _ = archive_parts(path.name)
        symbols.add(symbol)
        with zipfile.ZipFile(io.BytesIO(verified_payload(path))) as archive:
            if archive.namelist() != [path.stem+".csv"] or archive.infolist()[0].file_size > 50_000_000:
                raise ValueError("unexpected trade-flow archive contents")
            with archive.open(archive.infolist()[0]) as source:
                output.extend(parse_rows(csv.reader(io.TextIOWrapper(source, encoding="utf-8"))))
    if len(symbols) != 1 or not output:
        raise ValueError("trade flow requires one nonempty asset series")
    output.sort(key=lambda row: row.open_time_us)
    if any(b.open_time_us-a.open_time_us != BAR_US for a, b in zip(output, output[1:])):
        raise ValueError("trade-flow bars missing or duplicated")
    return output


def imbalance(window: list[TradeFlow], cutoff_us: int) -> float | None:
    if len(window) != 288 or cutoff_us % BAR_US:
        raise ValueError("trade-flow feature requires one exact completed day")
    for i, row in enumerate(window):
        if row.open_time_us != cutoff_us-DAY_US+i*BAR_US:
            raise ValueError("feature includes wrong, missing or future bars")
        _volumes(row.total_quote, row.taker_buy_quote)
    total = math.fsum(row.total_quote for row in window)
    bought = math.fsum(min(row.total_quote, row.taker_buy_quote) for row in window)
    return (2*bought-total)/total if total > 0 else None


def panel(data: dict[str, list[Candle]], flows: dict[str, list[TradeFlow]], start_us: int, end_us: int) -> list[dict]:
    validate_alignment(data, PAIRS)
    if set(flows) != set(PAIRS) or start_us % DAY_US or end_us % DAY_US or end_us <= start_us:
        raise ValueError("invalid trade-flow universe or bounds")
    times = [c.open_time_us for c in data[PAIRS[0]]]
    if any([row.open_time_us for row in flows[p]] != times for p in PAIRS):
        raise ValueError("flow and price timestamps do not match")
    index = {t: i for i, t in enumerate(times)}
    output = []
    for entry_us in range(start_us+BAR_US, end_us-DAY_US, DAY_US):
        exit_us, cutoff_us = entry_us+DAY_US, entry_us-BAR_US
        if any(t not in index for t in (entry_us, exit_us, cutoff_us)):
            raise ValueError("missing exact feature/entry/exit boundary")
        first = index[cutoff_us]-288
        if first < 0:
            raise ValueError("insufficient previous-day warm-up")
        group = []
        for pair in PAIRS:
            value = imbalance(flows[pair][first:index[cutoff_us]], cutoff_us)
            entry_price, exit_price = data[pair][index[entry_us]].open, data[pair][index[exit_us]].open
            group.append({"pair": pair, "entry_us": entry_us, "exit_us": exit_us,
                          "feature_start_us": cutoff_us-DAY_US, "feature_end_exclusive_us": cutoff_us,
                          "date_utc": datetime.fromtimestamp(entry_us/1e6, timezone.utc).date().isoformat(),
                          "flow_covered": value is not None, "imbalance": value,
                          "selected": value is not None and value > 0,
                          "gross_return": payoff(entry_price, exit_price, 0, 0),
                          "base_return": payoff(entry_price, exit_price, .0005),
                          "stress_return": payoff(entry_price, exit_price, .0015)})
        controls = {cost: fmean(r[f"{cost}_return"] for r in group) for cost in ("gross", "base", "stress")}
        for row in group:
            for cost in controls:
                row[f"{cost}_basket_return"] = controls[cost]
                row[f"{cost}_advantage"] = row[f"{cost}_return"] - controls[cost]
            output.append(row)
    return output


def describe(rows: list[dict]) -> dict:
    selected = [r for r in rows if r["selected"]]
    result = {"scheduled_asset_observations": len(rows),
              "feature_coverage": fmean(r["flow_covered"] for r in rows) if rows else 0,
              "selected_observations": len(selected),
              "opportunity_dates_utc": len({r["date_utc"] for r in selected}),
              "selected_by_pair": {p: sum(r["pair"] == p for r in selected) for p in PAIRS},
              "coverage_by_pair": {p: fmean(r["flow_covered"] for r in rows if r["pair"] == p)
                                   if any(r["pair"] == p for r in rows) else 0 for p in PAIRS}}
    for cost in ("gross", "base", "stress"):
        values = [r[f"{cost}_return"] for r in selected]
        result[cost] = {"mean_return": fmean(values) if values else None,
                        "median_return": median(values) if values else None,
                        "mean_basket_advantage": fmean(r[f"{cost}_advantage"] for r in selected) if values else None,
                        "win_fraction": fmean(v > 0 for v in values) if values else None,
                        "worst_isolated_return": min(values) if values else None}
    return result


def assess(reports: dict, uncertainty: dict) -> dict:
    if set(reports) != {p for p, _, _ in periods("screen")}:
        raise ValueError("incomplete or unexpected trade-flow periods")
    quarter = reports["quarter"]
    positive = lambda x: isinstance(x, (int, float)) and math.isfinite(x) and x > 0
    gates = {
        "feature_coverage_at_least_99_percent": quarter["feature_coverage"] >= .99 and all(v >= .99 for v in quarter["coverage_by_pair"].values()),
        "enough_observations_dates_and_assets": quarter["selected_observations"] >= 60 and quarter["opportunity_dates_utc"] >= 30 and sum(n >= 10 for n in quarter["selected_by_pair"].values()) >= 3,
        "stress_profit_and_relative_advantage_with_positive_lower_bounds": (
            positive(quarter["stress"]["mean_return"]) and positive(quarter["stress"]["mean_basket_advantage"])
            and uncertainty["valid_replicates"] >= .95*uncertainty["repetitions"]
            and positive(uncertainty["stress_mean_interval"][0]) and positive(uncertainty["stress_advantage_interval"][0])),
        "two_positive_stress_months": sum(positive(reports[m]["stress"]["mean_return"]) for m in ("2025-01", "2025-02", "2025-03")) >= 2,
        "four_windows_with_eight_opportunity_dates": sum(reports[p]["opportunity_dates_utc"] >= 8 for p in reports if "_" in p) >= 4,
    }
    return {"gates": gates, "signal_passed_feasibility": all(gates.values()),
            "portfolio_candidate_implemented": False, "strategy_approved_for_live": False,
            "qualification_verified": False, "validation_data_opened": False,
            "long_only_research": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if hashlib.sha256((root/"TRADE_FLOW_PLAN.md").read_bytes()).hexdigest() != PLAN_SHA256:
        raise ValueError("trade-flow plan fingerprint changed")
    if args.output.exists():
        raise ValueError("use a new output directory; do not overwrite research")
    paths, inputs = {}, []
    for pair in PAIRS:
        symbol = pair.split("/")[0]+"USDT"
        paths[pair] = [args.market/f"{symbol}-5m-{month}.zip" for month in MONTHS]
        inputs.extend({"file": p.name, "sha256": hashlib.sha256(verified_payload(p)).hexdigest()} for p in paths[pair])
    data = {p: load_candles(files) for p, files in paths.items()}
    flows = {p: load_trade_flow(files) for p, files in paths.items()}
    rows = panel(data, flows, START, END)
    reports = {name: describe([r for r in rows if stamp(first) <= r["entry_us"] and r["exit_us"] < stamp(last)])
               for name, first, last in periods("screen")}
    uncertainty = bootstrap(rows, START, END)
    verdict = assess(reports, uncertainty)
    manifest = {"created_at": datetime.now(timezone.utc).isoformat(), "plan_sha256": PLAN_SHA256,
                "screening_spot_data_previously_inspected": True, "inputs": inputs,
                "signal": "prior_completed_UTC_day_trade_imbalance > 0", "lag_seconds": 300, "horizon_seconds": 86400,
                "source_sha256": {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in sorted(root.glob("src/roostoo_bot/*.py"))}}
    args.output.mkdir(parents=True)
    (args.output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    (args.output/"observations.jsonl").write_text("".join(json.dumps(row, allow_nan=False)+"\n" for row in rows))
    (args.output/"results.json").write_text(json.dumps({"reports": reports, "uncertainty": uncertainty, "verdict": verdict}, indent=2, allow_nan=False)+"\n")
    for period, report in reports.items():
        print(period, "selected=", report["selected_observations"], "dates=", report["opportunity_dates_utc"],
              "gross=", report["gross"]["mean_return"], "stress=", report["stress"]["mean_return"], flush=True)
    print(json.dumps(verdict, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
