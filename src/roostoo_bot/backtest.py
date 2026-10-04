from __future__ import annotations

import argparse
import csv
import json
import math
import zipfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import fmean, pstdev

from .strategy import target_weight


@dataclass(frozen=True)
class Candle:
    open_time_us: int
    open: float
    close: float
    high: float | None = None
    low: float | None = None


@dataclass(frozen=True)
class BacktestResult:
    initial_equity: float
    final_equity: float
    total_return: float
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float | None
    sortino_ratio: float | None
    calmar_ratio: float | None
    trades: int
    observations: int
    buy_and_hold_return: float | None = None
    active_trading_days: int | None = None


def load_candles(paths: list[Path]) -> list[Candle]:
    """Load continuous Binance five-minute spot candles from CSV or ZIP files."""
    candles: list[Candle] = []
    for path in paths:
        if path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path) as archive:
                names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
                if len(names) != 1:
                    raise ValueError(f"{path}: expected exactly one CSV")
                with archive.open(names[0]) as source:
                    candles.extend(_parse_candle_rows(csv.reader(line.decode() for line in source)))
        else:
            with path.open(newline="") as source:
                candles.extend(_parse_candle_rows(csv.reader(source)))
    candles.sort(key=lambda candle: candle.open_time_us)
    if len(candles) < 50:
        raise ValueError("at least 50 five-minute candles are required")
    if any(current.open_time_us - previous.open_time_us != 300_000_000 for previous, current in zip(candles, candles[1:])):
        raise ValueError("candles must be continuous five-minute intervals with no duplicates")
    if candles[-1].open_time_us + 300_000_000 > int(time.time() * 1_000_000):
        raise ValueError("dataset includes an incomplete or future candle")
    return candles


def _parse_candle_rows(rows: csv.reader) -> list[Candle]:
    parsed: list[Candle] = []
    for row in rows:
        if not row or row[0].lower() in {"open time", "open_time", "timestamp"}:
            continue
        if len(row) < 5:
            raise ValueError("expected Binance kline columns: open time, open, high, low, close")
        timestamp = int(row[0])
        if timestamp < 10**15:  # pre-2025 Binance files use milliseconds
            timestamp *= 1000
        candle = Candle(timestamp, float(row[1]), float(row[4]), float(row[2]), float(row[3]))
        if timestamp % 300_000_000:
            raise ValueError("candle is not aligned to a five-minute boundary")
        if any(not math.isfinite(value) or value <= 0 for value in (candle.open, candle.close, candle.high, candle.low)):
            raise ValueError("candle prices must be positive and finite")
        if candle.high < max(candle.open, candle.close) or candle.low > min(candle.open, candle.close):
            raise ValueError("invalid OHLC price bounds")
        if len(row) > 5 and (not math.isfinite(float(row[5])) or float(row[5]) < 0):
            raise ValueError("invalid volume")
        parsed.append(candle)
    return parsed


def _metrics(equity_curve: list[float], initial_equity: float, periods_per_year: int) -> tuple[float, float, float, float | None, float | None, float | None]:
    returns = [(current / previous) - 1 for previous, current in zip(equity_curve, equity_curve[1:]) if previous > 0]
    peak = initial_equity
    max_drawdown = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, 1 - equity / peak)
    total_return = equity_curve[-1] / initial_equity - 1
    annualized_return = (equity_curve[-1] / initial_equity) ** (periods_per_year / max(len(returns), 1)) - 1
    if len(returns) < 2:
        return total_return, annualized_return, max_drawdown, None, None, None
    mean_return = fmean(returns)
    volatility = pstdev(returns)
    sharpe = (mean_return / volatility * math.sqrt(periods_per_year)) if volatility else None
    downside = math.sqrt(fmean(min(value, 0.0) ** 2 for value in returns))
    sortino = (mean_return / downside * math.sqrt(periods_per_year)) if downside else None
    calmar = annualized_return / max_drawdown if max_drawdown else None
    return total_return, annualized_return, max_drawdown, sharpe, sortino, calmar


