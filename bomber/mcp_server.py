"""MCP server: exposes one Canadair firefighting mission (one Episode) as MCP tools.

    python -m bomber.mcp_server                      # stdio transport (default)
    python -m bomber.mcp_server --transport http     # streamable HTTP on :8000/mcp
                                                     # plus GET /score for the verifier

Environment variables:
    BOMBER_SEED     world seed of the mission (default 1)
    BOMBER_VARIANT  "base" (default) or "weather" (the wind changes before the operation)
    BOMBER_SALT     secret mixed into world generation (default empty). Set it whenever the agent
                    can run code and read this public repository, or the hidden air can be rebuilt
                    from the seed. harbor/make_tasks.py sets a random one.
    BOMBER_RESULT   if set, the full episode record (score, log, hidden truth) is written to this
                    path after every tool call. This file is for the harness / verifier. It must
                    live where the agent cannot read it.

The tools are thin wrappers around Episode.call_tool, the same entry point used by the in-process
evaluation, so both paths behave identically.
"""
import argparse
import json
import os
import tempfile
from typing import Annotated

from pydantic import Field

try:                                    # mcp 1.x
    from mcp.server.fastmcp import FastMCP
except ImportError:                     # mcp 2.x renamed it
    from mcp.server.mcpserver import MCPServer as FastMCP

from .episode import Episode, TOOLS, INSTRUCTION, _HYP_PROPS, _DROP_PROPS

_DESC = {t["name"]: t["description"] for t in TOOLS}


def _f(props, key):
    return Annotated[float, Field(description=props[key]["description"])]


Drag, WindSpeed, WindDir, Shear, Veer, Updraft = (_f(_HYP_PROPS, k) for k in _HYP_PROPS)
Heading, Altitude, Speed, X, Y = (_f(_DROP_PROPS, k) for k in _DROP_PROPS)
TargetId = Annotated[int, Field(description="Target id, 1 to 5.")]


def build_server(episode: Episode, result_path: str | None = None) -> FastMCP:
    mcp = FastMCP("canadair-firefighting", instructions=INSTRUCTION)

    def call(name: str, **args) -> dict:
        out = episode.call_tool(name, args)
        if result_path:
            d = os.path.dirname(os.path.abspath(result_path))
            fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
            with os.fdopen(fd, "w") as f:
                json.dump(episode.result(), f)
            os.replace(tmp, result_path)
        return out

    @mcp.tool(name="get_mission", description=_DESC["get_mission"])
    def get_mission() -> dict:
        return call("get_mission")

    @mcp.tool(name="test_drop", description=_DESC["test_drop"])
    def test_drop(heading: Heading, altitude: Altitude, speed: Speed, x: X, y: Y) -> dict:
        return call("test_drop", heading=heading, altitude=altitude, speed=speed, x=x, y=y)

    @mcp.tool(name="compare", description=_DESC["compare"])
    def compare(drag: Drag, wind_speed: WindSpeed, wind_dir: WindDir, shear: Shear, veer: Veer,
                updraft: Updraft) -> dict:
        return call("compare", drag=drag, wind_speed=wind_speed, wind_dir=wind_dir, shear=shear,
                    veer=veer, updraft=updraft)

    @mcp.tool(name="simulate", description=_DESC["simulate"])
    def simulate(drag: Drag, wind_speed: WindSpeed, wind_dir: WindDir, shear: Shear, veer: Veer,
                 updraft: Updraft, heading: Heading, altitude: Altitude, speed: Speed, x: X, y: Y) -> dict:
        return call("simulate", drag=drag, wind_speed=wind_speed, wind_dir=wind_dir, shear=shear,
                    veer=veer, updraft=updraft, heading=heading, altitude=altitude, speed=speed, x=x, y=y)

    if episode.cfg.weather_change:
        from .episode import MEASURE_WIND

        @mcp.tool(name="measure_wind", description=MEASURE_WIND["description"])
        def measure_wind(altitude: Altitude) -> dict:
            return call("measure_wind", altitude=altitude)

    @mcp.tool(name="begin_operation", description=_DESC["begin_operation"])
    def begin_operation() -> dict:
        return call("begin_operation")

    @mcp.tool(name="drop", description=_DESC["drop"])
    def drop(target: TargetId, heading: Heading, altitude: Altitude, speed: Speed, x: X, y: Y) -> dict:
        return call("drop", target=target, heading=heading, altitude=altitude, speed=speed, x=x, y=y)

    @mcp.tool(name="declare_done", description=_DESC["declare_done"])
    def declare_done() -> dict:
        return call("declare_done")

    @mcp.custom_route("/score", methods=["GET"])
    async def score(request):  # noqa: ARG001
        """For the verifier only (HTTP transport). Reading the score ENDS the mission first, so it
        cannot be used as feedback between two drops."""
        from starlette.responses import JSONResponse
        episode.finalize()
        call_result = episode.result()
        if result_path:
            with open(result_path, "w") as f:
                json.dump(call_result, f)
        return JSONResponse({"score": call_result["score"], "counts": call_result["counts"]})

    return mcp


def _http_app(mcp, host: str):
    """The server sits on a private container network and is reached by service name
    (http://mcp-server:8000/mcp), so the localhost-only Host check must be off."""
    try:
        from mcp.server.transport_security import TransportSecuritySettings
        security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
    except ImportError:
        security = None
    try:                                    # mcp 2.x
        return mcp.streamable_http_app(host=host, transport_security=security)
    except TypeError:                       # mcp 1.x keeps it in the server settings
        if security is not None and hasattr(mcp, "settings"):
            mcp.settings.transport_security = security
        return mcp.streamable_http_app()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--seed", type=int, default=int(os.environ.get("BOMBER_SEED", "1")))
    a = ap.parse_args()
    from .config import variant
    episode = Episode(a.seed, variant(os.environ.get("BOMBER_VARIANT")), salt=os.environ.get("BOMBER_SALT", ""))
    mcp = build_server(episode, os.environ.get("BOMBER_RESULT"))
    if a.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        import uvicorn
        uvicorn.run(_http_app(mcp, a.host), host=a.host, port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
