# Design notes

## 1. What the agent is supposed to learn

One sentence: **design experiments that separate competing explanations, fit a model under a
calculation budget, then commit.** The setting is a firefighting air tanker because the real
procedure has exactly this shape (wind sounding, release-point computation, one pass).

## 2. The world

Flat ground, x east, y north, z up, metres. A drop is `(heading, altitude, speed, x, y)`. The
load leaves with the aircraft's horizontal velocity and is integrated with a fixed 0.02 s
midpoint step (`bomber/physics.py`), so every result is exactly reproducible.

```
acceleration = -g z_hat - drag * |v - v_air| * (v - v_air)          g = 9.81
v_air        = wind(z) + updraft(x, y, z) z_hat
wind speed   = wind_speed * (z / 100)^shear                          toward
wind dir     = wind_dir + veer * (z - 100) / 100
updraft      = updraft * I * (1 - (r/R)^2) * min(1, z/15)            inside r < R = 50 sqrt(I)
```

Six hidden numbers per seed (`bomber/world.py`, ranges in `bomber/config.py`):

| Parameter | Truth range | Hypothesis bounds given to the agent |
|---|---|---|
| drag (1/m) | 0.025 to 0.045 | 0.010 to 0.080 |
| wind_speed at 100 m (m/s) | 5 to 13 | 0 to 20 |
| wind_dir at 100 m (deg) | 0 to 360 | 0 to 360 |
| shear | 0.12 to 0.38 | 0 to 0.6 |
| veer (deg per 100 m) | -35 to 35 | -60 to 60 |
| updraft (m/s at intensity 1) | 3 to 6.5 | 0 to 15 |

The bounds are deliberately wider than, and not centred on, the truth ranges, so "take the
middle of each range" is not a usable prior.

Five targets, 1000 to 1900 m from the calibration fire and at least 350 m apart, intensity 0.5
to 1.4, each with a 20 degree heading window, a 20 m altitude window and a 10 m/s speed window
placed anywhere in the flight envelope. Test drops must be released within 500 m of the
calibration fire, so calibration can never touch a target's smoke column.

Observation noise on test drops: 1.5 m on each impact coordinate, 0.05 s on fall time, 0.5 m/s
and 4 degrees on the wind readout.

## 3. Calibration history: what changed and why

The first version was too forgiving, and the numbers showed it. They are kept here because the
judging criteria ask whether the reward reflects real progress.

| Version | Change | Reference | Degraded strategies | Verdict |
|---|---|---|---|---|
| 1 | Low drag (terminal speed 30 to 40 m/s), radius 20 m, five unknowns | 0.96 | 0.90 to 0.92; no-fit prior 0.51 | Decisions barely matter. A sloppy agent would match the reference. |
| 2 | Higher drag (terminal speed 15 to 20 m/s): falls last 4 to 12 s, wind drift and updraft become first-order | 0.94 | 0.62 to 0.88 | Better, but one flight condition still scores 0.88. |
| 3 | Wind veer added (sixth unknown), wider wind range | 0.86, min 0.41 | 0.47 to 0.78 | Good separation, but the reference itself fails on some seeds. |
| 4 | Updraft range capped so the strongest column stays below 60 % of the load's terminal speed | 0.93 | 0.61 to 0.86 | Chaotic "hovering" regime removed. |
| 5 | Hypothesis bounds widened and off-centre; scoring radius 10 m | 0.87, min 0.62 | 0.13 to 0.60 | Mid-range guessing no longer works. |
| 6 | Reference aiming changed from "shift by the miss" to a secant update | **0.89, min 0.80 on 60 seeds** | 0.13 to 0.68 | Current. |

Versions 1 to 4 were scored with the 20 m radius, versions 5 and 6 with 10 m. Versions 1 to 5
are on 20 or 30 seeds; the degraded-strategy range of version 6 is on the ten default seeds.

Two findings worth stating:

- On its bad seeds in version 5 the reference's hypothesis was nearly exact, and its predicted
  impact was as far off as the real one. The misses of 10 to 30 m came from the aiming loop:
  inside a column the impact moves about twice as far as the release point, so the plain
  "shift by the miss" correction oscillates and never lands on the target. That is a real
  property of the task and a decision an agent has to get right, so it stayed in; only the
  reference's aiming was fixed.
