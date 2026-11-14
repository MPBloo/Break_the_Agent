"""One mission = one Episode.

The Episode is the only door into the world. Agents (the LLM, the reference
solution, the baselines) interact with it exclusively through `call_tool`,
which is also what the MCP server exposes. The hidden air parameters never
leave this module: no tool result, error message or budget counter depends on
them except through the noisy observations of calibration drops.
"""
from __future__ import annotations

import math
import random

from .config import Config, DEFAULT
from .physics import Air, Fire, simulate_drop, wind_at, G, Z_REF, Z_FLOOR, Z_UPDRAFT_FULL, SMOKE_RADIUS_UNIT
from .world import make_world

PATH_DT = 0.25  # s, sampling of the true paths kept for the viewer (never sent to agents)

_NUM = {"type": "number"}

_HYP_PROPS = {
    "drag": {"type": "number", "description": "Quadratic drag coefficient of the load, 1/m."},
    "wind_speed": {"type": "number", "description": "Wind speed at 100 m altitude, m/s."},
    "wind_dir": {"type": "number", "description": "Compass direction the wind blows TOWARD at 100 m altitude, degrees (0 = north = +y, 90 = east = +x)."},
    "shear": {"type": "number", "description": "Wind power-law exponent: speed(z) = wind_speed * (z/100)^shear."},
    "veer": {"type": "number", "description": "Degrees the wind direction turns clockwise per 100 m of altitude gain: dir(z) = wind_dir + veer * (z - 100)/100."},
    "updraft": {"type": "number", "description": "Peak updraft on the axis of a fire of intensity 1, m/s."},
}
_HYP_KEYS = list(_HYP_PROPS)

_DROP_PROPS = {
    "heading": {"type": "number", "description": "Aircraft track, compass degrees (0 = north = +y, 90 = east = +x)."},
    "altitude": {"type": "number", "description": "Release altitude above ground, m."},
    "speed": {"type": "number", "description": "Aircraft ground speed at release, m/s."},
    "x": {"type": "number", "description": "Release point, east coordinate, m."},
    "y": {"type": "number", "description": "Release point, north coordinate, m."},
}
_DROP_KEYS = list(_DROP_PROPS)


def _schema(props: dict) -> dict:
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


TOOLS = [
    {
        "name": "get_mission",
        "description": "Return the full mission briefing: objective, rules, known physics, unknown parameters, budgets, scoring, and current status. Free.",
        "parameters": _schema({}),
    },
    {
        "name": "test_drop",
        "description": "CALIBRATION PHASE. Release a small water marker and observe where it lands, how long it fell, and the wind measured by the aircraft at its own altitude. Costs one test drop.",
        "parameters": _schema(_DROP_PROPS),
    },
    {
        "name": "compare",
        "description": "Check a hypothesis about the air against all your test drops so far. Returns one row per test drop: predicted minus observed impact (dx, dy in m) and fall time (dt in s). Costs one calculation.",
        "parameters": _schema(_HYP_PROPS),
    },
    {
        "name": "simulate",
        "description": "Predict where a drop would land IF the air followed your hypothesis. It knows nothing about the real air. Costs one calculation.",
        "parameters": _schema({**_HYP_PROPS, **_DROP_PROPS}),
    },
    {
        "name": "begin_operation",
        "description": "End calibration for good and reveal the five wildfire hotspots with their imposed flight constraints. Irreversible: no test drop is possible afterwards.",
        "parameters": _schema({}),
    },
    {
        "name": "drop",
        "description": "FIRE-SUPPRESSION PHASE. Release the water load on a fire hotspot. One drop per hotspot, no feedback on where it lands.",
        "parameters": _schema({"target": {"type": "integer", "description": "Wildfire hotspot id, 1 to 5."}, **_DROP_PROPS}),
    },
    {
        "name": "declare_done",
        "description": "End the mission. Hotspots that received no water drop count as untreated.",
        "parameters": _schema({}),
    },
]
TOOL_NAMES = [t["name"] for t in TOOLS]

INSTRUCTION = (
    "You are the flight-support computer for a Canadair-style aerial firefighting aircraft. Five "
    "wildfire hotspots must each receive one water drop. Where the water load lands depends on the "
    "air it falls through, and the air is not known "
    "in advance: you first calibrate with a limited number of test drops over a calibration fire, then "
    "you commit to one water drop per hotspot without seeing the result. You act only through the provided "
    "tools. Start by calling get_mission to read the full briefing, then carry out the mission and finish "
    "with declare_done."
)


