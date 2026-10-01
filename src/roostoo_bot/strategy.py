from __future__ import annotations

from statistics import fmean, pstdev


def target_weight(prices: list[float], fast_window: int, slow_window: int, max_weight: float) -> float:
    """Long-only trend signal; cash is the defensive position.

    The bot owns an asset only when the fast average is above the slow average
    and recent volatility is not extreme. It intentionally does not force trades.
    """
    if len(prices) < slow_window + 1:
        return 0.0
    fast = fmean(prices[-fast_window:])
    slow = fmean(prices[-slow_window:])
    returns = [(b / a) - 1 for a, b in zip(prices[-slow_window - 1 : -1], prices[-slow_window:]) if a > 0]
    volatility = pstdev(returns) if len(returns) > 1 else 0.0
    if fast <= slow or volatility > 0.04:
        return 0.0
    # Scale conviction gently by trend strength without exceeding the risk cap.
    strength = min((fast / slow - 1) / 0.01, 1.0)
    return round(max_weight * (0.5 + 0.5 * strength), 6)

