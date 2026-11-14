"""Baselines required by the judging protocol, plus two shortcut strategies.

None of them should score: they are here to show that the reward cannot be
earned without doing the task.
"""
from __future__ import annotations

from .reference import Reference


def do_nothing(client):
    """Ends the mission immediately."""
    client.call("declare_done")


def stop_early(client):
    """Plays exactly like the reference, then stops after two of the five targets."""
    Reference(client).run(max_targets=2)


def calibrate_only(client):
    """Does the whole calibration, opens the operation, never drops."""
    Reference(client).run(max_targets=0)


def overhead(client):
    """No model at all: releases right above every target."""
    op = client.call("begin_operation")
    for t in op["targets"]:
        client.call("drop", target=t["id"], x=t["x"], y=t["y"],
                    heading=sum(t["heading_range"]) / 2, altitude=sum(t["altitude_range"]) / 2,
                    speed=sum(t["speed_range"]) / 2)
    client.call("declare_done")


def random_policy(client):
    """Random but valid actions: random test drops, then a random release near each target."""
    import random
    rng = random.Random(12345)
    for _ in range(10):
        client.call("test_drop", heading=rng.uniform(0, 360), altitude=rng.uniform(30, 150),
                    speed=rng.uniform(45, 80), x=rng.uniform(-300, 300), y=rng.uniform(-300, 300))
    op = client.call("begin_operation")
    for t in op["targets"]:
        client.call("drop", target=t["id"], x=t["x"] + rng.uniform(-150, 150), y=t["y"] + rng.uniform(-150, 150),
                    heading=rng.uniform(*t["heading_range"]), altitude=rng.uniform(*t["altitude_range"]),
                    speed=rng.uniform(*t["speed_range"]))
    client.call("declare_done")
