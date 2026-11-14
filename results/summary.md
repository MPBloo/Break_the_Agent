# Canadair Firefighting: evaluation summary

Seeds 1..10. Scores are mission scores in [0, 1]. Scripted agents are deterministic.

| Agent | Kind | Episodes | Mean | Std | Min | Max | Lost: experiments | Lost: fitting | Lost: aiming |
|---|---|---|---|---|---|---|---|---|---|
| Reference solution | reference | 10 | 0.824 | 0.056 | 0.714 | 0.915 |  |  |  |
| haiku-high-nouvel-essai | frontier | 9 | 0.000 | 0.000 | 0.000 | 0.000 | 0.67 | 0.18 | 0.03 |
| claude-sonnet-5-5 | frontier | 9 | 0.708 | 0.072 | 0.618 | 0.859 | 0.09 | 0.16 | -0.08 |
| claude-sonnet-5-5-canadair-2026-11-14 | frontier | 9 | 0.730 | 0.075 | 0.616 | 0.842 | 0.04 | 0.14 | -0.03 |
| claude-sonnet-4-5-20250929-canadair-2026-11-14 | frontier | 9 | 0.315 | 0.194 | 0.000 | 0.604 | 0.10 | 0.38 | 0.09 |
| claude-haiku-5-5 | frontier | 9 | 0.270 | 0.389 | 0.000 | 0.942 | 0.17 | 0.17 | 0.27 |
| claude-haiku-5-5-canadair-2026-11-14 | frontier | 9 | 0.000 | 0.000 | 0.000 | 0.000 | 0.65 | 0.19 | 0.04 |
| Stops fitting early | heuristic | 10 | 0.599 | 0.308 | 0.000 | 0.887 | -0.01 | 0.24 | -0.00 |
| One flight condition | heuristic | 10 | 0.388 | 0.222 | 0.057 | 0.757 | 0.44 | -0.01 | -0.00 |
| Assumes uniform wind | heuristic | 10 | 0.367 | 0.168 | 0.044 | 0.669 | 0.37 | 0.09 | -0.00 |
| Ignores the smoke column | heuristic | 10 | 0.205 | 0.116 | 0.000 | 0.411 | 0.58 | 0.04 | 0.00 |
| Trusts priors | heuristic | 10 | 0.039 | 0.068 | 0.000 | 0.215 | 0.70 | 0.08 | 0.00 |
| Stop early | baseline | 10 | 0.030 | 0.019 | 0.000 | 0.068 |  |  |  |
| Calibrate, never drop | baseline | 10 | 0.000 | 0.000 | 0.000 | 0.000 |  |  |  |
| Release overhead | baseline | 10 | 0.000 | 0.000 | 0.000 | 0.000 |  |  |  |
| Random actions | baseline | 10 | 0.000 | 0.000 | 0.000 | 0.000 |  |  |  |
| Do nothing | baseline | 10 | 0.000 | 0.000 | 0.000 | 0.000 |  |  |  |

"Lost" columns: mean points lost against the reference on the same seeds, split by cause (see bomber/analysis.py).

haiku-high-nouvel-essai: all 9 missions were cut short by the model provider's safety filter.

claude-haiku-5-5: 6 of 9 missions were cut short by the model provider's safety filter before any real drop and score 0. Mean over the 3 completed missions: 0.810.

claude-haiku-5-5-canadair-2026-11-14: all 9 missions were cut short by the model provider's safety filter.
