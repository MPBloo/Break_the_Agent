"""Tool clients. Every agent talks to the environment through `client.call(tool, **args)`.

LocalClient calls the Episode in-process (fast, used for bulk evaluation).
McpClient (see mcp_client.py) sends the same calls to the MCP server over stdio.
Both go through Episode.call_tool, so results are identical.
"""
from __future__ import annotations

from .episode import Episode


class LocalClient:
    def __init__(self, episode: Episode):
        self._episode = episode

    def call(self, tool: str, **args) -> dict:
        return self._episode.call_tool(tool, args)

    def close(self) -> None:
        pass
