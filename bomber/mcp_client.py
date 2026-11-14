"""Synchronous MCP client: lets any agent in this repo play through a real MCP server
(stdio transport) with the same `client.call(tool, **args)` interface as LocalClient."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import threading

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class McpClient:
    """McpClient(seed) spawns the server over stdio. McpClient(url="http://host:8000/mcp") connects to
    an already running server over streamable HTTP (the transport used inside Harbor)."""

    def __init__(self, seed: int = 1, result_path: str | None = None, url: str | None = None):
        env = dict(os.environ, BOMBER_SEED=str(seed))
        if result_path:
            env["BOMBER_RESULT"] = result_path
        self._url = url
        self._params = StdioServerParameters(command=sys.executable, args=["-m", "bomber.mcp_server"], env=env)
        self._loop = asyncio.new_event_loop()
        self._ready = threading.Event()
        self._stop: asyncio.Event | None = None
        self._session: ClientSession | None = None
        self._error: BaseException | None = None
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait(30)
        if self._error or self._session is None:
            raise RuntimeError(f"MCP server did not start: {self._error}")

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._main())
        except BaseException as e:  # noqa: BLE001
            self._error = e
            self._ready.set()

    async def _main(self) -> None:
        self._stop = asyncio.Event()
        if self._url:
            try:
                from mcp.client.streamable_http import streamablehttp_client as http_client
            except ImportError:  # newer mcp releases renamed the helper
                from mcp.client.streamable_http import streamable_http_client as http_client
            transport = http_client(self._url)
        else:
            transport = stdio_client(self._params)
        async with transport as streams:
            read, write = streams[0], streams[1]
            async with ClientSession(read, write) as session:
                await session.initialize()
                self._session = session
                self._ready.set()
                await self._stop.wait()

    def _sync(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result(60)

    def list_tools(self) -> list[dict]:
        tools = self._sync(self._session.list_tools()).tools
        return [{"name": t.name, "description": t.description, "parameters": t.input_schema
                 if hasattr(t, "input_schema") else t.inputSchema} for t in tools]

    def call(self, tool: str, **args) -> dict:
        res = self._sync(self._session.call_tool(tool, args))
        text = "".join(getattr(c, "text", "") for c in res.content)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"error": text[:300] or "Invalid call."}

    def close(self) -> None:
        if self._stop is not None:
            self._loop.call_soon_threadsafe(self._stop.set)
        self._thread.join(10)
        if not self._thread.is_alive() and not self._loop.is_closed():
            self._loop.close()
