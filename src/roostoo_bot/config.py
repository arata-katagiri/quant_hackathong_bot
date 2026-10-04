from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import math
import os


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name, str(default)).strip().lower()
    if value not in {"1", "true", "yes", "on", "0", "false", "no", "off"}:
        raise ValueError(f"{name} must be an explicit boolean")
    return value in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False)
    secret_key: str = field(repr=False)
    dry_run: bool
    pairs: tuple[str, ...]
    poll_seconds: int
    data_dir: Path
    fast_window: int
    slow_window: int
    max_asset_weight: float
    rebalance_band: float
    min_trade_usd: float
    max_daily_loss: float
    max_drawdown: float
    credential_set: str = "testing"
    strategy: str = "baseline"
    decision_every_bars: int = 1
    signal_buffer: float = 0.005
    fee_rate: float = 0.001
    slippage_rate: float = 0.0005
    cash_reserve: float = 0.01
    max_spread: float = 0.005
    max_quote_age_seconds: int = 30
    max_sample_lag_seconds: int = 30
    live_trading_enabled: bool = False
    signal_source: str = "binance"

    def __post_init__(self) -> None:
        if not self.pairs or len(set(self.pairs)) != len(self.pairs):
            raise ValueError("PAIRS must be nonempty and unique")
        if any(p.count("/") != 1 or not p.endswith("/USD") or not p.split("/")[0] for p in self.pairs):
            raise ValueError("only USD-quoted spot pairs are supported")
        if self.poll_seconds != 300:
            raise ValueError("POLL_SECONDS must be 300 to match five-minute research")
        if not 0 < self.fast_window < self.slow_window:
            raise ValueError("require 0 < FAST_WINDOW < SLOW_WINDOW")
        if self.signal_source not in {"binance", "roostoo", "offline"}:
            raise ValueError("SIGNAL_SOURCE must be binance, roostoo or offline")
        if self.signal_source == "offline" and (self.api_key or self.secret_key or not self.dry_run or self.live_trading_enabled):
            raise ValueError("offline research requires empty credentials and disabled trading")
        if self.signal_source == "binance" and (self.slow_window >= 1000 or set(self.pairs) - {"BTC/USD", "ETH/USD"}):
            raise ValueError("Binance signal input supports BTC/ETH and at most 999 slow samples")
        if self.strategy not in {"cash", "baseline", "buffered_trend", "breakout", "pullback", "vol_momentum", "vol_control", "relative_strength", "breadth_control"}:
            raise ValueError("unknown STRATEGY")
        if self.strategy in {"relative_strength", "breadth_control"}:
            if self.signal_source != "offline":
                raise ValueError("relative strength is offline research only")
            if (self.fast_window, self.slow_window, self.decision_every_bars) != (288, 2016, 288):
                raise ValueError("relative strength requires the frozen 288/2016/288 cadence")
        if self.strategy in {"vol_momentum", "vol_control"}:
            if self.signal_source != "offline":
                raise ValueError("volatility momentum is offline research only")
            if (self.fast_window, self.slow_window, self.decision_every_bars) != (288, 2016, 72):
                raise ValueError("volatility momentum requires the frozen 288/2016/72 cadence")
        if self.strategy == "pullback" and self.fast_window < 2:
            raise ValueError("pullback requires at least two fast-window samples")
        if self.decision_every_bars < 1 or 288 % self.decision_every_bars:
            raise ValueError("DECISION_EVERY_BARS must divide 288")
        for name in ("max_asset_weight", "rebalance_band", "max_daily_loss", "max_drawdown", "signal_buffer", "fee_rate", "slippage_rate", "cash_reserve", "max_spread"):
            value = getattr(self, name)
            if not math.isfinite(value) or not 0 <= value < 1:
                raise ValueError(f"invalid {name}")
        if self.max_asset_weight <= 0 or self.max_daily_loss <= 0 or self.max_drawdown <= 0:
            raise ValueError("weight and loss limits must be positive")
        if len(self.pairs) * self.max_asset_weight > 1 - self.cash_reserve + 1e-12:
            raise ValueError("asset caps exceed the portfolio cash budget")
        if not math.isfinite(self.min_trade_usd) or self.min_trade_usd <= 0:
            raise ValueError("MIN_TRADE_USD must be positive and finite")
        if self.max_quote_age_seconds < 1 or not 0 <= self.max_sample_lag_seconds < 300:
            raise ValueError("invalid quote age or sample lag")
        if self.credential_set not in {"testing", "competition"}:
            raise ValueError("invalid credential set")
        if not self.dry_run and not self.live_trading_enabled:
            raise ValueError("live orders disabled; separate LIVE_TRADING_ENABLED approval is required")

    @classmethod
    def from_env(cls) -> "Settings":
        pairs = tuple(p.strip().upper() for p in os.getenv("PAIRS", "BTC/USD,ETH/USD").split(",") if p.strip())
        if not pairs:
            raise ValueError("PAIRS must contain at least one pair")
        credential_set = os.getenv("CREDENTIAL_SET", "testing").strip().lower()
        if credential_set == "competition":
            api_key = os.getenv("ROOSTOO_COMPET_API_KEY", "")
            secret_key = os.getenv("ROOSTOO_COMPET_API_SECRET", "")
        elif credential_set == "testing":
            api_key = os.getenv("ROOSTOO_API_KEY", "")
            # ROOSTOO_SECRET_KEY is supported for compatibility with the API docs.
            secret_key = os.getenv("ROOSTOO_API_SECRET", os.getenv("ROOSTOO_SECRET_KEY", ""))
        else:
            raise ValueError("CREDENTIAL_SET must be testing or competition")
        settings = cls(
            api_key=api_key,
            secret_key=secret_key,
            dry_run=_bool("DRY_RUN", True),
            pairs=pairs,
            poll_seconds=_int("POLL_SECONDS", 300),
            data_dir=Path(os.getenv("DATA_DIR", "data")),
            fast_window=_int("FAST_WINDOW", 12),
            slow_window=_int("SLOW_WINDOW", 48),
            max_asset_weight=_float("MAX_ASSET_WEIGHT", 0.35),
            rebalance_band=_float("REBALANCE_BAND", 0.05),
            min_trade_usd=_float("MIN_TRADE_USD", 250),
            max_daily_loss=_float("MAX_DAILY_LOSS", 0.03),
            max_drawdown=_float("MAX_DRAWDOWN", 0.08),
            credential_set=credential_set,
            strategy=os.getenv("STRATEGY", "baseline"),
            decision_every_bars=_int("DECISION_EVERY_BARS", 1),
            signal_buffer=_float("SIGNAL_BUFFER", 0.005),
            fee_rate=_float("FEE_RATE", 0.001),
            slippage_rate=_float("SLIPPAGE_RATE", 0.0005),
            cash_reserve=_float("CASH_RESERVE", 0.01),
            max_spread=_float("MAX_SPREAD", 0.005),
            max_quote_age_seconds=_int("MAX_QUOTE_AGE_SECONDS", 30),
            max_sample_lag_seconds=_int("MAX_SAMPLE_LAG_SECONDS", 30),
            live_trading_enabled=_bool("LIVE_TRADING_ENABLED", False),
            signal_source=os.getenv("SIGNAL_SOURCE", "binance"),
        )
        return settings


def load_dotenv(path: Path = Path(".env")) -> None:
    """Minimal .env loader; environment variables win over file values."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
