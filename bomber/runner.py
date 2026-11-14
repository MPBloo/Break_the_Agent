"""Run one agent on one seed and return the full episode record."""
from __future__ import annotations

import json
import os
import tempfile

from .client import LocalClient
from .config import Config, DEFAULT
from .episode import Episode


def run_episode(agent_fn, seed: int, cfg: Config = DEFAULT, transport: str = "local") -> dict:
    """transport='local' calls the Episode in-process; 'mcp' spawns the MCP server and plays over stdio."""
    error, extra = None, None
    if transport == "mcp":
        from .mcp_client import McpClient
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        client = McpClient(seed, path)
        try:
            extra = agent_fn(client)
        except Exception as e:  # noqa: BLE001
            error = f"{type(e).__name__}: {e}"
        client.close()
        with open(path) as f:
            content = f.read()
        os.unlink(path)
        record = json.loads(content) if content else Episode(seed, cfg).result()
    else:
        episode = Episode(seed, cfg)
        try:
            extra = agent_fn(LocalClient(episode))
        except Exception as e:  # an agent crash ends its episode; the drops made so far still count
            error = f"{type(e).__name__}: {e}"
        episode.finalize()
        record = episode.result()
    record["agent_error"] = error
    record["agent_extra"] = extra if isinstance(extra, dict) else None
    return record


def replay(record: dict, cfg: Config = DEFAULT) -> dict:
    """Re-execute a stored transcript call by call on a fresh world and re-score it.
    Used to verify that a reported score really follows from the logged actions."""
    episode = Episode(record["seed"], cfg)
    for entry in record["log"]:
        episode.call_tool(entry["tool"], entry["args"])
    episode.finalize()
    return episode.result()
