from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class StateStore:
    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "state.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"prices": {}, "peak_equity": 0.0, "day": "", "day_start_equity": 0.0}
        return json.loads(self.path.read_text())

    def save(self, state: dict[str, Any]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, indent=2, sort_keys=True))
        temporary.replace(self.path)

