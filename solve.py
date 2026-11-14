#!/usr/bin/env python3
"""Run the reference solution on one mission.

    python solve.py --seed 3                          # in-process
    python solve.py --seed 3 --transport mcp          # through the MCP server over stdio
    python solve.py --url http://mcp-server:8000/mcp  # against a running MCP server (Harbor)

The reference only ever calls the seven mission tools.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents import reference  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--transport", choices=["local", "mcp"], default="local")
    ap.add_argument("--url", default=None)
    a = ap.parse_args()
    if a.url:
        from bomber.mcp_client import McpClient
        client = McpClient(url=a.url)
        reference.run(client)
        client.close()
        print("Reference mission played. The verifier reads the score from the server.")
        return 0
    from bomber.runner import run_episode
    rec = run_episode(reference.run, a.seed, transport=a.transport)
    print(f"seed {a.seed}: mission score {rec['score']}")
    for t in rec["targets_scored"]:
        print(f"  target {t['id']}: miss {t['distance']} m, score {t['score']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
