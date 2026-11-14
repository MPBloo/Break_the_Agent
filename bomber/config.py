"""Every tunable number of the environment lives here.

The defaults are the published benchmark setting. Difficulty knobs (budgets,
noise, scoring radius) can be changed to re-calibrate the environment, but any
reported result must state the configuration it was produced with.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Config:
    # Budgets
    n_test_drops: int = 10        # calibration drops, with feedback
    n_calculations: int = 120     # shared budget of `simulate` + `compare` calls
    n_targets: int = 5            # real drops, one per target, no feedback

    # Scoring
    score_radius: float = 6.0     # m; a hit at distance d scores max(0, 1 - d/score_radius)
    untreated_score: float = -0.5  # a target that never receives a drop

    # Observation noise on calibration drops (1 sigma)
    noise_impact: float = 1.5     # m, on each of x and y
    noise_time: float = 0.05      # s
    noise_wind_speed: float = 0.5  # m/s
    noise_wind_dir: float = 4.0   # degrees

    # Flight envelope
    altitude_min: float = 30.0
    altitude_max: float = 150.0
    speed_min: float = 45.0
    speed_max: float = 80.0
    map_half_size: float = 2500.0   # release points must satisfy |x|,|y| <= this
    calibration_radius: float = 500.0  # test drops are released within this distance of the calibration fire

    # Hidden-parameter ranges the world is drawn from
    true_drag: tuple = (0.025, 0.045)
    true_wind_speed: tuple = (5.0, 13.0)
    true_shear: tuple = (0.12, 0.38)
    true_veer: tuple = (-35.0, 35.0)
    true_updraft: tuple = (3.0, 6.5)

    # Bounds accepted for an agent's hypothesis (wider than the truth ranges)
    hyp_drag: tuple = (0.010, 0.080)
    hyp_wind_speed: tuple = (0.0, 20.0)
    hyp_shear: tuple = (0.0, 0.6)
    hyp_veer: tuple = (-60.0, 60.0)
    hyp_updraft: tuple = (0.0, 15.0)

    # Target generation
    target_dist: tuple = (1000.0, 1900.0)   # from the calibration fire
    target_separation: float = 350.0
    target_intensity: tuple = (0.5, 1.4)
    window_heading: float = 20.0    # width of the imposed run-in heading window (deg)
    window_altitude: float = 20.0   # width of the imposed altitude window (m)
    window_speed: float = 10.0      # width of the imposed speed window (m/s)

    # Variant "weather": the wind at the hotspots differs from the calibration wind (a front moved
    # through). Drag, shear, veer and updraft are unchanged. The agent can read the wind at a chosen
    # altitude a limited number of times during the operation.
    name: str = "base"
    weather_change: bool = False
    weather_dir_shift: tuple = (15.0, 35.0)     # degrees, sign drawn at random
    weather_speed_factor: tuple = (0.7, 1.35)
    n_wind_readings: int = 20

    def as_dict(self) -> dict:
        return asdict(self)


DEFAULT = Config()
WEATHER = Config(name="weather", weather_change=True)
VARIANTS = {"base": DEFAULT, "weather": WEATHER}


def variant(name: str | None) -> Config:
    """The configuration of a named variant ("base" when the name is empty)."""
    return VARIANTS[name or "base"]
