"""Frozen, long-only cross-sectional ranking; research only, no I/O."""
from __future__ import annotations

import math

LOOKBACK = 2016


def allocation(history: dict[str, list[float]], cap: float, *, ranking: bool = True) -> dict:
    if not history or not math.isfinite(cap) or not 0 < cap <= .5:
        raise ValueError("invalid relative-strength universe or cap")
    diagnostics = {}
    for pair, prices in history.items():
        if len(prices) < LOOKBACK + 1:
            raise ValueError("relative strength needs seven days of completed history")
        recent = prices[-LOOKBACK-1:]
        if any(not math.isfinite(p) or p <= 0 for p in recent):
            raise ValueError("invalid relative-strength price")
        hourly = recent[::12]
        diagnostics[pair] = {"score": hourly[-1] / max(hourly),
                             "eligible": hourly[-1] > hourly[0]}
    eligible = sorted((p for p in history if diagnostics[p]["eligible"]),
                      key=lambda p: (-diagnostics[p]["score"], p))
    selected = eligible[:2] if ranking else eligible
    gross = cap * min(2, len(eligible))
    weight = gross / len(selected) if selected else 0.0
    return {"targets": {p: weight if p in selected else 0.0 for p in history},
            "ranked_eligible": eligible, "diagnostics": diagnostics}
