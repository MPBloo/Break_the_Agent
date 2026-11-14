"""Reference solution.

It plays through the same tools, budgets and briefing as any agent. It never
imports the physics or the world: everything it knows comes from tool results.
Its edge is method, not information:

  1. Experiments chosen to separate the unknowns: three altitudes, two speeds,
     opposite headings, first in clear air, then the same conditions repeated
     through the smoke column (paired experiment).
  2. One-parameter-at-a-time refinement with `compare`: try a bit less, a bit
     more, keep the best. Only arithmetic an agent could do by hand.
  3. Aim each target with `simulate`, correcting the release point from the
     predicted miss until the prediction is on the target.

Deterministic: same seed, same calls, same score.
"""
from __future__ import annotations

import math

W_T = 20.0          # metres per second: weight of a fall-time residual against an impact residual
AIM_RESERVE = 30    # calculations kept for aiming the five targets

# (heading, altitude, speed) of the six clear-air test drops
CLEAR = [(0, 90, 60), (180, 90, 60), (90, 40, 50), (270, 40, 70), (90, 140, 70), (270, 140, 50)]
# indices into CLEAR whose conditions are repeated through the smoke column
PAIRED = [0, 2, 4, 5]

class OutOfBudget(Exception):
    pass


class Reference:
    """`clear`, `paired`, `fit_scales`, `fit_keys` and `polish` exist so that the ablated
    variants in agents/heuristics.py can switch off one decision at a time."""

    def __init__(self, client, clear=CLEAR, paired=PAIRED, fit_scales=(1.0, 0.4, 0.15),
                 fit_keys=("drag", "wind_speed", "wind_dir", "shear", "veer"), fit_updraft=True, polish=True,
                 start=None):
        self.c = client
        self.clear_plan = clear
        self.paired = paired
        self.fit_scales = fit_scales
        self.fit_keys = fit_keys
        self.fit_updraft = fit_updraft
        self.polish = polish
        self.updraft_steps = (4.0, 1.5, 0.5)
        self.calcs_left = None
        self.bounds = {}
        self.hyp = {}
        self.start = start or {}
        self.locked = set(start or {})

    # ----------------------------------------------------------- experiments
    def _test(self, heading, altitude, speed, x, y):
        r = self.c.call("test_drop", heading=heading, altitude=altitude, speed=speed, x=round(x, 1), y=round(y, 1))
        return r

    def clear_air_tests(self):
        """Six drops well away from the smoke: the track passes 400 m to the side of the fire."""
        out = []
        for heading, altitude, speed in self.clear_plan:
            a = math.radians(heading)
            fwd = (math.sin(a), math.cos(a))
            left = (-fwd[1], fwd[0])
            x = 400 * left[0] - 120 * fwd[0]
            y = 400 * left[1] - 120 * fwd[1]
            r = self._test(heading, altitude, speed, x, y)
            out.append({"id": r["test"], "heading": heading, "altitude": altitude, "speed": speed,
                        "dx": r["impact"]["x"] - round(x, 1), "dy": r["impact"]["y"] - round(y, 1),
                        "wind": r["wind_at_aircraft"]})
        return out

    def smoke_tests(self, clear):
        """Repeat four conditions so the load now lands on the fire: release = fire - observed travel."""
        ids = []
        for i in self.paired:
            t = clear[i]
            r = self._test(t["heading"], t["altitude"], t["speed"], -t["dx"], -t["dy"])
            ids.append(r["test"])
        return ids

    def wind_from_instruments(self, clear):
        """First guess of the wind profile from the aircraft readings at three altitudes
        (two straight-line fits: log speed and direction against altitude)."""
        xs = [math.log(t["wind"]["altitude"] / 100.0) for t in clear]
        ys = [math.log(max(t["wind"]["speed"], 0.1)) for t in clear]
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        spread = sum((a - mx) ** 2 for a in xs)
        if spread < 1e-9 or "shear" in self.locked:   # a single altitude says nothing about shear
            slope = self.hyp["shear"]
        else:
            slope = sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / spread
        s = sum(math.sin(math.radians(t["wind"]["toward_deg"])) for t in clear)
        c = sum(math.cos(math.radians(t["wind"]["toward_deg"])) for t in clear)
        mean_dir = math.degrees(math.atan2(s, c))
        # direction against altitude: slope = veer, value at 100 m = wind_dir
        zs = [(t["wind"]["altitude"] - 100.0) / 100.0 for t in clear]
        ds = [(t["wind"]["toward_deg"] - mean_dir + 180.0) % 360.0 - 180.0 for t in clear]
        mz, md = sum(zs) / n, sum(ds) / n
        zspread = sum((z - mz) ** 2 for z in zs)
        if zspread < 1e-9 or "veer" in self.locked:
            veer = self.hyp["veer"]
        else:
            veer = sum((z - mz) * (d - md) for z, d in zip(zs, ds)) / zspread
        lo, hi = self.bounds["veer"]
        self.hyp["veer"] = min(hi, max(lo, veer))
        lo, hi = self.bounds["shear"]
        self.hyp["shear"] = min(hi, max(lo, slope))
        self.hyp["wind_speed"] = min(self.bounds["wind_speed"][1], math.exp(my - slope * mx))
        self.hyp["wind_dir"] = (mean_dir + md - self.hyp["veer"] * mz) % 360.0

    # ------------------------------------------------------------------ fit
    def cost(self, hyp, ids):
        if self.calcs_left is not None and self.calcs_left <= AIM_RESERVE:
            raise OutOfBudget
        args = {k: round(v, 6) for k, v in hyp.items()}
        args["wind_dir"] = args["wind_dir"] % 360.0
        r = self.c.call("compare", **args)
        if "error" in r:
            if "calculations" in r["error"]:
                raise OutOfBudget
            return float("inf")
        self.calcs_left = r["calculations_left"]
        rows = [x for x in r["rows"] if x[0] in ids]     # each row: [test, dx, dy, dt]
        return sum(x[1] ** 2 + x[2] ** 2 + (W_T * x[3]) ** 2 for x in rows) / len(rows)

    def refine(self, key, step, ids, j0):
        """Try key-step and key+step, jump to the bottom of the parabola, keep the best point seen."""
        lo, hi = self.bounds[key]
        x0 = self.hyp[key]

        def clamp(v):
            return v if lo is None else min(hi, max(lo, v))

        pts = [(x0, j0)]
        for v in (clamp(x0 - step), clamp(x0 + step)):
            if abs(v - x0) > 1e-12:
                pts.append((v, self.cost({**self.hyp, key: v}, ids)))
        if len(pts) == 3 and all(math.isfinite(p[1]) for p in pts):
            (xa, ja), (xb, jb) = pts[1], pts[2]
            den = (xa - x0) * (xb - x0) * (xa - xb)
            curv = ((xb - x0) * (ja - j0) - (xa - x0) * (jb - j0)) / den if den else 0.0
            if curv > 0:
                slope = ((xa - x0) ** 2 * (jb - j0) - (xb - x0) ** 2 * (ja - j0)) / den
                v = clamp(min(x0 + 2 * step, max(x0 - 2 * step, x0 - slope / (2 * curv))))
                if all(abs(v - p[0]) > 1e-9 for p in pts):
                    pts.append((v, self.cost({**self.hyp, key: v}, ids)))
        best = min(pts, key=lambda p: p[1])
        self.hyp[key] = best[0]
        return best[1]

    def sweep(self, keys_steps, ids, j0=None):
        if j0 is None:
            j0 = self.cost(self.hyp, ids)
        for key, step in keys_steps:
            j0 = self.refine(key, step, ids, j0)
        return j0

    def fit(self, clear_ids, smoke_ids):
        steps = {"drag": 0.012, "wind_speed": 1.2, "wind_dir": 8.0, "shear": 0.08, "veer": 10.0}
        fine = {"drag": 0.001, "updraft": 0.3, "wind_speed": 0.2, "wind_dir": 1.5, "shear": 0.02, "veer": 2.0}
        try:
            j = None
            for scale in self.fit_scales:
                j = self.sweep([(k, steps[k] * scale) for k in self.fit_keys], clear_ids, j)
            if self.fit_updraft and smoke_ids:
                j = None
                for step in self.updraft_steps:
                    j = self.sweep([("updraft", step)], smoke_ids, j)
            if self.polish:
                keys = [k for k in fine if k in self.fit_keys or (k == "updraft" and self.fit_updraft and smoke_ids)]
                self.sweep([(k, fine[k]) for k in keys], clear_ids + smoke_ids)
        except OutOfBudget:
            pass

    # ------------------------------------------------------------------ aim
    def aim(self, target, travel_guess):
        """Find the release point whose predicted impact is the fire centre, then drop.

        Each `simulate` gives a predicted miss. Shifting the release point by the opposite of the
        miss is exact in clear air, but inside a smoke column a 1 m shift of the release can move
        the impact by 2 m, and the naive correction then overshoots forever. So we keep a running
        2x2 estimate J of "how far the impact moves when the release moves" (secant update from the
        last two simulations) and correct by J^-1 * miss.
        """
        heading = sum(target["heading_range"]) / 2
        altitude = sum(target["altitude_range"]) / 2
        speed = sum(target["speed_range"]) / 2
        a = math.radians(heading)
        x = round(target["x"] - travel_guess * math.sin(a), 1)
        y = round(target["y"] - travel_guess * math.cos(a), 1)
        hyp = {k: round(v, 6) for k, v in self.hyp.items()}
        hyp["wind_dir"] %= 360.0
        j = [[1.0, 0.0], [0.0, 1.0]]
        best, prev = None, None
        for _ in range(6):
            r = self.c.call("simulate", **hyp, heading=heading, altitude=altitude, speed=speed, x=x, y=y)
            if "error" in r:
                break
            fx, fy = r["impact"]["x"] - target["x"], r["impact"]["y"] - target["y"]
            miss = math.hypot(fx, fy)
            if best is None or miss < best[0]:
                best = (miss, x, y)
            if miss < 0.3:
                break
            if prev is not None:
                sx, sy = x - prev[0], y - prev[1]
                yx, yy = fx - prev[2], fy - prev[3]
                ss = sx * sx + sy * sy
                if ss > 1e-9:
                    ux = (yx - (j[0][0] * sx + j[0][1] * sy)) / ss
                    uy = (yy - (j[1][0] * sx + j[1][1] * sy)) / ss
                    j = [[j[0][0] + ux * sx, j[0][1] + ux * sy], [j[1][0] + uy * sx, j[1][1] + uy * sy]]
            prev = (x, y, fx, fy)
            det = j[0][0] * j[1][1] - j[0][1] * j[1][0]
            if abs(det) < 0.05:
                j, det = [[1.0, 0.0], [0.0, 1.0]], 1.0
            dx = -(j[1][1] * fx - j[0][1] * fy) / det
            dy = -(-j[1][0] * fx + j[0][0] * fy) / det
            norm = math.hypot(dx, dy)
            if norm > 150.0:
                dx, dy = dx * 150.0 / norm, dy * 150.0 / norm
            x, y = round(x + dx, 1), round(y + dy, 1)
        if best is not None:
            x, y = best[1], best[2]
        self.c.call("drop", target=target["id"], heading=heading, altitude=altitude, speed=speed, x=x, y=y)

    # ------------------------------------------------------------------ run
    def _read_mission(self):
        mission = self.c.call("get_mission")
        self.bounds = {k: tuple(v) for k, v in mission["hypothesis_bounds"].items()}
        self.bounds["wind_dir"] = (None, None)   # an angle wraps around, no clamping
        self.hyp = {k: (lo + hi) / 2 for k, (lo, hi) in mission["hypothesis_bounds"].items()}
        self.hyp.update(self.start)

    def _operate(self, travel, max_targets=None):
        op = self.c.call("begin_operation")
        for target in op["targets"][:max_targets]:
            self.aim(target, travel)
        self.c.call("declare_done")

    def run(self, max_targets=None):
        self._read_mission()
        clear = self.clear_air_tests()
        self.wind_from_instruments(clear)
        smoke_ids = self.smoke_tests(clear)
        self.fit([t["id"] for t in clear], smoke_ids)
        self._operate(sum(math.hypot(t["dx"], t["dy"]) for t in clear) / len(clear), max_targets)

    # ----------------------------------------------- used by the attribution analysis
    def run_on_given_tests(self, test_args):
        """Fit and aim exactly like the reference, but on test drops chosen by someone else."""
        self._read_mission()
        tests = []
        for a in test_args:
            r = self.c.call("test_drop", **a)
            if "error" not in r:
                tests.append({"id": r["test"], "wind": r["wind_at_aircraft"], "smoke": r["entered_smoke"]})
        clear_ids = [t["id"] for t in tests if not t["smoke"]]
        smoke_ids = [t["id"] for t in tests if t["smoke"]]
        if tests:
            self.wind_from_instruments(tests)
            if not clear_ids:           # everything went through smoke: fit all parameters on that
                clear_ids = smoke_ids
            self.fit(clear_ids, smoke_ids)
        self._operate(80.0)

    def run_with_hypothesis(self, hyp):
        """Aim exactly like the reference, but with a hypothesis built by someone else."""
        self._read_mission()
        self.hyp.update(hyp)
        self._operate(80.0)


def run(client):
    Reference(client).run()
