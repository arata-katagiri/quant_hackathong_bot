"""Synchronized spot-portfolio simulation using the bot's decision functions."""
from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from statistics import fmean, pstdev
import csv

from .backtest import Candle, load_candles
from .config import Settings
from .portfolio import HKT, PairRules, Quote, equity, next_order, strategy_targets, update_risk

BAR_US = 300_000_000
# Public /v3/exchangeInfo snapshot on 2026-10-01. Research assumption, not a live constant.
RESEARCH_RULES = {"BTC/USD": PairRules(5, 1.0), "ETH/USD": PairRules(4, 1.0)}


@dataclass(frozen=True)
class ScheduledTarget:
    source_cutoff_us: int
    weights: dict[str, float]


def research_settings(**overrides) -> Settings:
    values = dict(api_key="offline", secret_key="offline", dry_run=True, pairs=("BTC/USD", "ETH/USD"),
                  poll_seconds=300, data_dir=Path("data/research"), fast_window=12, slow_window=48,
                  max_asset_weight=0.35, rebalance_band=0.05, min_trade_usd=250.0,
                  max_daily_loss=0.03, max_drawdown=0.08)
    values.update(overrides)
    return Settings(**values)


def validate_alignment(data: dict[str, list[Candle]], pairs: tuple[str, ...]) -> None:
    if set(data) != set(pairs):
        raise ValueError("data must exactly match configured pairs")
    reference = [c.open_time_us for c in data[pairs[0]]]
    if len(reference) < 2 or any(b - a != BAR_US for a, b in zip(reference, reference[1:])):
        raise ValueError("noncontinuous portfolio candles")
    for pair in pairs:
        if [c.open_time_us for c in data[pair]] != reference:
            raise ValueError("asset timestamps are not aligned; no forward-filling allowed")
        if any(not math.isfinite(p) or p <= 0 for c in data[pair] for p in (c.open, c.close)):
            raise ValueError("invalid portfolio prices")


