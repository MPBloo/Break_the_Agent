"""The reference for agents that have a shell: same experiments, but the model is fitted and the drops are
aimed with a local simulator written from the briefing.

The briefing gives the full physics, so an agent with a shell (OpenCode in Harbor) can re-implement it
and fit the six unknowns without the 120-calculation budget of `compare` and `simulate`. This reference
does exactly that, with the same ten test drops as `reference.py`:

- a simulator written from the briefing's equations alone (it does not import the environment's code);
- a weighted least-squares fit on every measurement: impacts (noise 1.5 m), fall times (0.05 s) and the
  aircraft's wind readings (0.5 m/s), from several starting points;
- each drop aimed by solving for the release point with the local simulator, including the target fire's
  own smoke column.

It still acts only through the MCP tools. It needs numpy and scipy (installed in the Harbor agent image).
"""
from __future__ import annotations

import math

import numpy as np
from scipy.optimize import least_squares

from .reference import Reference

G = 9.81
NAMES = ["drag", "wind_speed", "wind_dir", "shear", "veer", "updraft"]
LOWER = [0.01, 0.0, -720.0, 0.0, -60.0, 0.0]
UPPER = [0.08, 20.0, 720.0, 0.6, 60.0, 15.0]


# ------------------------------------------------------------------ physics, as stated in the briefing
def wind(p, z):
    zc = max(z, 2.0)
    s = p[1] * (zc / 100.0) ** p[3]
    a = math.radians(p[2] + p[4] * (zc - 100.0) / 100.0)
    return s * math.sin(a), s * math.cos(a)


def fly(p, fires, heading, altitude, speed, x, y, dt=0.02):
    """Impact (x, y) and fall time of one load: point mass, quadratic drag relative to the air."""
    drag, up = p[0], p[5]

    def acc(px, py, pz, vx, vy, vz):
        wx, wy = wind(p, pz)
        wz = 0.0
        for fx, fy, inten in fires:
            R = 50.0 * math.sqrt(inten)
            r2 = (px - fx) ** 2 + (py - fy) ** 2
            if r2 < R * R:
                wz += up * inten * (1.0 - r2 / (R * R)) * min(1.0, max(pz, 0.0) / 15.0)
        rx, ry, rz = vx - wx, vy - wy, vz - wz
        k = drag * math.sqrt(rx * rx + ry * ry + rz * rz)
        return -k * rx, -k * ry, -G - k * rz

    a = math.radians(heading)
    s = [x, y, altitude, speed * math.sin(a), speed * math.cos(a), 0.0]
    t = 0.0
    while t < 60.0:
        def d(st):
            ax, ay, az = acc(*st)
            return [st[3], st[4], st[5], ax, ay, az]
        k1 = d(s)
        k2 = d([s[i] + 0.5 * dt * k1[i] for i in range(6)])
        k3 = d([s[i] + 0.5 * dt * k2[i] for i in range(6)])
        k4 = d([s[i] + dt * k3[i] for i in range(6)])
        n = [s[i] + dt / 6.0 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]) for i in range(6)]
        if n[2] <= 0.0:
            f = s[2] / (s[2] - n[2])
            return s[0] + f * (n[0] - s[0]), s[1] + f * (n[1] - s[1]), t + f * dt
        s, t = n, t + dt
    return s[0], s[1], t


class ReferenceLocal(Reference):
    def __init__(self, client):
        super().__init__(client)
        self.obs = []          # (heading, altitude, speed, x, y, impact x, impact y, fall time)
        self.cal_fire = [(0.0, 0.0, 1.0)]

    def _test(self, heading, altitude, speed, x, y):
        r = super()._test(heading, altitude, speed, x, y)
        if "error" not in r:
            self.obs.append((heading, altitude, speed, round(x, 1), round(y, 1),
                             r["impact"]["x"], r["impact"]["y"], r["fall_time"]))
        return r

    # ------------------------------------------------------------------ fit on every measurement
    def _local_residuals(self, q):
        out = []
        for hd, alt, spd, x, y, ix, iy, t in self.obs:
            px, py, pt = fly(q, self.cal_fire, hd, alt, spd, x, y)
            out += [(px - ix) / 1.5, (py - iy) / 1.5, (pt - t) / 0.05]
        for z, wx, wy in self.readings:
            mx, my = wind(q, z)
            out += [(mx - wx) / 0.5, (my - wy) / 0.5]
        return np.array(out)

    def fit(self, clear_ids, smoke_ids):
        super().fit(clear_ids, smoke_ids)          # the budgeted fit gives a good starting point
        h = self.hyp
        start = np.array([h[k] for k in NAMES], dtype=float)
        best = None
        for jitter in (0.0, 0.15, -0.15):
            x0 = start * (1.0 + jitter * np.array([1, 0.2, 0, 1, 0, 1]))
            x0[3] = min(max(x0[3], 0.01), 0.59)
            x0 = np.clip(x0, np.array(LOWER) + 1e-6, np.array(UPPER) - 1e-6)
            r = least_squares(self._local_residuals, x0, bounds=(LOWER, UPPER),
                              x_scale=[0.005, 1.0, 5.0, 0.05, 5.0, 1.0], diff_step=1e-4, max_nfev=60)
            if best is None or r.cost < best.cost:
                best = r
        self.hyp = {k: float(v) for k, v in zip(NAMES, best.x)}
        self.hyp["wind_dir"] %= 360.0

    # ------------------------------------------------------------------ aim with the local simulator
    def aim(self, target, travel_guess):
        heading = sum(target["heading_range"]) / 2
        altitude = sum(target["altitude_range"]) / 2
        speed = sum(target["speed_range"]) / 2
        q = [self.hyp[k] for k in NAMES]
        fires = [(target["x"], target["y"], target["intensity"])]
        a = math.radians(heading)
        x, y = target["x"] - travel_guess * math.sin(a), target["y"] - travel_guess * math.cos(a)
        j = np.eye(2)
        prev = None
        for _ in range(25):
            ix, iy, _t = fly(q, fires, heading, altitude, speed, x, y)
            f = np.array([ix - target["x"], iy - target["y"]])
            if np.hypot(*f) < 0.02:
                break
            if prev is not None:                                   # secant update of d(impact)/d(release)
                s = np.array([x - prev[0], y - prev[1]])
                if s @ s > 1e-12:
                    j = j + np.outer(f - prev[2] - j @ s, s) / (s @ s)
            prev = (x, y, f)
            try:
                step = -np.linalg.solve(j, f)
            except np.linalg.LinAlgError:
                j, step = np.eye(2), -f
            n = np.hypot(*step)
            if n > 150.0:
                step *= 150.0 / n
            x, y = x + step[0], y + step[1]
        self.c.call("drop", target=target["id"], heading=heading, altitude=altitude, speed=speed,
                    x=round(x, 1), y=round(y, 1))


def run(client):
    ReferenceLocal(client).run()
