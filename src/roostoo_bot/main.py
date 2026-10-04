from __future__ import annotations

import argparse
import time

from .client import RoostooAPIError, RoostooClient
from .config import Settings, load_dotenv
from .engine import BotEngine
from .logging_utils import event, setup_logger


def main() -> int:
    parser = argparse.ArgumentParser(description="Roostoo low-frequency bot baseline")
    parser.add_argument("--once", action="store_true", help="run one decision cycle, then exit")
    parser.add_argument("--dry-run", action="store_true", help="force observation even if .env requests orders")
    args = parser.parse_args()
    load_dotenv()
    if args.dry_run:
        import os
        os.environ["DRY_RUN"] = "true"
    settings = Settings.from_env()
    logger = setup_logger(settings.data_dir)
    engine = BotEngine(RoostooClient(settings.api_key, settings.secret_key, allow_orders=not settings.dry_run and settings.live_trading_enabled), settings)
    logger.info("bot started dry_run=%s pairs=%s", settings.dry_run, ",".join(settings.pairs))
    while True:
        failed = False
        try:
            failed = engine.run_once() == "blocked"
        except RoostooAPIError as exc:
            failed = True
            event(settings.data_dir, "api_failure", error=str(exc))
            logger.error("API failure: %s", exc)
        except Exception as exc:
            failed = True
            event(settings.data_dir, "unexpected_failure", error_type=type(exc).__name__)
            logger.error("cycle failed (%s); inspect account/state before enabling orders", type(exc).__name__)
        if args.once:
            return 1 if failed else 0
        time.sleep(settings.poll_seconds - time.time() % settings.poll_seconds + 0.2)


if __name__ == "__main__":
    raise SystemExit(main())
