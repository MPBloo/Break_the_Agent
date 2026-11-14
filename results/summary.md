# Canadair Firefighting: evaluation summary

Seeds 1..10. Scores are mission scores in [0, 1]. Scripted agents are deterministic.

| Agent | Kind | Episodes | Mean | Std | Min | Max | Lost: experiments | Lost: fitting | Lost: aiming |
|---|---|---|---|---|---|---|---|---|---|
| Reference solution | reference | 10 | 0.859 | 0.058 | 0.724 | 0.937 |  |  |  |
| Claude Opus 5.5 | frontier | 9 | 0.853 | 0.062 | 0.745 | 0.942 | 0.02 | 0.01 | 0.01 |
| Claude Sonnet 5.5 | frontier | 9 | 0.730 | 0.075 | 0.616 | 0.842 | 0.04 | 0.16 | -0.03 |
| Claude Sonnet 4.5 | frontier | 9 | 0.315 | 0.194 | 0.000 | 0.604 | 0.11 | 0.38 | 0.09 |
| Claude Haiku 5.5 | frontier | 9 | 0.000 | 0.000 | 0.000 | 0.000 |  |  |  |
| Stops fitting early | heuristic | 10 | 0.599 | 0.308 | 0.000 | 0.887 | 0.01 | 0.25 | -0.00 |
| One flight condition | heuristic | 10 | 0.745 | 0.087 | 0.631 | 0.899 | 0.09 | 0.02 | 0.00 |
| Assumes uniform wind | heuristic | 10 | 0.385 | 0.147 | 0.128 | 0.604 | 0.08 | 0.39 | 0.00 |
| Ignores the smoke column | heuristic | 10 | 0.192 | 0.111 | 0.000 | 0.396 | 0.58 | 0.08 | 0.00 |
| Trusts priors | heuristic | 10 | 0.039 | 0.068 | 0.000 | 0.215 | 0.63 | 0.19 | 0.00 |
| Stop early | baseline | 10 | 0.042 | 0.022 | 0.000 | 0.076 |  |  |  |
| Calibrate, never drop | baseline | 10 | 0.000 | 0.000 | 0.000 | 0.000 |  |  |  |
| Release overhead | baseline | 10 | 0.000 | 0.000 | 0.000 | 0.000 |  |  |  |
| Random actions | baseline | 10 | 0.000 | 0.000 | 0.000 | 0.000 |  |  |  |
| Do nothing | baseline | 10 | 0.000 | 0.000 | 0.000 | 0.000 |  |  |  |
| claude-haiku-5-5 | legacy | 9 | 0.270 | 0.389 | 0.000 | 0.942 | 0.03 | 0.17 | -0.12 |
| claude-opus-5-5-weather-2026-11-15 | legacy | 9 | 0.839 | 0.064 | 0.750 | 0.974 | -0.03 | 0.05 | -0.02 |
| claude-sonnet-5-5 | legacy | 9 | 0.708 | 0.072 | 0.618 | 0.859 | 0.03 | 0.24 | -0.08 |
| haiku-high-nouvel-essai | legacy | 9 | 0.000 | 0.000 | 0.000 | 0.000 |  |  |  |

"Lost" columns: mean points lost against the reference on the same seeds, split by cause (see bomber/analysis.py).

Claude Haiku 5.5: all 9 missions were cut short by the model provider's safety filter.

claude-haiku-5-5: 6 of 9 missions were cut short by the model provider's safety filter before any real drop and score 0. Mean over the 3 completed missions: 0.810.

haiku-high-nouvel-essai: all 9 missions were cut short by the model provider's safety filter.