def simulate_candles(
    candles: list[Candle],
    *,
    initial_cash: float = 50_000.0,
    fee_rate: float = 0.001,
    slippage_rate: float = 0.0005,
    fast_window: int = 12,
    slow_window: int = 48,
    max_asset_weight: float = 0.35,
    rebalance_band: float = 0.05,
    min_trade_usd: float = 250.0,
) -> tuple[BacktestResult, list[float]]:
    """Calculate the signal after a close; fill any order at the next open."""
    if initial_cash <= 0 or not 0 <= fee_rate < 1 or not 0 <= slippage_rate < 1:
        raise ValueError("invalid cash, fee or slippage")
    if not 0 < fast_window < slow_window:
        raise ValueError("fast_window must be positive and smaller than slow_window")
    if len(candles) < slow_window + 2:
        raise ValueError("not enough candles to warm up and execute")
    cash, quantity, trades = initial_cash, 0.0, 0
    active_days: set[int] = set()
    close_history: list[float] = []
    target_for_next_open: float | None = None
    curve: list[float] = []
    for candle in candles:
        if target_for_next_open is not None:
            equity_at_open = cash + quantity * candle.open
            delta_value = equity_at_open * target_for_next_open - quantity * candle.open
            threshold = max(min_trade_usd, equity_at_open * rebalance_band)
            if abs(delta_value) >= threshold:
                executed = False
                if delta_value > 0:
                    fill_price = candle.open * (1 + slippage_rate)
                    notional = min(delta_value, cash / (1 + fee_rate))
                    if notional > 0:
                        cash -= notional * (1 + fee_rate)
                        quantity += notional / fill_price
                        trades += 1
                        executed = True
                else:
                    fill_price = candle.open * (1 - slippage_rate)
                    sold_quantity = min(quantity, abs(delta_value) / candle.open)
                    if sold_quantity > 0:
                        cash += sold_quantity * fill_price * (1 - fee_rate)
                        quantity -= sold_quantity
                        trades += 1
                        executed = True
                if executed:
                    active_days.add(candle.open_time_us // 86_400_000_000)
        curve.append(cash + quantity * candle.close)
        close_history.append(candle.close)
        target_for_next_open = target_weight(close_history, fast_window, slow_window, max_asset_weight)
    total_return, annualized_return, max_drawdown, sharpe, sortino, calmar = _metrics(curve, initial_cash, 105_120)
    buy_hold_quantity = initial_cash / (candles[0].open * (1 + slippage_rate) * (1 + fee_rate))
    return (
        BacktestResult(
            initial_equity=initial_cash,
            final_equity=curve[-1],
            total_return=total_return,
            annualized_return=annualized_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            trades=trades,
            observations=len(candles),
            buy_and_hold_return=buy_hold_quantity * candles[-1].close / initial_cash - 1,
            active_trading_days=len(active_days),
        ),
        curve,
    )


def write_report(result: BacktestResult, equity_curve: list[float], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(json.dumps(asdict(result), indent=2) + "\n")
    with (output_dir / "equity_curve.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["observation", "equity"])
        writer.writerows(enumerate(equity_curve))


def main() -> int:
    parser = argparse.ArgumentParser(description="Backtest the five-minute trend strategy")
    parser.add_argument("--csv", type=Path, nargs="+", required=True, help="Binance 5m kline CSV or ZIP files in sequence")
    parser.add_argument("--output", type=Path, default=Path("data/backtest"))
    parser.add_argument("--initial-cash", type=float, default=50_000.0)
    parser.add_argument("--slippage-rate", type=float, default=0.0005)
    parser.add_argument("--fast-window", type=int, default=12)
    parser.add_argument("--slow-window", type=int, default=48)
    args = parser.parse_args()
    result, curve = simulate_candles(
        load_candles(args.csv), initial_cash=args.initial_cash,
        slippage_rate=args.slippage_rate,
        fast_window=args.fast_window, slow_window=args.slow_window,
    )
    write_report(result, curve, args.output)
    print(json.dumps(asdict(result), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
