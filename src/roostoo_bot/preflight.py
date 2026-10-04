"""Read-only TEST-account health check. This entry point cannot submit orders."""
from __future__ import annotations
import json
import os
from pathlib import Path
import time

from .client import RoostooClient
from .config import Settings, load_dotenv
from .engine import BotEngine
from .market_data import MarketDataError
from .portfolio import balances, equity


def main() -> int:
    load_dotenv()
    os.environ["CREDENTIAL_SET"] = "testing"
    os.environ["DRY_RUN"] = "true"
    os.environ["LIVE_TRADING_ENABLED"] = "false"
    settings = Settings.from_env()
    client = RoostooClient(settings.api_key, settings.secret_key)
    engine = BotEngine(client, settings)
    try:
        server_ms = float(client.server_time()["ServerTime"])
        clock_delta = abs(time.time() - server_ms / 1000)
        if clock_delta > settings.max_quote_age_seconds:
            raise ValueError("server clock mismatch")
        engine._rules()
        wallet = balances(client.balance()["Wallet"], settings.pairs)
        pending = client.pending_count()["TotalPending"]
        if not isinstance(pending, int) or isinstance(pending, bool) or pending < 0:
            raise ValueError("invalid pending order count")
        # A balance request signs only timestamp. Exercise decoded pair values
        # on a read-only POST too, without enabling any order submissions.
        recent = client.query_orders(settings.pairs[0], limit=1)
        if not isinstance(recent.get("OrderMatched"), list):
            raise ValueError("invalid read-only order history response")
        quotes = engine._quotes()
        history_counts = None
        if settings.signal_source == "binance":
            history = engine.market_data(settings.pairs, settings.slow_window + 1, int(time.time() // 300) * 300)
            history_counts = {p:len(prices) for p,prices in history.items()}
        report = {"credential_set": "testing", "orders_enabled": False, "equity": equity(wallet, quotes),
                  "pending_orders": pending, "server_clock_delta_seconds": clock_delta,
                  "authenticated_pair_query_ok": True,
                  "rules": {p: {"amount_precision": r.amount_precision, "min_notional": r.min_notional, "can_trade": r.can_trade} for p,r in engine.rules.items()},
                  "spread_fraction": {p:q.spread for p,q in quotes.items()},
                  "signal_source": settings.signal_source, "closed_history_counts": history_counts,
                  "strategy_approved_for_live": False}
        (settings.data_dir / "preflight.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        print(json.dumps(report, indent=2))
        return 1 if pending else 0
    except Exception as exc:
        # MarketDataError contains only our own safe status/type description.
        detail = str(exc) if isinstance(exc, MarketDataError) else type(exc).__name__
        print(f"read-only preflight failed ({detail}); no order was submitted")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
