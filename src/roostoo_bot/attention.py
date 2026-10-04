"""Frozen Wikipedia long/cash experiment. Public download or offline simulation only."""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from statistics import fmean, median
from urllib.request import Request, urlopen

from .basket_research import RULES as BASKET_RULES
from .long_trend import DAY_US, block_intervals, load_inputs, periods
from .portfolio_backtest import BAR_US, ScheduledTarget, research_settings, simulate_portfolio, write_report
from .research import stamp

PLAN_SHA256 = "83ddeef2333e6e04e8107fda7b42891e3187ebbd162073ced7cb3cb4148ea1ec"
PAGES = {"BTC/USD": "Bitcoin", "ETH/USD": "Ethereum"}
PAIRS = tuple(PAGES)
RULES = {p: BASKET_RULES[p] for p in PAIRS}
STRATEGIES = ("attention", "price_contrarian", "constant_control", "cash", "buy_hold_equal_70")
USER_AGENT = "RoostooOfflineResearch/1.0 (https://github.com/arata-katagiri/quant_hackathong_bot) Python-urllib"


def requests():
    for pair, page in PAGES.items():
        for year in (2021, 2022, 2023, 2024):
            start = f"{year}1201" if year == 2021 else f"{year}0101"
            end = f"{year}1231"
            yield dict(pair=pair, page=page, first=start, last=end,
                file=f"{page}-{year}.json",
                url=f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia.org/all-access/user/{page}/daily/{start}/{end}")


def parse_counts(payload: bytes, page: str, first: str, last: str) -> dict[int, int]:
    """Missing rows remain missing; no interpolation, duplicate collapse or zero fill."""
    obj = json.loads(payload)
    if not isinstance(obj, dict) or not isinstance(obj.get("items"), list):
        raise ValueError("invalid attention response")
    start = datetime.strptime(first, "%Y%m%d").replace(tzinfo=timezone.utc)
    end = datetime.strptime(last, "%Y%m%d").replace(tzinfo=timezone.utc)
    result, previous = {}, None
    for row in obj["items"]:
        if not isinstance(row, dict) or any(row.get(k) != v for k, v in
            dict(project="en.wikipedia", article=page, granularity="daily", access="all-access", agent="user").items()):
            raise ValueError("attention metadata mismatch")
        raw, views = row.get("timestamp"), row.get("views")
        if not isinstance(raw, str) or len(raw) != 10 or not raw.isascii() or not raw.isdigit():
            raise ValueError("invalid attention timestamp")
        date = datetime.strptime(raw, "%Y%m%d%H").replace(tzinfo=timezone.utc)
        if date.hour or not start <= date <= end or (previous is not None and date <= previous):
            raise ValueError("attention dates unordered, duplicated or out of range")
        if type(views) is not int or views < 0:
            raise ValueError("invalid attention count")
        result[int(date.timestamp()*1e6)] = views
        previous = date
    return result


def verify_plan():
    root = Path(__file__).resolve().parents[2]
    if hashlib.sha256((root/"ATTENTION_PLAN.md").read_bytes()).hexdigest() != PLAN_SHA256:
        raise ValueError("frozen attention plan changed")
    return root


def download(output: Path):
    verify_plan()
    output.mkdir(parents=True, exist_ok=False)
    manifest = dict(plan_sha256=PLAN_SHA256, historical_first_seen_verified=False, inputs=[])
    for item in requests():
        request = Request(item["url"], headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        with urlopen(request, timeout=30) as response:
            payload = response.read(2_000_001)
            if len(payload) > 2_000_000:
                raise ValueError("attention response too large")
        counts = parse_counts(payload, item["page"], item["first"], item["last"])
        (output/item["file"]).write_bytes(payload)
        manifest["inputs"].append(dict(**item, sha256=hashlib.sha256(payload).hexdigest(),
            retrieved_at=datetime.now(timezone.utc).isoformat(), rows=len(counts),
            zero_rows=sum(v == 0 for v in counts.values())))
        (output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
        print("downloaded:", item["file"], "rows:", len(counts), flush=True)


def load_counts(directory: Path):
    manifest = json.loads((directory/"manifest.json").read_text())
    expected = list(requests())
    if manifest.get("plan_sha256") != PLAN_SHA256 or len(manifest.get("inputs", [])) != len(expected):
        raise ValueError("attention manifest incomplete or wrong plan")
    result = {p: {} for p in PAIRS}
    for item, entry in zip(expected, manifest["inputs"]):
        if any(entry.get(k) != v for k, v in item.items()):
            raise ValueError("attention inventory mismatch")
        payload = (directory/item["file"]).read_bytes()
        if hashlib.sha256(payload).hexdigest() != entry.get("sha256"):
            raise ValueError("attention snapshot checksum mismatch")
        counts = parse_counts(payload, item["page"], item["first"], item["last"])
        if len(counts) != entry.get("rows") or sum(v == 0 for v in counts.values()) != entry.get("zero_rows"):
            raise ValueError("attention coverage mismatch")
        if result[item["pair"]].keys() & counts.keys():
            raise ValueError("overlapping attention archives")
        result[item["pair"]].update(counts)
    return result, manifest


def schedules(counts, days, first, last):
    if set(counts) != set(PAIRS) or not set(PAIRS) <= set(days) or first % DAY_US or last % DAY_US or first >= last:
        raise ValueError("invalid attention calendar")
    targets = {s: {} for s in STRATEGIES[:3]}
    diagnostics = []
    for date in range(first, last, DAY_US):
        older, newer = date-3*DAY_US, date-2*DAY_US
        views = {p: [counts[p].get(d) for d in (older, newer)] for p in PAIRS}
        closes = {p: [days[p].get(d) for d in (older, newer)] for p in PAIRS}
        if any(type(v) is not int or v <= 0 for values in views.values() for v in values):
            return None, dict(reason="missing_or_zero_attention", decision_date_us=date)
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0
               for values in closes.values() for v in values):
            return None, dict(reason="missing_price_control_close", decision_date_us=date)
        weights = dict(attention={p: .35 if views[p][1] <= views[p][0] else 0.0 for p in PAIRS},
            price_contrarian={p: .35 if closes[p][1] <= closes[p][0] else 0.0 for p in PAIRS},
            constant_control=dict.fromkeys(PAIRS, .35))
        execution, cutoff = date+BAR_US, date-DAY_US
        for strategy, allocation in weights.items():
            targets[strategy][execution] = ScheduledTarget(cutoff, allocation)
        diagnostics.append(dict(execution_us=execution, source_cutoff_us=cutoff,
            older_day_us=older, newer_day_us=newer, views=views, closes=closes, weights=weights))
    return targets, diagnostics


def trial_data(prices, first, last):
    times = range(first, last, BAR_US)
    if any(t not in prices[p] for p in PAIRS for t in times):
        return None
    return {p: [prices[p][t] for t in times] for p in PAIRS}


def assess(rows, excluded):
    calendar = periods()
    names = {p for p, _, _ in calendar}
    omitted = [r["period"] for r in excluded]
    if len(set(omitted)) != len(omitted) or not set(omitted) <= names:
        raise ValueError("invalid attention exclusions")
    expected = {(p, s, c) for p in names-set(omitted) for s in STRATEGIES for c in ("base", "stress")}
    keyed = {(r["period"], r["strategy"], r["cost"]): r for r in rows}
    if len(keyed) != len(rows) or set(keyed) != expected:
        raise ValueError("invalid attention trial inventory")
    starts = {p: first for p, first, _ in calendar}
    if any(r["start_us"] != starts[r["period"]] or
           any(not math.isfinite(r[k]) for k in ("total_return", "max_drawdown", "turnover")) for r in rows):
        raise ValueError("invalid attention results")
    result = dict(scheduled_trials=78, usable_trials=78-len(omitted), excluded_trials=len(omitted), costs={})
    positive = lambda value: value is not None and value > 0
    for cost in ("base", "stress"):
        selected = [r for r in rows if r["strategy"] == "attention" and r["cost"] == cost]
        arrays = [[keyed[(p, s, cost)]["total_return"] if (p, s, cost) in keyed else None for p, _, _ in calendar]
                  for s in ("attention", "price_contrarian")]
        ci = block_intervals(*arrays)
        years = {str(y): [r for r in selected if datetime.fromtimestamp(r["start_us"]/1e6, timezone.utc).year == y]
                 for y in (2022, 2023, 2024)}
        means = {y: fmean(r["total_return"] for r in group) if group else None for y, group in years.items()}
        mean = fmean(r["total_return"] for r in selected) if selected else None
        control = fmean(v for v in arrays[1] if v is not None) if selected else None
        gates = dict(coverage=len(selected) >= 75,
            positive_return=positive(mean) and positive(ci["return_interval"][0]),
            price_control_advantage=bool(selected) and mean > control and positive(ci["advantage_interval"][0]),
            bootstrap_coverage=ci["valid_replicates"] >= .95*ci["repetitions"],
            two_positive_years=sum(positive(v) for v in means.values()) >= 2,
            profitable_windows=sum(r["total_return"] > 0 for r in selected) >= 52,
            active_windows=sum(r["active_days_utc"] >= 8 for r in selected) >= 52,
            drawdown=bool(selected) and all(r["max_drawdown"] <= .08 for r in selected))
        result["costs"][cost] = dict(mean_return=mean, median_return=median(r["total_return"] for r in selected) if selected else None,
            control_mean_return=control, mean_turnover=fmean(r["turnover"] for r in selected) if selected else None,
            worst_drawdown=max((r["max_drawdown"] for r in selected), default=None), year_means=means,
            positive_windows=sum(r["total_return"] > 0 for r in selected),
            active_utc_windows=sum(r["active_days_utc"] >= 8 for r in selected),
            active_hkt_windows=sum(r["active_days_hkt"] >= 8 for r in selected), uncertainty=ci, gates=gates)
    result.update(screen_passed=all(all(c["gates"].values()) for c in result["costs"].values()),
        strategy_approved=False, historical_first_seen_verified=False,
        reserved_validation_opened=False, qualification_verified=False)
    return result


def run(market: Path, attention: Path, output: Path, *, summaries_only=False):
    root = verify_plan()
    if output.exists():
        raise ValueError("use a new output directory")
    counts, source = load_counts(attention)
    days, prices, inputs = load_inputs(market)
    cfg = research_settings(api_key="", secret_key="", signal_source="offline", pairs=PAIRS,
        strategy="cash", fast_window=1, slow_window=2, max_asset_weight=.35, rebalance_band=.0025)
    output.mkdir(parents=True)
    manifest = dict(created_at=datetime.now(timezone.utc).isoformat(), plan_sha256=PLAN_SHA256,
        attention_snapshot=source, market_inputs=inputs, summaries_only=summaries_only,
        settings={k: v for k, v in asdict(cfg).items() if k not in {"api_key", "secret_key", "data_dir"}},
        rules={p: asdict(r) for p, r in RULES.items()},
        source_sha256={str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.glob("src/roostoo_bot/*.py"))})
    (output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    rows, excluded = [], []
    for period, first, last in periods():
        data = trial_data(prices, first, last)
        targets, diagnostics = schedules(counts, days, first, last)
        reasons = (["missing_execution_bar"] if data is None else []) + ([diagnostics["reason"]] if targets is None else [])
        if reasons:
            excluded.append(dict(period=period, start_us=first, end_exclusive_us=last, reasons=reasons))
            print(period, "excluded:", reasons, flush=True)
            continue
        (output/f"{period}_schedule.json").write_text(json.dumps(diagnostics, indent=2)+"\n")
        for cost, slip in (("base", .0005), ("stress", .0015)):
            for strategy in STRATEGIES:
                schedule = targets.get(strategy)
                summary, curve, trades = simulate_portfolio(data, replace(cfg, slippage_rate=slip), rules=RULES,
                    target_schedule=schedule, benchmark=None if schedule is not None else strategy)
                row = dict(period=period, strategy=strategy, cost=cost, **summary)
                rows.append(row)
                if not summaries_only:
                    write_report(output/period/strategy/cost, row, curve, trades)
                if strategy == "attention":
                    print(period, cost, f"return={summary['total_return']:.2%} dd={summary['max_drawdown']:.2%} active={summary['active_days_utc']}", flush=True)
        (output/"results.json").write_text(json.dumps(rows, indent=2, allow_nan=False)+"\n")
    (output/"excluded.json").write_text(json.dumps(excluded, indent=2)+"\n")
    verdict = assess(rows, excluded)
    (output/"verdict.json").write_text(json.dumps(verdict, indent=2, allow_nan=False)+"\n")
    print(json.dumps(verdict, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    fetch = sub.add_parser("download")
    fetch.add_argument("--output", type=Path, required=True)
    study = sub.add_parser("research")
    study.add_argument("--market", type=Path, required=True)
    study.add_argument("--attention", type=Path, required=True)
    study.add_argument("--output", type=Path, required=True)
    study.add_argument("--summaries-only", action="store_true", help="rerun without duplicating detailed ledgers")
    args = parser.parse_args()
    if args.command == "download":
        download(args.output)
    else:
        run(args.market, args.attention, args.output, summaries_only=args.summaries_only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
