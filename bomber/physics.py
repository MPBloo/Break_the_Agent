"""Deterministic drop physics.

A released load is a point mass subject to gravity and quadratic drag relative
to the surrounding air. The air moves: a horizontal wind whose speed follows a
power law with altitude and whose direction turns with altitude, plus a
vertical updraft inside the thermal column above every fire. Fixed-step midpoint integration, so the same inputs always
give the same outputs.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict

G = 9.81            # m/s^2
DT = 0.02           # s, integration step
T_MAX = 60.0        # s, safety cap on fall duration
Z_REF = 100.0       # m, reference altitude of the wind power law
Z_FLOOR = 2.0       # m, the power law is frozen below this height
Z_UPDRAFT_FULL = 15.0   # m, updraft grows linearly from 0 at ground to full here
SMOKE_RADIUS_UNIT = 50.0  # m, column radius for a fire of intensity 1


@dataclass(frozen=True)
class Air:
    """The six numbers that define the air (truth or an agent's hypothesis)."""
    drag: float         # 1/m, quadratic drag coefficient of the load
    wind_speed: float   # m/s at Z_REF
    wind_dir: float     # compass degrees the wind blows TOWARD at Z_REF (0 = +y, 90 = +x)
    shear: float        # power-law exponent: speed(z) = wind_speed * (z/Z_REF)**shear
    veer: float         # degrees the wind direction turns clockwise per 100 m of altitude gain
    updraft: float      # m/s, peak updraft on the axis of a fire of intensity 1

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Fire:
    x: float
    y: float
    intensity: float

    @property
    def radius(self) -> float:
        return SMOKE_RADIUS_UNIT * math.sqrt(self.intensity)


def wind_at(air: Air, z: float) -> tuple[float, float]:
    zc = z if z > Z_FLOOR else Z_FLOOR
    s = air.wind_speed * (zc / Z_REF) ** air.shear
    a = math.radians(air.wind_dir + air.veer * (zc - Z_REF) / 100.0)
    return s * math.sin(a), s * math.cos(a)


def _updraft_at(air: Air, fires, x: float, y: float, z: float) -> tuple[float, bool]:
    w = 0.0
    inside = False
    for f in fires:
        dx = x - f.x
        dy = y - f.y
        r2 = dx * dx + dy * dy
        rr = f.radius * f.radius
        if r2 < rr:
            inside = True
            zf = z / Z_UPDRAFT_FULL
            if zf > 1.0:
                zf = 1.0
            elif zf < 0.0:
                zf = 0.0
            w += air.updraft * f.intensity * (1.0 - r2 / rr) * zf
    return w, inside


def _accel(air: Air, fires, p, u):
    wx, wy = wind_at(air, p[2])
    wz, inside = _updraft_at(air, fires, p[0], p[1], p[2])
    rx = u[0] - wx
    ry = u[1] - wy
    rz = u[2] - wz
    s = math.sqrt(rx * rx + ry * ry + rz * rz)
    k = air.drag * s
    return (-k * rx, -k * ry, -G - k * rz), inside


def simulate_drop(air: Air, fires, heading: float, altitude: float, speed: float,
                  x: float, y: float, path_dt: float | None = None) -> dict:
    """Fly one load to the ground.

    heading: compass degrees of the aircraft track (0 = +y north, 90 = +x east).
    Returns impact point, fall time, whether the load entered a smoke column,
    and (if path_dt is given) the sampled path for visualisation.
    """
    a = math.radians(heading)
    p = (x, y, altitude)
    u = (speed * math.sin(a), speed * math.cos(a), 0.0)
    t = 0.0
    smoke = False
    path = [] if path_dt is not None else None
    next_sample = 0.0
    while t < T_MAX:
        if path is not None and t >= next_sample - 1e-9:
            path.append((round(p[0], 2), round(p[1], 2), round(p[2], 2)))
            next_sample += path_dt
        a1, inside = _accel(air, fires, p, u)
        smoke = smoke or inside
        pm = (p[0] + 0.5 * DT * u[0], p[1] + 0.5 * DT * u[1], p[2] + 0.5 * DT * u[2])
        um = (u[0] + 0.5 * DT * a1[0], u[1] + 0.5 * DT * a1[1], u[2] + 0.5 * DT * a1[2])
        a2, _ = _accel(air, fires, pm, um)
        pn = (p[0] + DT * um[0], p[1] + DT * um[1], p[2] + DT * um[2])
        un = (u[0] + DT * a2[0], u[1] + DT * a2[1], u[2] + DT * a2[2])
        if pn[2] <= 0.0:
            f = p[2] / (p[2] - pn[2]) if p[2] != pn[2] else 0.0
            ix = p[0] + f * (pn[0] - p[0])
            iy = p[1] + f * (pn[1] - p[1])
            t += f * DT
            if path is not None:
                path.append((round(ix, 2), round(iy, 2), 0.0))
            return {"x": ix, "y": iy, "t": t, "smoke": smoke, "landed": True, "path": path}
        p, u = pn, un
        t += DT
    return {"x": p[0], "y": p[1], "t": t, "smoke": smoke, "landed": False, "path": path}
