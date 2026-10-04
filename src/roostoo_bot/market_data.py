"""Public closed-candle input; credentials and order APIs are never used here."""
from __future__ import annotations
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from .backtest import _parse_candle_rows

SYMBOLS = {"BTC/USD": "BTCUSDT", "ETH/USD": "ETHUSDT"}


class MarketDataError(RuntimeError):
    pass


def _public_payload(url: str) -> bytes:
    # Idempotent public read only. Do not retry invalid candle contents.
    for attempt in range(2):
        try:
            with urlopen(url, timeout=15) as response:
                return response.read(1_000_001)
        except (OSError, URLError) as exc:
            code = exc.code if isinstance(exc, HTTPError) else None
            # A mocked or body-less HTTPError may have no response stream.
            # Python 3.9's close() raises in that case and must not mask 403.
            if isinstance(exc, HTTPError) and exc.fp is not None:
                exc.close()
            retryable = code is None or code in {408, 429} or code >= 500
            if attempt == 0 and retryable:
                time.sleep(1)
                continue
            cause = type(exc.reason).__name__ if isinstance(exc, URLError) else type(exc).__name__
            detail = "HTTP " + str(code) if code is not None else cause
            raise MarketDataError("public candle feed unavailable (" + detail + ")") from None
    raise MarketDataError("public candle request exhausted")


def closed_prices(rows: list, count: int, boundary_seconds: int) -> list[float]:
    boundary_us = boundary_seconds * 1_000_000
    if not isinstance(rows, list) or len(rows) != count:
        raise MarketDataError("incorrect historical candle count")
    for row in rows:
        if not isinstance(row, list) or len(row) < 7:
            raise MarketDataError("malformed kline")
        close_time = int(row[6])
        close_time *= 1000 if close_time < 10**15 else 1
        if close_time >= boundary_us:
            raise MarketDataError("incomplete candle was returned")
    candles = _parse_candle_rows([[str(value) for value in row] for row in rows])
    expected = [boundary_us - (count - i) * 300_000_000 for i in range(count)]
    if [c.open_time_us for c in candles] != expected:
        raise MarketDataError("historical candles are stale, duplicated or missing")
    return [c.close for c in candles]


def fetch_closed_history(pairs: tuple[str, ...], count: int, boundary_seconds: int) -> dict[str, list[float]]:
    if not 1 <= count <= 1000 or boundary_seconds % 300:
        raise ValueError("invalid candle request")
    history = {}
    for pair in pairs:
        if pair not in SYMBOLS:
            raise ValueError("no historical symbol mapping for pair")
        params = urlencode({"symbol": SYMBOLS[pair], "interval": "5m", "limit": count, "endTime": boundary_seconds * 1000 - 1})
        try:
            payload = _public_payload("https://data-api.binance.vision/api/v3/klines?" + params)
            if len(payload) > 1_000_000:
                raise MarketDataError("historical response exceeds limit")
            history[pair] = closed_prices(json.loads(payload), count, boundary_seconds)
        except (OSError, ValueError, TypeError, IndexError) as exc:
            detail = "HTTP " + str(exc.code) if isinstance(exc, HTTPError) else type(exc).__name__
            raise MarketDataError("public candle feed unavailable (" + detail + ")") from None
    return history
