#!/usr/bin/env python3
"""Run a frontier model on the mission and store its transcripts under results/llm/<label>/.

    cp .env.example .env        # then put your key in .env
    python run_llm.py --seeds 3 --runs 3

Settings come from .env (or the environment); command-line options override them.
  Claude:  LLM_PROVIDER=anthropic, ANTHROPIC_API_KEY, LLM_MODEL (default claude-opus-5-5)
  Others:  LLM_PROVIDER=gemini|openai|openrouter, LLM_API_KEY, LLM_MODEL, or --base-url for any
           OpenAI-compatible endpoint (e.g. a local vLLM server hosting a small fine-tuned model)

The model plays through a plain tool-calling loop: the seven mission tools, no shell, no code
execution.

Stored transcripts are picked up by `python run_eval.py`, which replays them to verify their
score, attributes the lost points and adds them to the report. Existing files are not re-run.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from bomber.envfile import load_env  # noqa: E402

load_env(os.path.join(ROOT, ".env"))     # before the agents read their settings

from agents.llm_agent import LLMConfig, make_agent  # noqa: E402
from bomber.config import variant  # noqa: E402
from bomber.runner import run_episode  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=os.environ.get("LLM_MODEL"))
    ap.add_argument("--provider", default=os.environ.get("LLM_PROVIDER", "gemini"))
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--label", default=None, help="name shown in the report (default: the model id)")
    ap.add_argument("--seeds", type=int, default=3, help="play seeds 1..N (default 3)")
    ap.add_argument("--runs", type=int, default=3, help="independent runs per seed (default 3)")
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--transport", choices=["local", "mcp"], default="local",
                    help="'mcp' plays through the real MCP server over stdio")
    ap.add_argument("--variant", default="base", choices=["base", "weather"],
                    help="'weather': the wind changes between calibration and operation")
    ap.add_argument("--out", default=os.path.join(ROOT, "results"))
    a = ap.parse_args()

    if a.provider == "anthropic" and not a.base_url:
        try:
            from agents.anthropic_agent import ClaudeConfig, make_agent as make_claude_agent
        except ImportError:
            print("The Anthropic SDK is not installed. Run: pip install anthropic")
            return 2
        cfg = ClaudeConfig(model=a.model)
        if not cfg.ready():
            print("Missing key: put ANTHROPIC_API_KEY in .env (see .env.example).")
            return 2
        agent = make_claude_agent(cfg)
        print(f"Claude agent: model {cfg.model}, effort {cfg.effort}, "
              f"refusal fallbacks {'on' if cfg.fallbacks else 'off'}.")
    else:
        cfg = LLMConfig(model=a.model, provider=a.provider, base_url=a.base_url)
        if not cfg.ready():
            print("Missing configuration: set LLM_API_KEY and LLM_MODEL in .env (see .env.example), "
                  "or pass --model with --provider or --base-url.")
            return 2
        agent = make_agent(cfg)
    label = a.label or cfg.model
    folder = os.path.join(a.out, "llm", re.sub(r"[^A-Za-z0-9._-]+", "_", label))
    os.makedirs(folder, exist_ok=True)

    def one(job):
        seed, run = job
        path = os.path.join(folder, f"seed{seed:03d}_run{run}.json")
        if os.path.exists(path):
            with open(path) as f:
                return seed, run, json.load(f)["score"], "cached"
        rec = run_episode(agent, seed, cfg=variant(a.variant), transport=a.transport)
        rec.update(agent=label, run=run)
        if rec["agent_error"] and rec["counts"]["tool_calls"] == 0:
            return seed, run, None, rec["agent_error"]       # nothing happened: do not store
        with open(path, "w") as f:
            json.dump(rec, f)
        return seed, run, rec["score"], rec["agent_error"] or "ok"

    jobs = [(s, r) for s in range(1, a.seeds + 1) for r in range(1, a.runs + 1)]
    with ThreadPoolExecutor(a.parallel) as pool:
        for seed, run, score, status in pool.map(one, jobs):
            print(f"seed {seed} run {run}: score {score}  [{status}]", flush=True)
    print(f"\nTranscripts in {os.path.relpath(folder, ROOT)}/. Now run: python run_eval.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
