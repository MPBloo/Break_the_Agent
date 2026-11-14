"""Where did an agent lose its points?

For any episode we replay two counterfactuals on the same world, both using the reference's own
code, so the only thing that changes is the decision under study:

  B  "reference on the agent's experiments": the agent's test drops are replayed, then the
     reference fits and aims. If B is low, the experiments themselves were uninformative.
  C  "agent's hypothesis, reference aiming": the last hypothesis the agent worked with is aimed
     by the reference. If C is low while B is high, the data was fine but the fit was not.

With A the reference's own score and D the agent's actual score:
    A - B = lost by the choice of experiments
    B - C = lost while fitting a hypothesis to the data
    C - D = lost while aiming and executing the real drops
"""
from __future__ import annotations

from .config import Config, DEFAULT
from .client import LocalClient
from .episode import Episode, _HYP_KEYS

from agents.reference import Reference


def _run(seed: int, cfg: Config, play) -> float:
    episode = Episode(seed, cfg)
    try:
        play(Reference(LocalClient(episode)))
    except Exception:  # noqa: BLE001
        pass
    episode.finalize()
    return episode.score()["score"]


def final_hypothesis(record: dict) -> dict | None:
    """The last hypothesis the agent used: preferably in `simulate` (what it aimed with), else in `compare`."""
    for tool in ("simulate", "compare"):
        for e in reversed(record["log"]):
            if e["tool"] == tool and "error" not in e["result"]:
                return {k: e["args"][k] for k in _HYP_KEYS}
    return None


def attribute(record: dict, reference_score: float, cfg: Config = DEFAULT) -> dict:
    seed, d = record["seed"], record["score"]
    tests = [e["args"] for e in record["log"] if e["tool"] == "test_drop" and "error" not in e["result"]]
    b = _run(seed, cfg, lambda ref: ref.run_on_given_tests(tests))
    hyp = final_hypothesis(record)
    c = _run(seed, cfg, lambda ref: ref.run_with_hypothesis(hyp)) if hyp else d
    return {
        "reference": reference_score,
        "ref_on_agent_tests": b,
        "agent_hypothesis_ref_aim": c,
        "agent": d,
        "lost_experiments": round(reference_score - b, 4),
        "lost_fitting": round(b - c, 4),
        "lost_aiming": round(c - d, 4),
        "final_hypothesis": hyp,
    }