- The updraft cap of version 4 keeps the strongest column at about 60 % of the load's terminal
  speed, so a load is slowed in the core but never close to hovering there.

## 4. The reference (`agents/reference.py`)

1. **Six clear-air drops**: altitudes 40, 90, 140 m; speeds 50, 60, 70 m/s; opposite headings.
   The track passes 400 m beside the calibration fire.
2. **First guess from the instruments**: two straight-line fits of the six wind readouts (log
   speed and direction against altitude) give shear, veer and the wind at 100 m.
3. **Four smoke drops**: four of the clear-air conditions repeated, released so that the load
   lands on the fire (`release = fire - observed travel`). Same condition with and without smoke
   is a paired experiment: the difference is the updraft.
4. **Fit**: three passes over drag, wind speed, wind direction, shear, veer on the clear-air
   drops with shrinking steps; then updraft alone on the smoke drops; then one fine pass over
   all six on all ten. Each step tries a value below and above the current one, jumps to the
   bottom of the parabola through the three errors, and keeps the best point seen. About 70
   `compare` calls.
5. **Aim**: run-in at the centre of each window; correct the release point with a secant
   (Broyden) update of "how far the impact moves when the release moves" until the predicted
   miss is under 0.3 m. Three to six `simulate` calls per target.

About 95 of the 120 calculations are used. Final misses are typically 1 to 2 m, the level of
the observation noise.

## 5. Reading an agent's failure

For any transcript `run_eval.py` reports three numbers (see `bomber/analysis.py`):

| Lost to | Measured as | Typical cause visible in the transcript |
|---|---|---|
| experiments | reference score minus "reference fit and aim on the agent's test drops" | one altitude only; no drop through smoke; no clear-air twin of a smoke drop; test drops wasted on repeats |
| fitting | that, minus "reference aiming with the agent's last hypothesis" | stopping at a mean miss of 5 to 10 m; a parameter never moved from its first value (shear, veer, updraft); changing several parameters at once |
| aiming | that, minus the agent's actual score | oscillating corrections inside a column; dropping without a final `simulate`; run-in at the edge of the window with an unverified release |

The viewer adds, per mission: the six true numbers beside the agent's last hypothesis, the
true and hypothesised wind at 30, 90 and 150 m, and the fit error after every `compare` call.

## 6. Difficulty knobs

All in `bomber/config.py`. In order of how gently they act:

| Knob | Default | Effect |
|---|---|---|
| `score_radius` | 10 m | Smaller: every metre of model error costs more. |
| `n_calculations` | 120 | The reference needs about 95. Lower values force a more economical search. |
| `n_test_drops` | 10 | The reference uses all ten (six in clear air, four through smoke). |
| noise levels | 1.5 m, 0.05 s | Higher: averaging and replication start to matter. |
| `true_veer`, `true_shear`, `true_updraft` | see above | Wider: larger penalty for ignoring the effect. Keep `updraft * 1.4` under 60 % of the lowest terminal speed `sqrt(g / drag)`. |
| window widths | 20 deg, 20 m, 10 m/s | Wider: the agent may choose a run-in it has tested. |

If a frontier model turns out to score close to the reference, tighten `score_radius` and
`n_calculations` first: they do not change what is fair, only how much precision is rewarded.
If it scores near zero, loosen the same two.

## 7. What is not done

- One frontier model has been run (Claude Sonnet 5.5, nine missions on seeds 1 to 3): 0.80
  against 0.93 for the reference on the same seeds, below it in 7 of 9 missions. The sample is
  small and the gap is modest at the default 10 m scoring radius. Re-scoring the same drops with a
  5 m radius gives 0.64 against 0.86, at the price of a lower and less stable reference (0.79 on
  ten seeds, minimum 0.66).
- No small model has been trained. `export_dataset.py` writes reference missions as
  tool-calling transcripts; training and before/after evaluation remain to be done.
- The Harbor packaging has not been run under Docker.