def briefing(cfg: Config) -> str:
    c = cfg
    return f"""CANADAIR FIRE-SUPPRESSION MISSION BRIEFING

OBJECTIVE
Help contain {c.n_targets} wildfire hotspots. Each hotspot receives exactly one water drop. You
never see where a real drop lands, so you must first learn how a water load falls through today's air.

COORDINATES AND UNITS
Flat ground at z = 0. x points east, y points north, in metres. All directions are compass degrees of
motion: 0 = north (+y), 90 = east (+x), 180 = south, 270 = west. The wind direction is the direction the
wind blows TOWARD, in the same convention. Speeds in m/s, times in seconds.

HOW A DROP WORKS
You choose the aircraft heading, altitude ({c.altitude_min:g} to {c.altitude_max:g} m), ground speed ({c.speed_min:g} to {c.speed_max:g} m/s) and the
release point (x, y). The load leaves the aircraft with the aircraft's horizontal velocity and falls.

KNOWN PHYSICS (exactly what `simulate` and `compare` compute)
The load is a point mass. Its acceleration is gravity (g = {G} m/s^2, downward) plus quadratic drag
relative to the surrounding air:  a = -g*z_hat - drag * |v - v_air| * (v - v_air).
The air velocity v_air at a point is the sum of:
  1. A horizontal wind whose speed and direction depend on altitude z:
       speed(z)     = wind_speed * (z/{Z_REF:g})^shear
       direction(z) = wind_dir + veer * (z - {Z_REF:g})/100      (degrees, direction blown toward)
     (z is taken as {Z_FLOOR:g} m below {Z_FLOOR:g} m). wind_speed and wind_dir are the values at {Z_REF:g} m.
  2. Inside the smoke column above each fire (horizontal distance r < R from the fire centre, with
     R = {SMOKE_RADIUS_UNIT:g} * sqrt(intensity) metres), a vertical updraft of
     updraft * intensity * (1 - (r/R)^2) * min(1, z/{Z_UPDRAFT_FULL:g})  m/s.

UNKNOWN TODAY (six numbers, the same over the whole map and for the whole mission)
  drag        in [{c.hyp_drag[0]}, {c.hyp_drag[1]}] 1/m
  wind_speed  in [{c.hyp_wind_speed[0]:g}, {c.hyp_wind_speed[1]:g}] m/s
  wind_dir    in [0, 360) degrees
  shear       in [{c.hyp_shear[0]:g}, {c.hyp_shear[1]:g}]
  veer        in [{c.hyp_veer[0]:g}, {c.hyp_veer[1]:g}] degrees per 100 m
  updraft     in [{c.hyp_updraft[0]:g}, {c.hyp_updraft[1]:g}] m/s
Nothing else is hidden. A hypothesis is a value for each of these six numbers.

PHASE 1: CALIBRATION
A calibration fire of intensity 1 burns at (0, 0); its smoke column has radius {SMOKE_RADIUS_UNIT:g} m. You have
{c.n_test_drops} test drops (`test_drop`). A test drop must be released within {c.calibration_radius:g} m of (0, 0). For each
one you observe: the impact point (noise about {c.noise_impact} m on each axis), the fall time (noise about
{c.noise_time} s), whether the load entered the smoke, and the wind measured by the aircraft AT ITS OWN
ALTITUDE (noise about {c.noise_wind_speed} m/s and {c.noise_wind_dir:g} degrees). You cannot observe the wind at other altitudes.

CALCULATIONS
You have {c.n_calculations} calculations in total for the whole mission, shared between:
  `compare(hypothesis)`: for each test drop so far, predicted minus observed impact and fall time.
  `simulate(hypothesis, drop)`: predicted impact of any drop under your hypothesis.
Neither tool knows the real air. They only evaluate the hypothesis you give them.

PHASE 2: OPERATION
`begin_operation` ends calibration irreversibly and reveals the {c.n_targets} wildfire hotspots. Each hotspot is a fire with
its own position and intensity (between {c.target_intensity[0]} and {c.target_intensity[1]}), hence its own smoke column. For safety each
hotspot imposes a flight heading range, an altitude range and a speed range, which can lie anywhere in
the flight envelope; a drop outside these ranges is refused. The hotspots are far from the calibration
fire. Use `drop` once per hotspot. A real drop returns no information about where it landed.

SCORING
For each hotspot, d is the distance between the true impact point and the fire centre:
  hotspot score = max(0, 1 - d / {c.score_radius:g}).
A hotspot that never receives a drop keeps burning and scores {c.untreated_score}.
Mission score = max(0, mean of the {c.n_targets} hotspot scores). Call `declare_done` when finished.
"""


