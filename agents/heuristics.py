"""Scripted stand-ins for plausible agent behaviour.

Each one is the reference with ONE decision degraded, everything else equal
(same tools, same budgets, same fitting and aiming code). They are not LLM
runs. They measure how much each decision is worth, which is what lets us
attribute an agent's gap to a specific choice.
"""
from __future__ import annotations

import math

from .reference import Reference


def textbook(client):
    """Trusts priors: one test drop to read the wind, no fitting, mid-range values elsewhere,
    uniform wind, no updraft. Aims with `simulate`."""
    r = Reference(client, clear=[(0, 90, 60)], paired=[], fit_scales=(), fit_updraft=False, polish=False,
                  start={"shear": 0.0, "veer": 0.0, "updraft": 0.0})
    r.run()


def single_condition(client):
    """Repeats one flight condition (heading 90, 90 m, 60 m/s): five drops in clear air, five through
    the smoke. Fits everything it can from them."""
    r = Reference(client, clear=[(90, 90, 60)] * 5, paired=[0, 1, 2, 3, 4])
    r.run()


def uniform_wind(client):
    """Good variety of headings and speeds, smoke drops included, but a single altitude, and the wind
    is assumed to be the same at every height (shear = 0)."""
    r = Reference(client, clear=[(0, 90, 50), (180, 90, 70), (90, 90, 70), (270, 90, 50), (45, 90, 60), (225, 90, 60)],
                  paired=[0, 2, 3, 5], fit_keys=("drag", "wind_speed", "wind_dir"), start={"shear": 0.0, "veer": 0.0})
    r.run()


def ignores_smoke(client):
    """Careful calibration in clear air at three altitudes, but never flies a test through the smoke
    column and leaves the updraft at zero."""
    r = Reference(client, clear=[(0, 90, 60), (180, 90, 60), (90, 40, 50), (270, 40, 70), (90, 140, 70), (270, 140, 50),
                                 (45, 60, 55), (225, 120, 65), (135, 40, 75), (315, 140, 45)],
                  paired=[], fit_updraft=False, start={"updraft": 0.0})
    r.run()


def quick_fit(client):
    """Same experiments as the reference, but stops refining after one coarse pass
    ("the fit looks good enough")."""
    r = Reference(client, fit_scales=(1.0,), polish=False)
    r.updraft_steps = (4.0,)
    r.run()


def ignores_weather(client):
    """Weather variant: plays exactly like the reference, but keeps the calibration wind for the
    operation instead of reading the new one."""
    r = Reference(client)
    r._operate_original = r._operate
    r._operate = lambda travel, max_targets=None, update_wind=True: r._operate_original(travel, max_targets, update_wind=False)
    r.run()
