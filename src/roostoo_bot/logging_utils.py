from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def setup_logger(data_dir: Path) -> logging.Logger:
    data_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("roostoo_bot")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(data_dir / "bot.log", maxBytes=5_000_000, backupCount=3)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler())
    return logger


def event(data_dir: Path, kind: str, **details: Any) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": kind, **details}
    with (data_dir / "events.jsonl").open("a") as stream:
        stream.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
