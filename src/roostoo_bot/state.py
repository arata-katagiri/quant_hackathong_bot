from __future__ import annotations

import json
import fcntl
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class StateStore:
    def __init__(self, data_dir: Path, namespace: str = "testing.dry") -> None:
        self.path = data_dir / f"state.v2.{namespace}.json"
        self.lock_path = data_dir / "engine.lock"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 2, "prices": {}, "risk": {}}
        state = json.loads(self.path.read_text())
        if not isinstance(state, dict) or state.get("version") != 2:
            raise ValueError("invalid state; manual review required")
        return state

    def save(self, state: dict[str, Any]) -> None:
        temporary = self.path.with_suffix(".tmp")
        with temporary.open("w") as stream:
            json.dump(state, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(self.path)
        descriptor = os.open(self.path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    @contextmanager
    def lock(self):
        with self.lock_path.open("a") as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError("another engine is using this data directory") from None
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)
