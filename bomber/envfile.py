"""Tiny .env loader (no dependency). Variables already set in the environment win."""
from __future__ import annotations

import os


def load_env(path: str) -> list[str]:
    """Read KEY=VALUE lines from `path` into os.environ. Returns the names it set."""
    if not os.path.isfile(path):
        return []
    names = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.removeprefix("export ").strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            if key and value and key not in os.environ:
                os.environ[key] = value
                names.append(key)
    return names