def simulate_portfolio(data: dict[str, list[Candle]], settings: Settings, *, initial_cash: float = 100_000,
                       start_index: int = 0, end_index: int | None = None, benchmark: str | None = None,
                       rules: dict[str, PairRules] | None = None, liquidate: bool = True,
                       target_schedule: dict[int, ScheduledTarget] | None = None) -> tuple[dict, list[dict], list[dict]]:
    validate_alignment(data, settings.pairs)
    n = len(data[settings.pairs[0]])
    end_index = n if end_index is None else end_index
    if not math.isfinite(initial_cash) or initial_cash <= 0 or not 0 <= start_index < end_index <= n:
        raise ValueError("invalid simulation bounds or capital")
    if benchmark not in {None, "cash", "buy_hold_50", "buy_hold_35", "buy_hold_equal_28", "buy_hold_equal_70", "buy_hold_equal_100"}:
        raise ValueError("unknown benchmark")
    if benchmark in {"buy_hold_50", "buy_hold_35"} and len(settings.pairs) != 2:
        raise ValueError("35/35 and 50/50 benchmarks require exactly two assets")
    if target_schedule is not None:
        if (benchmark is not None or settings.signal_source != "offline" or settings.api_key or settings.secret_key
                or not settings.dry_run or settings.live_trading_enabled):
            raise ValueError("scheduled targets require isolated offline research without a benchmark")
        allowed_times = {c.open_time_us for c in data[settings.pairs[0]][start_index:end_index]}
        for timestamp, target in target_schedule.items():
            if (type(timestamp) is not int or timestamp not in allowed_times or not isinstance(target, ScheduledTarget)
                    or type(target.source_cutoff_us) is not int or target.source_cutoff_us > timestamp-BAR_US
                    or set(target.weights) != set(settings.pairs)):
                raise ValueError("invalid target schedule timestamp, source cutoff or pairs")
            if (any(isinstance(w, bool) or not math.isfinite(w) or not 0 <= w <= settings.max_asset_weight for w in target.weights.values())
                    or sum(target.weights.values()) > 1-settings.cash_reserve+1e-12):
                raise ValueError("invalid target schedule weights")
    rules = rules or RESEARCH_RULES
    if set(rules) != set(settings.pairs):
        raise ValueError("exchange rules must exactly match configured assets")
    wallet = {"USD": {"Free": initial_cash, "Lock": 0.0}}
    wallet.update({p.split("/")[0]: {"Free": 0.0, "Lock": 0.0} for p in settings.pairs})
    history = {p: [] for p in settings.pairs}
    state: dict = {"risk": {}}
    curve, trades = [], []
    stopped_bars = 0
    warm_start = max(0, start_index - settings.slow_window - 1)

    def fill(pair: str, side: str, quantity: float, price: float, timestamp: int, reason: str, forced: bool = False) -> None:
        fill_price = price * (1 + settings.slippage_rate * (1 if side == "BUY" else -1))
        notional = quantity * fill_price
        fee = notional * settings.fee_rate
        coin = pair.split("/")[0]
        if side == "BUY":
            if notional + fee > wallet["USD"]["Free"] + 1e-7:
                raise AssertionError("simulator attempted to overspend cash")
            wallet["USD"]["Free"] -= notional + fee
            wallet[coin]["Free"] += quantity
        else:
            if quantity > wallet[coin]["Free"] + 1e-10:
                raise AssertionError("simulator attempted to sell unavailable asset")
            wallet[coin]["Free"] -= quantity
            wallet["USD"]["Free"] += notional - fee
        trades.append(dict(timestamp_us=timestamp, decision_us=timestamp - 1, pair=pair, side=side, quantity=quantity,
                           price=fill_price, notional=notional, fee=fee, reason=reason, forced=forced))

    for index in range(warm_start, end_index):
        candle0 = data[settings.pairs[0]][index]
        stamp = candle0.open_time_us
        open_quotes = {p: Quote(data[p][index].open, data[p][index].open) for p in settings.pairs}
        if index >= start_index:
            value = equity(wallet, open_quotes)
            reason = "ok" if benchmark else update_risk(state["risk"], value, stamp / 1e6, settings)
            pending = None
            if reason != "ok":
                pending = dict.fromkeys(settings.pairs, 0.0)
                stopped_bars += 1
            elif benchmark:
                weight = {"cash": 0.0, "buy_hold_50": 0.5, "buy_hold_35": 0.35,
                          "buy_hold_equal_28": .28 / len(settings.pairs),
                          "buy_hold_equal_70": .7 / len(settings.pairs),
                          "buy_hold_equal_100": 1 / len(settings.pairs)}[benchmark]
                pending = dict.fromkeys(settings.pairs, weight) if index == start_index else None
            elif target_schedule is not None:
                target = target_schedule.get(stamp)
                pending = dict(target.weights) if target is not None else None
            else:
                # Fresh engine semantics: earlier candles warm indicators, not
                # hypothetical position state. Only completed prior bars enter
                # the decision at this open, after the same risk check as live.
                pending = strategy_targets(history, state, settings, stamp // BAR_US)
            if pending is not None:
                used = set()
                # Freeze both desired dollar exposures for benchmark allocation.
                benchmark_quantities = {p: rules[p].floor(initial_cash * pending[p] / (open_quotes[p].ask * (1 + settings.slippage_rate) * (1 + settings.fee_rate))) for p in settings.pairs} if benchmark else None
                for pair_index in range(len(settings.pairs)):
                    if benchmark:
                        pair = settings.pairs[pair_index]
                        quantity = float(benchmark_quantities[pair])
                        if rules[pair].can_trade and quantity * open_quotes[pair].bid * (1-settings.slippage_rate) > rules[pair].min_notional:
                            fill(pair, "BUY", quantity, open_quotes[pair].mid, stamp, benchmark)
                        continue
                    reason = update_risk(state["risk"], equity(wallet, open_quotes), stamp / 1e6, settings)
                    if reason != "ok":
                        pending = dict.fromkeys(settings.pairs, 0.0)
                    intent = next_order(wallet, open_quotes, rules, pending, settings, excluded=used, risk_reason=reason)
                    if intent is None:
                        break
                    used.add(intent.pair)
                    fill(intent.pair, intent.side, float(intent.quantity), open_quotes[intent.pair].mid, stamp, intent.reason)
        close_quotes = {p: Quote(data[p][index].close, data[p][index].close) for p in settings.pairs}
        for pair in settings.pairs:
            history[pair].append(data[pair][index].close)
            history[pair] = history[pair][-settings.slow_window - 1:]
        if index >= start_index:
            value = equity(wallet, close_quotes)
            # Mark the close for reporting only. The engine samples account
            # risk at decision boundaries, not at an extra pre-boundary tick.
            curve.append({"timestamp_us": stamp + BAR_US - 1, "equity": value, "cash": wallet["USD"]["Free"],
                          "exposure": 1 - wallet["USD"]["Free"] / value if value else 0,
                          "risk_reason": reason})
    mark_equity = curve[-1]["equity"]
    if liquidate:
        for pair in settings.pairs:
            quantity = wallet[pair.split("/")[0]]["Free"]
            if quantity > 0:
                fill(pair, "SELL", quantity, data[pair][end_index - 1].close, curve[-1]["timestamp_us"], "end_liquidation", True)
        curve[-1]["equity"] = wallet["USD"]["Free"]
        curve[-1]["cash"] = wallet["USD"]["Free"]
        curve[-1]["exposure"] = 0.0
    peak, drawdown = initial_cash, 0.0
    days: dict[str, float] = {}
    for point in curve:
        peak = max(peak, point["equity"])
        drawdown = max(drawdown, 1 - point["equity"] / peak)
        days[datetime.fromtimestamp(point["timestamp_us"] / 1e6, HKT).date().isoformat()] = point["equity"]
    daily_returns = []
    previous = initial_cash
    start_us = data[settings.pairs[0]][start_index].open_time_us
    for day, day_equity in days.items():
        day_start_us = int(datetime.fromisoformat(day).replace(tzinfo=HKT).timestamp() * 1e6)
        if day_start_us >= start_us and day_start_us + 86_400_000_000 <= curve[-1]["timestamp_us"] + 1:
            daily_returns.append(day_equity / previous - 1)
        previous = day_equity
    mean = fmean(daily_returns) if daily_returns else 0.0
    vol = pstdev(daily_returns) if len(daily_returns) > 1 else 0.0
    downside = math.sqrt(fmean(min(x, 0) ** 2 for x in daily_returns)) if daily_returns else 0.0
    duration_days = len(curve) / 288
    total_return = curve[-1]["equity"] / initial_cash - 1
    exponent = math.log1p(total_return) * 365 / duration_days
    annualized = math.expm1(exponent) if duration_days >= 1 and exponent < 700 else None
    active = [trade for trade in trades if not trade["forced"]]
    def by_day(tz):
        counts: dict[str, int] = {}
        for trade in active:
            day = datetime.fromtimestamp(trade["timestamp_us"] / 1e6, tz).date().isoformat()
            counts[day] = counts.get(day, 0) + 1
        return counts
    hkt_counts, utc_counts = by_day(HKT), by_day(timezone.utc)
    summary = dict(initial_equity=initial_cash, final_equity=curve[-1]["equity"], total_return=total_return,
                   mark_to_market_return=mark_equity / initial_cash - 1, max_drawdown=drawdown,
                   turnover=sum(t["notional"] for t in trades) / initial_cash, fees=sum(t["fee"] for t in trades),
                   trades=len(active), forced_liquidations=len(trades) - len(active), active_days_hkt=len(hkt_counts),
                   active_days_utc=len(utc_counts), fills_by_hkt_day=hkt_counts, fills_by_utc_day=utc_counts,
                   sharpe_daily=mean / vol * math.sqrt(365) if vol else None,
                   sortino_daily=mean / downside * math.sqrt(365) if downside else None,
                   calmar=annualized / drawdown if drawdown and annualized is not None else None, annualized_return=annualized,
                   full_days_for_ratios=len(daily_returns),
                   observations=len(curve), warmup_observations=start_index - warm_start, stopped_bars=stopped_bars,
                   drawdown_halted=state["risk"].get("drawdown_halted", False),
                   start_us=data[settings.pairs[0]][start_index].open_time_us, end_us=curve[-1]["timestamp_us"],
                   mean_exposure=fmean(p["exposure"] for p in curve))
    return summary, curve, trades


def write_report(output: Path, summary: dict, curve: list[dict], trades: list[dict]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    for name, rows in (("equity_curve", curve), ("trades", trades)):
        with (output / f"{name}.csv").open("w", newline="") as stream:
            if rows:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--btc", nargs="+", type=Path, required=True)
    parser.add_argument("--eth", nargs="+", type=Path, required=True)
    parser.add_argument("--strategy", choices=["baseline", "buffered_trend", "breakout", "pullback"], default="baseline")
    parser.add_argument("--output", type=Path, default=Path("data/portfolio_backtest"))
    args = parser.parse_args()
    overrides = {} if args.strategy == "baseline" else dict(fast_window=144, slow_window=576, decision_every_bars=12)
    if args.strategy == "pullback":
        overrides["decision_every_bars"] = 3
    settings = research_settings(strategy=args.strategy, **overrides)
    result, curve, trades = simulate_portfolio({"BTC/USD": load_candles(args.btc), "ETH/USD": load_candles(args.eth)}, settings)
    write_report(args.output, result, curve, trades)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
