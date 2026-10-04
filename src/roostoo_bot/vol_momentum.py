"""Pure, offline-only continuous momentum forecast and volatility sizing."""
from __future__ import annotations
import math
from statistics import fmean, pstdev

LOOKBACK = 2016  # seven days of five-minute intervals


def allocation(prices: list[float], cap: float, *, timing: bool = True) -> dict[str, float]:
    if len(prices) < LOOKBACK + 1:
        raise ValueError("volatility momentum requires 2017 completed closes")
    if not math.isfinite(cap) or not 0 < cap < 1:
        raise ValueError("invalid allocation cap")
    hourly = prices[-LOOKBACK - 1::12]
    # Anchor sampling to the latest close even if an external caller supplies
    # more history than requested. Never include an unfinished/current bar.
    if len(hourly) != 169 or any(not math.isfinite(p) or p <= 0 for p in hourly):
        raise ValueError("invalid hourly-spaced history")
    returns = [math.log(b / a) for a, b in zip(hourly, hourly[1:])]
    volatility = max(.005, pstdev(returns) * math.sqrt(24))
    risk_weight = cap * min(1.0, .02 / volatility)
    score = fmean(math.log(prices[-1] / prices[-1 - day * 288]) / (volatility * math.sqrt(day))
                  for day in (1, 3, 7))
    forecast = min(1.0, max(0.0, score)) if timing else 1.0
    return {"daily_volatility": volatility, "momentum_score": score, "forecast": forecast,
            "risk_weight": risk_weight, "target_weight": risk_weight * forecast}
