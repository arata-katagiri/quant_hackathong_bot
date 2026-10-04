"""Read-only diagnostics of saved activity proxies; never a strategy or orders."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .forecast_research import periods as forecast_periods
from .funding_research import DAY_US
from .portfolio import HKT
from .research import stamp
from .vol_research import periods as screen_periods

SOURCES = {
    "summary.json": {"baseline", "buffered_trend", "breakout"},
    "pullback_summary.json": {"pullback"},
    "basket_summary.json": {"pullback_basket"},
    "vol_summary.json": {"vol_momentum"},
    "relative_summary.json": {"relative_strength"},
}
METRICS = ("total_return", "max_drawdown", "active_days_utc", "active_days_hkt", "turnover", "fees", "trades")


def portfolio_windows(rows: list[dict], candidates: set[str]) -> list[dict]:
    keyed = {}
    for row in rows:
        if row["strategy"] not in candidates or row["end_us"]-row["start_us"]+1 != 14*DAY_US:
            continue
        key = (row["strategy"], row["cost"], row["start_us"], row["end_us"])
        if key in keyed:
            if any(keyed[key][k] != row[k] for k in METRICS):
                raise ValueError("conflicting duplicate portfolio intervals")
            keyed[key]["aliases"].append(row["period"])
        else:
            keyed[key] = {k: row[k] for k in (*METRICS, "strategy", "cost", "start_us", "end_us")}
            keyed[key]["aliases"] = [row["period"]]
    return [keyed[k] for k in sorted(keyed)]


def summarize_windows(rows: list[dict]) -> list[dict]:
    output = []
    for strategy, cost in sorted({(r["strategy"], r["cost"]) for r in rows}):
        selected = [r for r in rows if (r["strategy"], r["cost"]) == (strategy, cost)]
        record = dict(strategy=strategy, cost=cost, windows=len(selected),
                      positive=sum(r["total_return"] > 0 for r in selected))
        for zone in ("utc", "hkt"):
            active = lambda r: r["active_days_"+zone] >= 8
            record[zone] = dict(activity=sum(active(r) for r in selected),
                positive_and_active=sum(r["total_return"] > 0 and active(r) for r in selected),
                positive_active_and_drawdown=sum(r["total_return"] > 0 and active(r) and r["max_drawdown"] <= .08 for r in selected))
        output.append(record)
    return output


def event_calendar(rows: list[dict], start: int, end: int) -> dict:
    if start >= end or start % DAY_US or end % DAY_US:
        raise ValueError("invalid activity calendar bounds")
    selected = []
    for row in rows:
        if (type(row["entry_us"]) is not int or type(row["exit_us"]) is not int
                or row["exit_us"] <= row["entry_us"] or type(row["selected"]) is not bool):
            raise ValueError("invalid hypothetical event record")
        if row["selected"] and start <= row["entry_us"] and row["exit_us"] < end:
            selected.append(row)
    result = dict(selected_observations=len(selected), start_us=start, end_exclusive_us=end,
                  executable_portfolio=False, netting_applied=False, qualification_verified=False)
    for zone, tz in (("utc", timezone.utc), ("hkt", HKT)):
        date = lambda t: datetime.fromtimestamp(t/1e6, tz).date().isoformat()
        entries = {date(r["entry_us"]) for r in selected}
        events = entries | {date(r["exit_us"]) for r in selected}
        result[zone] = dict(entry_dates=len(entries), unnetted_entry_exit_dates=len(events),
                            entry_date_list=sorted(entries), unnetted_date_list=sorted(events))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.output.exists():
        raise ValueError("use a new output directory")
    release = json.loads((root/"research/release_manifest.json").read_text())
    inputs, windows, count = [], [], 0
    for filename, candidates in SOURCES.items():
        relative = "research/"+filename
        path = root/relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if release["file_sha256"][relative] != digest:
            raise ValueError("saved portfolio report fingerprint differs")
        rows = json.loads(path.read_text())
        count += len(rows)
        windows.extend(portfolio_windows(rows, candidates))
        inputs.append(dict(file=relative, sha256=digest))
    if count != 440 or len(windows) != 96:
        raise ValueError("unexpected existing scenario/window inventory")
    signal_rows = {}
    specs = (("funding", "funding_screen", "opportunity_dates_utc"),
             ("trade_flow", "trade_flow_screen", "opportunity_dates_utc"),
             ("forecast", "forecast_screen_verified", "dates"))
    for name, directory, count_key in specs:
        source = root/"data"/directory
        rows = [json.loads(line) for line in (source/"observations.jsonl").read_text().splitlines()]
        results = json.loads((source/"results.json").read_text())
        tracked = root/"research"/(name+"_summary.json")
        if hashlib.sha256(tracked.read_bytes()).hexdigest() != release["file_sha256"][str(tracked.relative_to(root))]:
            raise ValueError("saved information report fingerprint differs")
        if json.loads(tracked.read_text()) != results:
            raise ValueError("observation reports disagree with tracked results")
        periods = forecast_periods() if name == "forecast" else [(p, stamp(a), stamp(b)) for p, a, b in screen_periods("screen")]
        signal_rows[name] = []
        for period, first, last in periods:
            if last-first != 14*DAY_US:
                continue
            result = event_calendar(rows, first, last)
            if result["utc"]["entry_dates"] != results["reports"][period][count_key]:
                raise ValueError("reconstructed entry-date count differs")
            signal_rows[name].append(dict(period=period, **result))
        for file in (source/"observations.jsonl", source/"results.json", tracked):
            inputs.append(dict(file=str(file.relative_to(root)), sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
    aggregates = {name: dict(windows=len(rows),
        entry_dates_at_least_eight=sum(r["utc"]["entry_dates"] >= 8 for r in rows),
        unnetted_dates_at_least_eight=sum(r["utc"]["unnetted_entry_exit_dates"] >= 8 for r in rows))
        for name, rows in signal_rows.items()}
    output = dict(portfolio_source_rows=count, unique_candidate_cost_windows=len(windows),
        portfolio_summary=summarize_windows(windows), portfolio_windows=windows,
        information_summary=aggregates, information_windows=signal_rows,
        prior_verdicts_changed=False, strategy_approved=False, qualification_verified=False)
    manifest = dict(inputs=inputs, plan_sha256=hashlib.sha256((root/"ACTIVITY_AUDIT_PLAN.md").read_bytes()).hexdigest(),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    args.output.mkdir(parents=True)
    for name, value in (("results", output), ("manifest", manifest)):
        (args.output/f"{name}.json").write_text(json.dumps(value, indent=2, allow_nan=False)+"\n")
    print(json.dumps(dict(portfolios=output["portfolio_summary"], information=aggregates),indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
