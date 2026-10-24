"""Per-user preferences, in ~/.config/maze-store/settings.json."""
from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULTS = {"notify_updates": True}


def path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "maze-store" / "settings.json"


def load() -> dict:
    out = dict(DEFAULTS)
    try:
        data = json.loads(path().read_text())
        if isinstance(data, dict):
            out.update({k: v for k, v in data.items() if k in DEFAULTS})
    except (OSError, ValueError):
        pass
    return out


def save(values: dict) -> None:
    p = path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps({**load(), **values}, indent=1))
        os.replace(tmp, p)
    except OSError:
        pass
