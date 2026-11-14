#!/usr/bin/env python3
"""One command to reproduce every reported number.

    python run_eval.py                 # reference + heuristics + baselines on seeds 1..10, then the report
    python run_eval.py --seeds 30      # more seeds
    python run_eval.py --quick         # 3 seeds, for a fast check

What it does:
  1. Plays every scripted agent on every seed (deterministic: same seed, same score).
  2. Plays the reference once more through the real MCP server and checks the score is identical.
  3. Loads stored frontier-model transcripts from results/llm/ (produced by run_llm.py), replays
     each one call by call on a fresh world and checks the stored score is reproduced.
  4. Attributes every non-reference episode's lost points to experiments / fitting / aiming.
  5. Writes results/summary.md, results/summary.json and results/report.html.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import statistics as st
import sys
import time
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from agents.registry import AGENTS  # noqa: E402
from bomber.analysis import attribute  # noqa: E402
from bomber.config import DEFAULT  # noqa: E402
from bomber.report import build_report  # noqa: E402
from bomber.runner import replay, run_episode  # noqa: E402


def _play(job):
    agent, seed = job
    rec = run_episode(AGENTS[agent]["fn"], seed)
    rec.update(agent=agent, run=1)
    return rec


def _attribute(job):
    rec, ref_score = job
    return attribute(rec, ref_score)


def _load_llm(out_dir: str) -> list[dict]:
    recs = []
    for path in sorted(glob.glob(os.path.join(out_dir, "llm", "*", "*.json"))):
        with open(path) as f:
            rec = json.load(f)
        rec["_path"] = os.path.relpath(path, out_dir)
        recs.append(rec)
    return recs


def _stats(scores: list[float]) -> dict:
    return {"n": len(scores), "mean": round(st.mean(scores), 4),
            "std": round(st.pstdev(scores), 4) if len(scores) > 1 else 0.0,
            "min": round(min(scores), 4), "max": round(max(scores), 4)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=int, default=10, help="evaluate seeds 1..N (default 10)")
    ap.add_argument("--quick", action="store_true", help="shortcut for --seeds 3")
    ap.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    ap.add_argument("--out", default=os.path.join(ROOT, "results"))
    ap.add_argument("--no-mcp-check", action="store_true", help="skip the MCP parity check")
    ap.add_argument("--fragment", default=None, help=argparse.SUPPRESS)  # report without <html> skeleton
    a = ap.parse_args()
    seeds = list(range(1, (3 if a.quick else a.seeds) + 1))
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    ok = True

    print(f"[1/5] Playing {len(AGENTS)} scripted agents on seeds {seeds[0]}..{seeds[-1]} ...", flush=True)
    with Pool(a.workers) as pool:
        records = pool.map(_play, [(ag, s) for ag in AGENTS for s in seeds])
    ref_by_seed = {r["seed"]: r["score"] for r in records if r["agent"] == "reference"}

    if a.no_mcp_check:
        print("[2/5] MCP parity check skipped.")
    else:
        try:
            via_mcp = run_episode(AGENTS["reference"]["fn"], seeds[0], transport="mcp")["score"]
            same = via_mcp == ref_by_seed[seeds[0]]
            ok &= same
            print(f"[2/5] MCP parity: reference on seed {seeds[0]} scores {via_mcp} over MCP, "
                  f"{ref_by_seed[seeds[0]]} in-process -> {'identical' if same else 'MISMATCH'}")
        except ImportError:
            print("[2/5] MCP parity check skipped: the `mcp` package is not installed.")

    llm = _load_llm(a.out)
    bad = 0
    for rec in llm:
        again = replay(rec)
        rec["replay_ok"] = again["score"] == rec["score"]
        bad += not rec["replay_ok"]
        if rec["seed"] not in ref_by_seed:
            ref_by_seed[rec["seed"]] = run_episode(AGENTS["reference"]["fn"], rec["seed"])["score"]
    ok &= bad == 0
    print(f"[3/5] Frontier-model transcripts: {len(llm)} found in results/llm/, "
          f"{len(llm) - bad} reproduce their stored score on replay" + (f", {bad} DO NOT" if bad else "") + ".")

    print("[4/5] Attributing lost points ...", flush=True)
    todo = [r for r in records if AGENTS[r["agent"]]["group"] == "heuristic"] + llm
    with Pool(a.workers) as pool:
        for rec, att in zip(todo, pool.map(_attribute, [(r, ref_by_seed[r["seed"]]) for r in todo])):
            rec["attribution"] = att

    # ---- summary -----------------------------------------------------------------------------
    groups = []
    for name, info in AGENTS.items():
        rs = [r for r in records if r["agent"] == name]
        groups.append({"id": name, "label": info["label"], "group": info["group"], "desc": info["desc"], "episodes": rs})
    by_model: dict[str, list[dict]] = {}
    for rec in llm:
        by_model.setdefault(rec["agent"], []).append(rec)
    for model, rs in by_model.items():
        groups.insert(1, {"id": model, "label": model, "group": "frontier",
                          "desc": "Frontier model in a plain tool-calling loop: no shell, no code execution.",
                          "episodes": rs})

    summary = {"config": DEFAULT.as_dict(), "seeds": seeds, "agents": []}
    for g in groups:
        sc = [r["score"] for r in g["episodes"]]
        row = {"id": g["id"], "label": g["label"], "group": g["group"], **_stats(sc),
               "scores": [{"seed": r["seed"], "run": r["run"], "score": r["score"]} for r in g["episodes"]]}
        row["refused"] = sum(1 for r in g["episodes"] if (r.get("agent_extra") or {}).get("stopped") == "refusal")
        atts = [r["attribution"] for r in g["episodes"] if r.get("attribution")]
        if atts:
            row["lost"] = {k: round(st.mean(x[k] for x in atts), 4)
                           for k in ("lost_experiments", "lost_fitting", "lost_aiming")}
        summary["agents"].append(row)
    with open(os.path.join(a.out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)

    lines = ["# Canadair Firefighting: evaluation summary", "",
             f"Seeds {seeds[0]}..{seeds[-1]}. Scores are mission scores in [0, 1]. Scripted agents are deterministic.", "",
             "| Agent | Kind | Episodes | Mean | Std | Min | Max | Lost: experiments | Lost: fitting | Lost: aiming |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in summary["agents"]:
        lost = r.get("lost")
        cells = [f"{lost[k]:.2f}" for k in ("lost_experiments", "lost_fitting", "lost_aiming")] if lost else ["", "", ""]
        lines.append(f"| {r['label']} | {r['group']} | {r['n']} | {r['mean']:.3f} | {r['std']:.3f} | "
                     f"{r['min']:.3f} | {r['max']:.3f} | " + " | ".join(cells) + " |")
    lines += ["", "\"Lost\" columns: mean points lost against the reference on the same seeds, split by cause "
              "(see bomber/analysis.py).", ""]
    for r in summary["agents"]:
        if r["refused"]:
            done = [x["score"] for x, e in zip(r["scores"], next(g for g in groups if g["id"] == r["id"])["episodes"])
                    if (e.get("agent_extra") or {}).get("stopped") != "refusal"]
            lines += [f"{r['label']}: {r['refused']} of {r['n']} missions were cut short by the model provider's safety "
                      f"filter before any real drop and score 0. Mean over the {len(done)} completed missions: "
                      f"{st.mean(done):.3f}." if done else
                      f"{r['label']}: all {r['n']} missions were cut short by the model provider's safety filter.", ""]
    with open(os.path.join(a.out, "summary.md"), "w") as f:
        f.write("\n".join(lines))

    report = build_report(groups, summary, os.path.join(a.out, "report.html"), a.fragment)
    print(f"[5/5] Wrote results/summary.md, results/summary.json, results/report.html ({report // 1024} KB).")
    print()
    w = max(len(r["label"]) for r in summary["agents"])
    print(f"{'Agent':<{w}}  {'kind':<10} {'n':>3}  {'mean':>6} {'std':>6} {'min':>6} {'max':>6}")
    for r in summary["agents"]:
        print(f"{r['label']:<{w}}  {r['group']:<10} {r['n']:>3}  {r['mean']:>6.3f} {r['std']:>6.3f} {r['min']:>6.3f} {r['max']:>6.3f}")
    print(f"\nDone in {time.time() - t0:.0f} s." + ("" if ok else "  SOME CHECKS FAILED, see above."))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