class Episode:
    def __init__(self, seed: int, cfg: Config = DEFAULT, salt: str = ""):
        self.seed = int(seed)
        self.cfg = cfg
        self._world = make_world(self.seed, cfg, salt)
        self._obs_rng = random.Random(f"water-bomber-obs-{salt}{self.seed}")
        self.phase = "calibration"
        self.tests: list[dict] = []
        self.drops: dict[int, dict] = {}
        self.calcs_used = 0
        self.log: list[dict] = []

    # ------------------------------------------------------------------ helpers
    def _fires(self) -> list[Fire]:
        fires = [self._world.calibration_fire]
        if self.phase != "calibration":
            fires += [t.fire for t in self._world.targets]
        return fires

    def _calcs_left(self) -> int:
        return self.cfg.n_calculations - self.calcs_used

    def _tests_left(self) -> int:
        return self.cfg.n_test_drops - len(self.tests)

    @staticmethod
    def _number(args: dict, key: str, lo: float, hi: float) -> float:
        v = args.get(key)
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError(f"'{key}' must be a number.")
        v = float(v)
        if not math.isfinite(v):
            raise ValueError(f"'{key}' must be a finite number.")
        if v < lo or v > hi:
            raise ValueError(f"'{key}' must be between {lo:g} and {hi:g}.")
        return v

    @staticmethod
    def _check_keys(args: dict, allowed: list[str]) -> None:
        extra = sorted(set(args) - set(allowed))
        if extra:
            raise ValueError(f"Unknown argument(s): {', '.join(map(str, extra))}.")
        missing = [k for k in allowed if k not in args]
        if missing:
            raise ValueError(f"Missing argument(s): {', '.join(missing)}.")

    def _hypothesis(self, args: dict) -> Air:
        c = self.cfg
        return Air(
            drag=self._number(args, "drag", *c.hyp_drag),
            wind_speed=self._number(args, "wind_speed", *c.hyp_wind_speed),
            wind_dir=self._number(args, "wind_dir", 0.0, 360.0) % 360.0,
            shear=self._number(args, "shear", *c.hyp_shear),
            veer=self._number(args, "veer", *c.hyp_veer),
            updraft=self._number(args, "updraft", *c.hyp_updraft),
        )

    def _drop_args(self, args: dict) -> dict:
        c = self.cfg
        return {
            "heading": self._number(args, "heading", 0.0, 360.0),
            "altitude": self._number(args, "altitude", c.altitude_min, c.altitude_max),
            "speed": self._number(args, "speed", c.speed_min, c.speed_max),
            "x": self._number(args, "x", -c.map_half_size, c.map_half_size),
            "y": self._number(args, "y", -c.map_half_size, c.map_half_size),
        }

    def _status(self) -> dict:
        s = {
            "phase": self.phase,
            "test_drops_left": self._tests_left(),
            "calculations_left": self._calcs_left(),
        }
        if self.phase != "calibration":
            s["targets_without_drop"] = [t.id for t in self._world.targets if t.id not in self.drops]
        return s

    # ------------------------------------------------------------------- tools
    def _t_get_mission(self, args: dict) -> dict:
        self._check_keys(args, [])
        out = {
            "briefing": briefing(self.cfg),
            "calibration_fire": {"x": 0.0, "y": 0.0, "intensity": 1.0, "smoke_radius": SMOKE_RADIUS_UNIT},
            "hypothesis_bounds": {"drag": list(self.cfg.hyp_drag), "wind_speed": list(self.cfg.hyp_wind_speed),
                                  "wind_dir": [0.0, 360.0], "shear": list(self.cfg.hyp_shear), "veer": list(self.cfg.hyp_veer),
                                  "updraft": list(self.cfg.hyp_updraft)},
            "status": self._status(),
        }
        if self.phase != "calibration":
            out["targets"] = [t.public() for t in self._world.targets]
        return out

    def _t_test_drop(self, args: dict) -> dict:
        if self.phase != "calibration":
            raise ValueError("Test drops are only possible during the calibration phase.")
        self._check_keys(args, _DROP_KEYS)
        d = self._drop_args(args)
        if math.hypot(d["x"], d["y"]) > self.cfg.calibration_radius:
            raise ValueError(f"A test drop must be released within {self.cfg.calibration_radius:g} m of the calibration fire at (0, 0).")
        if self._tests_left() <= 0:
            raise ValueError("No test drops left.")
        truth = simulate_drop(self._world.air, self._fires(), path_dt=PATH_DT, **d)
        rng, c = self._obs_rng, self.cfg
        wx, wy = wind_at(self._world.air, d["altitude"])
        obs = {
            "x": round(truth["x"] + rng.gauss(0, c.noise_impact), 1),
            "y": round(truth["y"] + rng.gauss(0, c.noise_impact), 1),
            "t": round(truth["t"] + rng.gauss(0, c.noise_time), 2),
            "wind_speed": round(max(0.0, math.hypot(wx, wy) + rng.gauss(0, c.noise_wind_speed)), 1),
            "wind_dir": round((math.degrees(math.atan2(wx, wy)) + rng.gauss(0, c.noise_wind_dir)) % 360.0, 0),
            "smoke": truth["smoke"],
        }
        tid = len(self.tests) + 1
        self.tests.append({"id": tid, **d, "obs": obs,
                           "true": {"x": truth["x"], "y": truth["y"], "t": truth["t"], "path": truth["path"]}})
        return {
            "test": tid,
            "impact": {"x": obs["x"], "y": obs["y"]},
            "fall_time": obs["t"],
            "entered_smoke": obs["smoke"],
            "wind_at_aircraft": {"altitude": d["altitude"], "speed": obs["wind_speed"], "toward_deg": obs["wind_dir"]},
            "test_drops_left": self._tests_left(),
        }

    def _t_compare(self, args: dict) -> dict:
        self._check_keys(args, _HYP_KEYS)
        hyp = self._hypothesis(args)
        if not self.tests:
            raise ValueError("There is no test drop to compare with yet.")
        if self._calcs_left() <= 0:
            raise ValueError("No calculations left.")
        fires = [self._world.calibration_fire]
        rows = []
        for t in self.tests:
            p = simulate_drop(hyp, fires, t["heading"], t["altitude"], t["speed"], t["x"], t["y"])
            if not p["landed"]:
                raise ValueError("Under this hypothesis a load never reaches the ground. Lower updraft or drag.")
            dx, dy = p["x"] - t["obs"]["x"], p["y"] - t["obs"]["y"]
            rows.append([t["id"], round(dx, 1), round(dy, 1), round(p["t"] - t["obs"]["t"], 2)])
        self.calcs_used += 1
        return {
            "columns": ["test", "dx", "dy", "dt"],
            "rows": rows,
            "meaning": "predicted minus observed: dx, dy in metres (impact), dt in seconds (fall time)",
            "mean_miss": round(sum(math.hypot(r[1], r[2]) for r in rows) / len(rows), 2),
            "mean_abs_dt": round(sum(abs(r[3]) for r in rows) / len(rows), 3),
            "calculations_left": self._calcs_left(),
        }

    def _t_simulate(self, args: dict) -> dict:
        self._check_keys(args, _HYP_KEYS + _DROP_KEYS)
        hyp = self._hypothesis(args)
        d = self._drop_args(args)
        if self._calcs_left() <= 0:
            raise ValueError("No calculations left.")
        p = simulate_drop(hyp, self._fires(), **d)
        if not p["landed"]:
            raise ValueError("Under this hypothesis the load never reaches the ground. Lower updraft or drag.")
        self.calcs_used += 1
        return {
            "impact": {"x": round(p["x"], 1), "y": round(p["y"], 1)},
            "fall_time": round(p["t"], 2),
            "enters_smoke": p["smoke"],
            "calculations_left": self._calcs_left(),
        }

    def _t_begin_operation(self, args: dict) -> dict:
        self._check_keys(args, [])
        if self.phase != "calibration":
            raise ValueError("The operation phase has already begun.")
        self.phase = "operation"
        return {
            "status": "Calibration is over. Targets revealed.",
            "targets": [t.public() for t in self._world.targets],
            "calculations_left": self._calcs_left(),
        }

    def _t_drop(self, args: dict) -> dict:
        if self.phase != "operation":
            raise ValueError("Real drops are only possible during the operation phase. Call begin_operation first.")
        self._check_keys(args, ["target"] + _DROP_KEYS)
        tid = args.get("target")
        if isinstance(tid, float) and tid.is_integer():
            tid = int(tid)
        if isinstance(tid, bool) or not isinstance(tid, int) or not 1 <= tid <= len(self._world.targets):
            raise ValueError(f"'target' must be an integer between 1 and {len(self._world.targets)}.")
        d = self._drop_args(args)
        if tid in self.drops:
            raise ValueError(f"Target {tid} has already received its drop.")
        tgt = self._world.targets[tid - 1]
        for key, (lo, hi) in (("heading", tgt.heading), ("altitude", tgt.altitude), ("speed", tgt.speed)):
            if not lo - 1e-9 <= d[key] <= hi + 1e-9:
                raise ValueError(f"Drop refused: {key} must be between {lo:g} and {hi:g} for target {tid}.")
        self.drops[tid] = d
        return {"status": f"Load released on target {tid}.",
                "targets_without_drop": [t.id for t in self._world.targets if t.id not in self.drops]}

    def _t_declare_done(self, args: dict) -> dict:
        self._check_keys(args, [])
        self.phase = "done"
        s = self.score()
        return {"status": "Mission over.", "mission_score": s["score"],
                "targets": [{"id": t["id"], "treated": t["treated"], "score": t["score"]} for t in s["targets"]]}

    # ---------------------------------------------------------------- dispatch
    def call_tool(self, name: str, args: dict | None = None) -> dict:
        """The single entry point. Never raises, never leaks hidden state."""
        args = {} if args is None else args
        phase_before = self.phase
        try:
            if name not in TOOL_NAMES:
                raise ValueError(f"Unknown tool '{name}'. Available: {', '.join(TOOL_NAMES)}.")
            if not isinstance(args, dict):
                raise ValueError("Arguments must be an object.")
            if self.phase == "done":
                raise ValueError("The mission is over.")
            result = getattr(self, f"_t_{name}")(args)
        except ValueError as e:
            result = {"error": str(e)}
        except Exception:
            result = {"error": "Invalid call."}
        self.log.append({"n": len(self.log) + 1, "phase": phase_before, "tool": str(name)[:40],
                         "args": args if isinstance(args, dict) else {"_raw": str(args)[:200]},
                         "result": result if name != "get_mission" else {"briefing": "(omitted)", **{k: v for k, v in result.items() if k != "briefing"}}})
        return result

    # ----------------------------------------------------------------- scoring
    def finalize(self) -> None:
        """Called by the harness when the agent stops, whether or not it declared done."""
        self.phase = "done"

    def score(self) -> dict:
        """Ground-truth reward, computed from the real drops under the real air."""
        c = self.cfg
        fires = [self._world.calibration_fire] + [t.fire for t in self._world.targets]
        rows = []
        for t in self._world.targets:
            d = self.drops.get(t.id)
            if d is None:
                rows.append({"id": t.id, "treated": False, "distance": None, "score": c.untreated_score, "impact": None, "path": None})
                continue
            p = simulate_drop(self._world.air, fires, path_dt=PATH_DT, **d)
            dist = math.hypot(p["x"] - t.fire.x, p["y"] - t.fire.y)
            rows.append({"id": t.id, "treated": True, "distance": round(dist, 2),
                         "score": round(max(0.0, 1.0 - dist / c.score_radius), 4),
                         "impact": {"x": round(p["x"], 2), "y": round(p["y"], 2)}, "path": p["path"]})
        total = max(0.0, sum(r["score"] for r in rows) / len(rows))
        return {"score": round(total, 4), "targets": rows}

    def result(self) -> dict:
        """Full record for the harness and the viewer. Contains the hidden truth:
        it must never be routed back to an agent."""
        s = self.score()
        return {
            "seed": self.seed,
            "score": s["score"],
            "targets_scored": [{k: v for k, v in r.items() if k != "path"} for r in s["targets"]],
            "counts": {"test_drops": len(self.tests), "calculations": self.calcs_used,
                       "real_drops": len(self.drops), "tool_calls": len(self.log),
                       "declared_done": any(e["tool"] == "declare_done" and "error" not in e["result"] for e in self.log)},
            "log": self.log,
            "debrief": {
                "air": self._world.air.as_dict(),
                "targets": [t.public() for t in self._world.targets],
                "tests": [{"id": t["id"], **{k: t[k] for k in _DROP_KEYS},
                           "obs": t["obs"], "true": {"x": round(t["true"]["x"], 2), "y": round(t["true"]["y"], 2),
                                                     "t": round(t["true"]["t"], 3)}, "path": t["true"]["path"]}
                          for t in self.tests],
                "drops": [{"target": tid, **d, "path": next(r["path"] for r in s["targets"] if r["id"] == tid)}
                          for tid, d in sorted(self.drops.items())],
            },
        }
