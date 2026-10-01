from __future__ import annotations

import argparse
import time

from .client import RoostooAPIError, RoostooClient
from .config import Settings, load_dotenv
from .engine import BotEngine
from .logging_utils import setup_logger


def main() -> int:
    parser = argparse.ArgumentParser(description="Roostoo low-frequency bot baseline")
    parser.add_argument("--once", action="store_true", help="run one decision cycle, then exit")
    args = parser.parse_args()
    load_dotenv()
    settings = Settings.from_env()
    logger = setup_logger(settings.data_dir)
    engine = BotEngine(RoostooClient(settings.api_key, settings.secret_key), settings)
    logger.info("bot started dry_run=%s pairs=%s", settings.dry_run, ",".join(settings.pairs))
    while True:
        try:
            engine.run_once()
        except RoostooAPIError as exc:
            logger.exception("API failure: %s", exc)
        except Exception:
            logger.exception("unexpected failure")
        if args.once:
            return 0
        time.sleep(settings.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())

