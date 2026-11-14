#!/usr/bin/env python3
"""Stretch goal scaffold: turn reference missions into supervised fine-tuning data.

    python export_dataset.py --seeds 1000-1199 --out data/reference_sft.jsonl

Each line is one mission as a chat transcript in the OpenAI tool-calling format (system, user,
then alternating assistant tool calls and tool results), which most fine-tuning stacks accept
(Gemma, Qwen, Llama through their chat templates). Training seeds should stay disjoint from the
evaluation seeds (1..N of run_eval.py); the default range starts at 1000.

To measure the effect: serve the base model and the fine-tuned model behind an OpenAI-compatible
endpoint (vLLM, Ollama) and run `python run_llm.py --base-url http://localhost:8000/v1 --model ...`
for each, then `python run_eval.py`. Nothing in this repository has trained a model yet.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents import reference  # noqa: E402
from agents.llm_agent import SYSTEM  # noqa: E402
from bomber import Episode  # noqa: E402


class Recorder:
    """A client that keeps the complete, untruncated tool results, exactly as a model would see them."""

    def __init__(self, episode: Episode):
        self.episode = episode
        self.turns: list[tuple[str, dict, dict]] = []

    def call(self, tool: str, **args) -> dict:
        out = self.episode.call_tool(tool, args)
        self.turns.append((tool, args, out))
        return out


def mission_to_chat(seed: int) -> dict:
    rec = Recorder(Episode(seed))
    reference.run(rec)
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": "Begin the mission."}]
    for i, (tool, args, out) in enumerate(rec.turns):
        call_id = f"call_{i}"
        messages.append({"role": "assistant", "content": None, "tool_calls": [
            {"id": call_id, "type": "function", "function": {"name": tool, "arguments": json.dumps(args)}}]})
        messages.append({"role": "tool", "tool_call_id": call_id, "content": json.dumps(out)})
    return {"seed": seed, "score": rec.episode.score()["score"], "messages": messages}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", default="1000-1049", help="inclusive range, e.g. 1000-1199")
    ap.add_argument("--out", default="data/reference_sft.jsonl")
    ap.add_argument("--min-score", type=float, default=0.8, help="keep only missions at least this good")
    a = ap.parse_args()
    lo, hi = (int(x) for x in a.seeds.split("-"))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    kept = 0
    with open(a.out, "w") as f:
        for seed in range(lo, hi + 1):
            ex = mission_to_chat(seed)
            if ex["score"] >= a.min_score:
                f.write(json.dumps(ex) + "\n")
                kept += 1
    print(f"wrote {kept} of {hi - lo + 1} missions to {a.out}")


if __name__ == "__main__":
    main()
