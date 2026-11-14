"""All scripted agents, in the order they appear in reports."""
from __future__ import annotations

from . import baselines, heuristics, reference

AGENTS = {
    "reference": {
        "fn": reference.run, "group": "reference", "label": "Reference solution",
        "desc": "Varied test drops in clear air, the same conditions repeated through the smoke, "
                "one-parameter-at-a-time fitting, secant aiming. Same tools and budgets as any agent."},
    "quick_fit": {
        "fn": heuristics.quick_fit, "group": "heuristic", "label": "Stops fitting early",
        "desc": "Same experiments as the reference, but one coarse fitting pass only."},
    "single_condition": {
        "fn": heuristics.single_condition, "group": "heuristic", "label": "One flight condition",
        "desc": "All ten test drops at the same heading, altitude and speed (five in clear air, five through smoke)."},
    "uniform_wind": {
        "fn": heuristics.uniform_wind, "group": "heuristic", "label": "Assumes uniform wind",
        "desc": "Varied headings and speeds at a single altitude; wind assumed identical at every height."},
    "ignores_smoke": {
        "fn": heuristics.ignores_smoke, "group": "heuristic", "label": "Ignores the smoke column",
        "desc": "Careful clear-air calibration at three altitudes, no test through smoke, updraft left at zero."},
    "textbook": {
        "fn": heuristics.textbook, "group": "heuristic", "label": "Trusts priors",
        "desc": "One test drop to read the wind, mid-range guesses for the rest, no fitting."},
    "stop_early": {
        "fn": baselines.stop_early, "group": "baseline", "label": "Stop early",
        "desc": "Plays like the reference, then stops after two of the five targets."},
    "calibrate_only": {
        "fn": baselines.calibrate_only, "group": "baseline", "label": "Calibrate, never drop",
        "desc": "Full calibration and fit, then ends the mission without a single real drop."},
    "overhead": {
        "fn": baselines.overhead, "group": "baseline", "label": "Release overhead",
        "desc": "No model: releases right above every target."},
    "random_policy": {
        "fn": baselines.random_policy, "group": "baseline", "label": "Random actions",
        "desc": "Random test drops, then a random release near each target."},
    "do_nothing": {
        "fn": baselines.do_nothing, "group": "baseline", "label": "Do nothing",
        "desc": "Ends the mission immediately."},
}
