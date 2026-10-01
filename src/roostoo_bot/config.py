from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name, str(default)).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


@dataclass(frozen=True)
class Settings:
    api_key: str
    secret_key: str
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

    @classmethod
    def from_env(cls) -> "Settings":
        pairs = tuple(p.strip().upper() for p in os.getenv("PAIRS", "BTC/USD,ETH/USD").split(",") if p.strip())
        if not pairs:
            raise ValueError("PAIRS must contain at least one pair")
        settings = cls(
            api_key=os.getenv("ROOSTOO_API_KEY", ""),
            secret_key=os.getenv("ROOSTOO_SECRET_KEY", ""),
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
        )
        if settings.fast_window >= settings.slow_window:
            raise ValueError("FAST_WINDOW must be smaller than SLOW_WINDOW")
        if not 0 < settings.max_asset_weight <= 1:
            raise ValueError("MAX_ASSET_WEIGHT must be in (0, 1]")
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

