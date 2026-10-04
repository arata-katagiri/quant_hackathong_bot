"""Pure decision functions shared by the execution engine and portfolio simulator."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_DOWN
import math
from statistics import fmean, pstdev

from .config import Settings
from .strategy import target_weight

HKT = timezone(timedelta(hours=8))


def number(value: object, *, nonnegative: bool = True) -> float:
    result = float(value)
    if not math.isfinite(result) or (nonnegative and result < 0):
        raise ValueError("nonfinite or negative market/account value")
    return result


@dataclass(frozen=True)
class PairRules:
    amount_precision: int
    min_notional: float
    can_trade: bool = True

    @classmethod
    def from_api(cls, value: dict) -> "PairRules":
        precision = value["AmountPrecision"]
        if isinstance(precision, bool) or not isinstance(precision, int) or not 0 <= precision <= 12:
            raise ValueError("invalid AmountPrecision")
        if not isinstance(value["CanTrade"], bool):
            raise ValueError("invalid CanTrade")
        return cls(precision, number(value["MiniOrder"]), value["CanTrade"])

    def floor(self, quantity: float) -> Decimal:
        return Decimal(str(number(quantity))).quantize(Decimal(1).scaleb(-self.amount_precision), rounding=ROUND_DOWN)


@dataclass(frozen=True)
class Quote:
    bid: float
    ask: float

    def __post_init__(self) -> None:
        if number(self.bid) <= 0 or number(self.ask) < self.bid:
            raise ValueError("invalid or crossed quote")

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2

    @property
    def spread(self) -> float:
        return (self.ask - self.bid) / self.mid


@dataclass(frozen=True)
class OrderIntent:
    pair: str
    side: str
    quantity: str
    estimated_notional: float
    reason: str


def balances(wallet: dict, pairs: tuple[str, ...]) -> dict[str, dict[str, float]]:
    allowed = {"USD", *(p.split("/")[0] for p in pairs)}
    result = {}
    for coin, raw in wallet.items():
        free, locked = float(raw.get("Free", 0)), float(raw.get("Lock", 0))
        # FAQ documents cent-level rounding residues after sales.
        if coin == "USD" and -0.02 <= free < 0:
            free = 0.0
        free, locked = number(free), number(locked)
        if coin not in allowed and free + locked > 0:
            raise ValueError("unpriced holdings outside configured pairs")
        result[coin] = {"Free": free, "Lock": locked}
    if "USD" not in result:
        raise ValueError("wallet missing USD")
    for coin in allowed:
        result.setdefault(coin, {"Free": 0.0, "Lock": 0.0})
    return result


def equity(wallet: dict, quotes: dict[str, Quote]) -> float:
    total = wallet["USD"]["Free"] + wallet["USD"]["Lock"]
    for pair, quote in quotes.items():
        asset = wallet[pair.split("/")[0]]
        total += quote.mid * (asset["Free"] + asset["Lock"])
    return number(total)


def update_risk(state: dict, value: float, timestamp: float, settings: Settings) -> str:
    """Latch a daily stop until next HKT day; a drawdown stop until explicit review.

    The caller liquidates available holdings when stopped. This is checked every
    five minutes even when the strategy makes hourly decisions.
    """
    value = number(value)
    today = datetime.fromtimestamp(timestamp, HKT).date().isoformat()
    if state.get("day") != today:
        state["day"] = today
        state["day_start_equity"] = state.get("last_equity", value)
        state["daily_halted"] = False
    peak = max(state.get("peak_equity", value), value)
    state["peak_equity"] = peak
    start = state["day_start_equity"]
    if start > 0 and value <= start * (1 - settings.max_daily_loss):
        state["daily_halted"] = True
    if peak > 0 and value <= peak * (1 - settings.max_drawdown):
        state["drawdown_halted"] = True
    state["last_equity"] = value
    if state.get("drawdown_halted"):
        return "drawdown_limit"
    if state.get("daily_halted"):
        return "daily_loss_limit"
    return "ok"


def strategy_targets(history: dict[str, list[float]], state: dict, settings: Settings, bar: int) -> dict[str, float] | None:
    if settings.strategy == "cash":
        return dict.fromkeys(settings.pairs, 0.0)
    if any(len(history.get(pair, [])) < settings.slow_window + 1 for pair in settings.pairs):
        return None
    if bar % settings.decision_every_bars:
        return None
    if settings.strategy in {"relative_strength", "breadth_control"}:
        from .relative_strength import allocation
        result = allocation({p: history[p] for p in settings.pairs}, settings.max_asset_weight,
                            ranking=settings.strategy == "relative_strength")
        state["relative_strength"] = result
        return result["targets"]
    if settings.strategy in {"vol_momentum", "vol_control"}:
        from .vol_momentum import allocation
        diagnostics = {p: allocation(history[p], settings.max_asset_weight, timing=settings.strategy == "vol_momentum")
                       for p in settings.pairs}
        state["volatility_allocation"] = diagnostics
        return {p: row["target_weight"] for p, row in diagnostics.items()}
    targets = {}
    signals = state.setdefault("signals", {})
    for pair in settings.pairs:
        prices = history[pair]
        if settings.strategy == "baseline":
            weight = target_weight(prices, settings.fast_window, settings.slow_window, settings.max_asset_weight)
        else:
            active = signals.get(pair, False)
            if settings.strategy == "buffered_trend":
                ratio = fmean(prices[-settings.fast_window:]) / fmean(prices[-settings.slow_window:])
                active = ratio > 1 if active else ratio > 1 + settings.signal_buffer
            elif settings.strategy == "breakout":
                prior = prices[:-1]
                active = prices[-1] > min(prior[-settings.fast_window:]) if active else prices[-1] > max(prior[-settings.slow_window:]) * (1 + settings.signal_buffer)
            elif settings.strategy == "pullback":
                prior, latest = prices[:-1], prices[-1]
                short = prior[-settings.fast_window:]
                mean, deviation = fmean(short), pstdev(short)
                trend_mean = fmean(prior[-settings.slow_window:])
                entries = state.setdefault("pullback_entries", {})
                if active:
                    entry = entries[pair]
                    active = latest < entry["target"] and latest > trend_mean and bar - entry["bar"] < settings.fast_window
                    if not active:
                        entries.pop(pair)
                else:
                    active = (mean > trend_mean and latest > trend_mean and deviation > 0
                              and latest <= mean - 2 * deviation and mean / latest - 1 >= .006)
                    if active:
                        entries[pair] = {"bar": bar, "target": mean}
            signals[pair] = active
            weight = settings.max_asset_weight if active else 0.0
        targets[pair] = weight
    return targets


def next_order(wallet: dict, quotes: dict[str, Quote], rules: dict[str, PairRules], targets: dict[str, float], settings: Settings, *, excluded: set[str] | None = None, risk_reason: str = "ok") -> OrderIntent | None:
    """Choose sells before buys. Recompute after each confirmed fill/balance refresh.

    Never spend expected sell proceeds, locked funds or the cash reserve. Full
    exits bypass the rebalance band and local minimum, but obey exchange minimums.
    """
    value = equity(wallet, quotes)
    intents = []
    for pair in settings.pairs:
        if pair in (excluded or set()):
            continue
        rule, quote = rules[pair], quotes[pair]
        if not rule.can_trade or quote.spread > settings.max_spread:
            continue
        weight = number(targets[pair])
        if weight > settings.max_asset_weight + 1e-12:
            raise ValueError("target exceeds asset cap")
        asset = wallet[pair.split("/")[0]]
        current = (asset["Free"] + asset["Lock"]) * quote.mid
        delta = value * weight - current
        exiting = weight == 0 and current > 0
        if not exiting and abs(delta) < max(settings.min_trade_usd, value * settings.rebalance_band):
            continue
        side = "BUY" if delta > 0 else "SELL"
        if side == "BUY":
            available = max(0.0, wallet["USD"]["Free"] - value * settings.cash_reserve)
            worst_price = quote.ask * (1 + settings.slippage_rate)
            quantity = min(delta / quote.mid, available / (worst_price * (1 + settings.fee_rate)))
        else:
            quantity = min(asset["Free"], current / quote.mid if exiting else abs(delta) / quote.mid)
        rounded = rule.floor(quantity)
        conservative_notional = float(rounded) * quote.bid * (1 - settings.slippage_rate)
        if rounded <= 0 or conservative_notional <= rule.min_notional:
            continue
        if not exiting and conservative_notional < settings.min_trade_usd:
            continue
        intents.append(OrderIntent(pair, side, format(rounded, "f"), float(rounded) * quote.mid, risk_reason if risk_reason != "ok" else ("exit" if exiting else "rebalance")))
    return min(intents, key=lambda x: (x.side == "BUY", -x.estimated_notional, x.pair)) if intents else None
