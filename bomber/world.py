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
    calibration_fire: Fire
    targets: tuple


def make_world(seed: int, cfg: Config) -> World:
    rng = random.Random(f"water-bomber-world-{seed}")
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
    return World(seed=seed, air=air, calibration_fire=calibration_fire, targets=tuple(targets))
