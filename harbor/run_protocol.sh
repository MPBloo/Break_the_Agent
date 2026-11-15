#!/bin/bash
# The judges' protocol in Harbor: reference run, three agent runs, do-nothing and stop-early baselines,
# on every generated task. Usage (from the repository root, with ANTHROPIC_API_KEY set):
#
#   python harbor/make_tasks.py --seeds 3
#   bash harbor/run_protocol.sh anthropic/claude-sonnet-5-5
#
# The agent runs use OpenCode with its shell, file-writing and editing tools turned off, so it acts only
# through the mission's MCP tools (the setting the challenge announced). Set SHELL_TOOLS=1 to leave
# OpenCode's defaults on: with a shell, a model can re-implement the simulator from the briefing and skip
# the calculation budget (see README, "With a shell").
set -e
MODEL=${1:-anthropic/claude-sonnet-5-5}
OUT=${OUT:-jobs}
TASKS=${TASKS:-harbor/tasks}
NOSHELL='opencode_config={"tools":{"bash":false,"edit":false,"write":false,"patch":false}}'
harbor run -p "$TASKS" -n 3 -o "$OUT" --job-name reference -a oracle
if [ "${SHELL_TOOLS:-0}" = "1" ]; then
  harbor run -p "$TASKS" -n 3 -o "$OUT" --job-name agent -a opencode -m "$MODEL" -k 3 --ae ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY"
else
  harbor run -p "$TASKS" -n 3 -o "$OUT" --job-name agent -a opencode -m "$MODEL" -k 3 --ae ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" --ak "$NOSHELL"
fi
harbor run -p "$TASKS" -n 3 -o "$OUT" --job-name do-nothing -a nop
PYTHONPATH=. harbor run -p "$TASKS" -n 3 -o "$OUT" --job-name stop-early -a agents.harbor_stop_early:StopEarlyAgent
