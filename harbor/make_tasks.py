#!/usr/bin/env python3
"""Generate self-contained Harbor tasks, one per seed.

    python harbor/make_tasks.py --seeds 5          # writes harbor/tasks/canadair-firefighting-seed-1 ... -5
    harbor run -p harbor/tasks/canadair-firefighting-seed-1 -a oracle       # the reference solution
    harbor run -p harbor/tasks/canadair-firefighting-seed-1 -a opencode -m <model>

Layout follows Harbor's official multi-container MCP example (examples/tasks/hello-mcp):
the agent runs in `main`, the mission lives in a separate `mcp-server` container that the agent
can only reach through MCP, and the verifier reads the score from the server.

Not exercised in this repository's CI: no Docker daemon was available where it was written.
The server, the HTTP transport, the solution and the /score endpoint it relies on are tested.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from bomber.episode import INSTRUCTION  # noqa: E402

TASK_TOML = '''schema_version = "1.1"

[task]
name = "junction/canadair-firefighting-seed-{seed}"
description = "Calibrate an unknown atmosphere with ten test drops, then deliver water to five wildfire hotspots."
authors = []
keywords = ["experiment-design", "system-identification", "mcp"]

[metadata]
seed = {seed}

[verifier]
timeout_sec = 120.0

[agent]
timeout_sec = 3600.0

[environment]
build_timeout_sec = 600.0
cpus = 1
memory_mb = 2048
storage_mb = 10240
gpus = 0
[[environment.mcp_servers]]
name = "canadair-firefighting"
transport = "streamable-http"
url = "http://mcp-server:8000/mcp"
args = []

[verifier.env]

[environment.env]

[solution.env]
'''

INSTRUCTION_MD = '''# Canadair Firefighting

{instruction}

The mission tools are served by the MCP server `canadair-firefighting` at `http://mcp-server:8000/mcp`:
`get_mission`, `test_drop`, `compare`, `simulate`, `begin_operation`, `drop`, `declare_done`.
Everything you need to know is in the briefing returned by `get_mission`.
'''

MAIN_DOCKERFILE = '''FROM ubuntu:24.04

RUN apt-get update && apt-get install -y curl python3 python3-pip && rm -rf /var/lib/apt/lists/*

WORKDIR /app
'''

COMPOSE = '''# Merged on top of Harbor's base docker-compose config (see Harbor's hello-mcp example).
services:
  main:
    depends_on:
      mcp-server:
        condition: service_healthy

  mcp-server:
    build:
      context: ./mcp-server
    environment:
      BOMBER_SEED: "{seed}"
    expose:
      - "8000"
    healthcheck:
      test: ["CMD", "python", "-c", "import socket; s=socket.create_connection(('localhost',8000),timeout=2); s.close()"]
      interval: 2s
      timeout: 5s
      retries: 15
      start_period: 5s
'''

SERVER_DOCKERFILE = '''FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir "mcp>=1.12" uvicorn
COPY bomber /app/bomber

EXPOSE 8000
CMD ["python", "-m", "bomber.mcp_server", "--transport", "http", "--port", "8000"]
'''

SOLVE_SH = '''#!/bin/bash
# Reference solution: plays the mission through the MCP tools only.
set -e
cd "$(dirname "$0")"
pip install --break-system-packages --quiet "mcp>=1.12" 2>/dev/null || pip install --quiet "mcp>=1.12"
python3 solve_http.py http://mcp-server:8000/mcp
'''

SOLVE_HTTP = '''import sys

import reference
from mcp_client import McpClient

client = McpClient(url=sys.argv[1])
reference.run(client)
client.close()
print("Reference mission played.")
'''

TEST_SH = '''#!/bin/bash
# Verifier. The score is computed by the mission server from the real drops. Asking for it ends
# the mission first, so it is not a feedback channel.
mkdir -p /logs/verifier
python3 - << 'PY'
import json, urllib.request
try:
    with urllib.request.urlopen("http://mcp-server:8000/score", timeout=60) as r:
        score = json.loads(r.read())["score"]
except Exception as e:
    print("verifier could not read the score:", e)
    score = 0
open("/logs/verifier/reward.txt", "w").write(str(score))
print("reward", score)
PY
'''


def write(path: str, content: str, executable: bool = False) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    if executable:
        os.chmod(path, 0o755)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=int, default=3, help="generate tasks for seeds 1..N")
    ap.add_argument("--out", default=os.path.join(ROOT, "harbor", "tasks"))
    a = ap.parse_args()
    for seed in range(1, a.seeds + 1):
        d = os.path.join(a.out, f"canadair-firefighting-seed-{seed}")
        shutil.rmtree(d, ignore_errors=True)
        write(os.path.join(d, "task.toml"), TASK_TOML.format(seed=seed))
        write(os.path.join(d, "instruction.md"), INSTRUCTION_MD.format(instruction=INSTRUCTION))
        write(os.path.join(d, "environment", "Dockerfile"), MAIN_DOCKERFILE)
        write(os.path.join(d, "environment", "docker-compose.yaml"), COMPOSE.format(seed=seed))
        write(os.path.join(d, "environment", "mcp-server", "Dockerfile"), SERVER_DOCKERFILE)
        shutil.copytree(os.path.join(ROOT, "bomber"), os.path.join(d, "environment", "mcp-server", "bomber"),
                        ignore=shutil.ignore_patterns("__pycache__", "analysis.py", "report*", "runner.py"))
        write(os.path.join(d, "solution", "solve.sh"), SOLVE_SH, executable=True)
        write(os.path.join(d, "solution", "solve_http.py"), SOLVE_HTTP)
        shutil.copy(os.path.join(ROOT, "agents", "reference.py"), os.path.join(d, "solution", "reference.py"))
        shutil.copy(os.path.join(ROOT, "bomber", "mcp_client.py"), os.path.join(d, "solution", "mcp_client.py"))
        write(os.path.join(d, "tests", "test.sh"), TEST_SH, executable=True)
        print("wrote", os.path.relpath(d, ROOT))


if __name__ == "__main__":
    main()
