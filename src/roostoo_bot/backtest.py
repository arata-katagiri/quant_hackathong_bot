from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import fmean, pstdev

from .strategy import target_weight


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


def load_closes(path: Path) -> list[float]:
    """Read close prices from a named CSV or Binance's headerless kline export."""
    with path.open(newline="") as stream:
        first_line = stream.readline()
        stream.seek(0)
        has_header = "close" in first_line.lower()
        if has_header:
            rows = csv.DictReader(stream)
            closes = [float(row.get("close") or row.get("Close") or "") for row in rows]
        else:
            rows = csv.reader(stream)
            closes = [float(row[4]) for row in rows if len(row) >= 5]
    if len(closes) < 2:
        raise ValueError("CSV must contain at least two close prices")
    if any(price <= 0 for price in closes):
        raise ValueError("close prices must be positive")
    return closes


def _metrics(equity_curve: list[float], initial_equity: float, periods_per_year: int) -> tuple[float, float, float | None, float | None, float | None]:
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


def simulate(
    closes: list[float],
    *,
    initial_cash: float = 50_000.0,
    fee_rate: float = 0.001,
    fast_window: int = 12,
    slow_window: int = 48,
    max_asset_weight: float = 0.35,
    rebalance_band: float = 0.05,
    min_trade_usd: float = 250.0,
    periods_per_year: int = 8_760,
) -> tuple[BacktestResult, list[float]]:
    """Simulate the live bot's long-only rebalancing using closing prices.

    Fees are charged on every market-order notional. The implementation mirrors
    the live strategy's warm-up, target allocation and rebalance threshold.
    """
    if initial_cash <= 0 or not 0 <= fee_rate < 1:
        raise ValueError("initial_cash must be positive and fee_rate must be in [0, 1)")
    cash, quantity, trades = initial_cash, 0.0, 0
    curve: list[float] = []
    for index, price in enumerate(closes):
        equity = cash + quantity * price
        target = target_weight(closes[: index + 1], fast_window, slow_window, max_asset_weight)
        current_value = quantity * price
        delta_value = equity * target - current_value
        threshold = max(min_trade_usd, equity * rebalance_band)
        if abs(delta_value) >= threshold:
            if delta_value > 0:
                notional = min(delta_value, cash / (1 + fee_rate))
                if notional > 0:
                    cash -= notional * (1 + fee_rate)
                    quantity += notional / price
                    trades += 1
            else:
                notional = min(abs(delta_value), current_value)
                if notional > 0:
                    cash += notional * (1 - fee_rate)
                    quantity -= notional / price
                    trades += 1
        curve.append(cash + quantity * price)
    total_return, annualized_return, max_drawdown, sharpe, sortino, calmar = _metrics(curve, initial_cash, periods_per_year)
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
            observations=len(closes),
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
    parser = argparse.ArgumentParser(description="Backtest the live bot's trend strategy against candle closes")
    parser.add_argument("--csv", type=Path, required=True, help="Binance kline CSV or a CSV with a close column")
    parser.add_argument("--output", type=Path, default=Path("data/backtest"))
    parser.add_argument("--periods-per-year", type=int, default=8_760, help="8760 for hourly candles; 105120 for 5-minute candles")
    parser.add_argument("--initial-cash", type=float, default=50_000.0)
    args = parser.parse_args()
    result, curve = simulate(load_closes(args.csv), initial_cash=args.initial_cash, periods_per_year=args.periods_per_year)
    write_report(result, curve, args.output)
    print(json.dumps(asdict(result), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
