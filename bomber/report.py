"""Build the self-contained results viewer (results/report.html) from episode records."""
from __future__ import annotations

import datetime
import json
import os

from .config import DEFAULT
from .episode import briefing

HERE = os.path.dirname(os.path.abspath(__file__))
SKELETON_HEAD = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
                 '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                 '<style>body{margin:0;font:14px system-ui,-apple-system,"Segoe UI",sans-serif}'
                 'img{max-width:100%}[hidden]{display:none!important}</style>\n</head>\n<body>\n')
SKELETON_TAIL = "\n</body>\n</html>\n"


def _thin(path):
    """Keep every other sample of a path, and always its last point."""
    if not path:
        return path
    out = path[::2]
    if out[-1] != path[-1]:
        out.append(path[-1])
    return out


def _compact_result(tool: str, result: dict) -> dict:
    if "error" in result:
        return {"error": result["error"]}
    if tool == "compare":
        return {k: result[k] for k in ("mean_miss", "mean_abs_dt", "calculations_left")}
    if tool == "get_mission":
        return {"status": result.get("status")}
    if tool == "begin_operation":
        return {"status": result["status"], "calculations_left": result["calculations_left"]}
    return result


def _compact_episode(rec: dict) -> dict:
    deb = rec["debrief"]
    return {
        "agent": rec["agent"], "seed": rec["seed"], "run": rec["run"], "score": rec["score"],
        "counts": rec["counts"], "scored": rec["targets_scored"],
        "air": deb["air"], "targets": deb["targets"],
        "tests": [{**{k: v for k, v in t.items() if k != "path"}, "path": _thin(t["path"])} for t in deb["tests"]],
        "drops": [{**{k: v for k, v in d.items() if k != "path"}, "path": _thin(d["path"])} for d in deb["drops"]],
        "log": [[e["n"], e["phase"], e["tool"], e["args"], _compact_result(e["tool"], e["result"])] for e in rec["log"]],
        "notes": (rec.get("agent_extra") or {}).get("notes") or [],
        "usage": (rec.get("agent_extra") or {}).get("usage"),
        "att": rec.get("attribution"),
        "error": rec.get("agent_error"),
        "replay_ok": rec.get("replay_ok"),
    }


def build_report(groups: list[dict], summary: dict, out_path: str, fragment_path: str | None = None) -> int:
    """Write the viewer. Returns its size in bytes. `fragment_path`, if given, also receives the
    page without the document skeleton (the form expected when publishing it as a hosted page)."""
    episodes, agents = [], []
    stats = {a["id"]: a for a in summary["agents"]}
    for g in groups:
        idx = []
        for rec in g["episodes"]:
            idx.append(len(episodes))
            episodes.append(_compact_episode(rec))
        s = stats[g["id"]]
        agents.append({"id": g["id"], "label": g["label"], "group": g["group"], "desc": g["desc"],
                       "n": s["n"], "mean": s["mean"], "std": s["std"], "min": s["min"], "max": s["max"],
                       "lost": s.get("lost"), "episodes": idx})
    data = {
        "meta": {"config": summary["config"], "seeds": summary["seeds"],
                 "generated": datetime.date.today().isoformat()},
        "briefing": briefing(DEFAULT),
        "agents": agents,
        "episodes": episodes,
    }
    with open(os.path.join(HERE, "report_template.html")) as f:
        template = f.read()
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    page = template.replace("/*__REPORT_DATA__*/null", payload)
    with open(out_path, "w") as f:
        f.write(SKELETON_HEAD + page + SKELETON_TAIL)
    if fragment_path:
        with open(fragment_path, "w") as f:
            f.write(page)
    return len(page.encode())
