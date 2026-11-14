"""Seeded world generation. Everything here stays on the server side."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

from .config import Config
from .physics import Air, Fire


@dataclass(frozen=True)
class Target:
    id: int
    fire: Fire
    heading: tuple   # allowed run-in heading window (lo, hi), compass degrees, lo < hi
    altitude: tuple  # allowed altitude window (lo, hi), m
    speed: tuple     # allowed speed window (lo, hi), m/s

    def public(self) -> dict:
        return {
            "id": self.id,
            "x": self.fire.x,
            "y": self.fire.y,
            "intensity": self.fire.intensity,
            "smoke_radius": round(self.fire.radius, 1),
            "heading_range": list(self.heading),
            "altitude_range": list(self.altitude),
            "speed_range": list(self.speed),
        }


@dataclass(frozen=True)
class World:
    seed: int
    air: Air
    air_op: Air     # the air during the operation (same as `air` unless the weather changes)
    calibration_fire: Fire
    targets: tuple


def make_world(seed: int, cfg: Config, salt: str = "") -> World:
    """`salt` is a server-side secret. With an empty salt the world depends on the seed alone, which
    keeps published results reproducible from the public code. A deployment where the agent has a
    shell and can read this repository must set a secret salt (BOMBER_SALT), otherwise the seed can
    be recovered from the revealed hotspots and the hidden air rebuilt exactly."""
    rng = random.Random(f"water-bomber-world-{salt}{seed}")
    u = rng.uniform
    air = Air(
        drag=round(u(*cfg.true_drag), 5),
        wind_speed=round(u(*cfg.true_wind_speed), 2),
        wind_dir=round(u(0.0, 360.0), 1),
        shear=round(u(*cfg.true_shear), 3),
        veer=round(u(*cfg.true_veer), 1),
        updraft=round(u(*cfg.true_updraft), 2),
    )
    calibration_fire = Fire(0.0, 0.0, 1.0)

    targets = []
    placed: list[tuple[float, float]] = []
    while len(targets) < cfg.n_targets:
        d = u(*cfg.target_dist)
        a = u(0.0, 2 * math.pi)
        x, y = round(d * math.sin(a)), round(d * math.cos(a))
        if any(math.hypot(x - px, y - py) < cfg.target_separation for px, py in placed):
            continue
        placed.append((x, y))
        h_lo = round(u(0.0, 360.0 - cfg.window_heading))
        a_lo = round(u(cfg.altitude_min, cfg.altitude_max - cfg.window_altitude))
        s_lo = round(u(cfg.speed_min, cfg.speed_max - cfg.window_speed))
        targets.append(Target(
            id=len(targets) + 1,
            fire=Fire(float(x), float(y), round(u(*cfg.target_intensity), 2)),
            heading=(float(h_lo), float(h_lo + cfg.window_heading)),
            altitude=(float(a_lo), float(a_lo + cfg.window_altitude)),
            speed=(float(s_lo), float(s_lo + cfg.window_speed)),
        ))
    air_op = air
    if cfg.weather_change:   # drawn after everything else, so the calibration world is the same as in "base"
        shift = u(*cfg.weather_dir_shift) * (1 if u(0.0, 1.0) < 0.5 else -1)
        air_op = Air(drag=air.drag, wind_speed=round(air.wind_speed * u(*cfg.weather_speed_factor), 2),
                     wind_dir=round((air.wind_dir + shift) % 360.0, 1), shear=air.shear, veer=air.veer,
                     updraft=air.updraft)
    return World(seed=seed, air=air, air_op=air_op, calibration_fire=calibration_fire, targets=tuple(targets))
