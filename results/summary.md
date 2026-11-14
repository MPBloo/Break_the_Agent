# Water Bomber: evaluation summary

Seeds 1..10. Scores are mission scores in [0, 1]. Scripted agents are deterministic.

| Agent | Kind | Episodes | Mean | Std | Min | Max | Lost: experiments | Lost: fitting | Lost: aiming |
|---|---|---|---|---|---|---|---|---|---|
| Reference solution | reference | 10 | 0.894 | 0.034 | 0.829 | 0.949 |  |  |  |
| claude-sonnet-5-5 | frontier | 1 | 0.846 | 0.000 | 0.846 | 0.846 | 0.11 | 0.02 | -0.03 |
| Stops fitting early | heuristic | 10 | 0.679 | 0.342 | 0.000 | 0.932 | -0.00 | 0.22 | -0.00 |
| One flight condition | heuristic | 10 | 0.550 | 0.226 | 0.186 | 0.854 | 0.35 | -0.00 | -0.00 |
| Assumes uniform wind | heuristic | 10 | 0.563 | 0.174 | 0.169 | 0.801 | 0.27 | 0.06 | 0.00 |
| Ignores the smoke column | heuristic | 10 | 0.364 | 0.120 | 0.096 | 0.542 | 0.44 | 0.09 | 0.00 |
| Trusts priors | heuristic | 10 | 0.133 | 0.157 | 0.000 | 0.463 | 0.60 | 0.17 | 0.00 |
| Stop early | baseline | 10 | 0.057 | 0.014 | 0.029 | 0.081 |  |  |  |
| Calibrate, never drop | baseline | 10 | 0.000 | 0.000 | 0.000 | 0.000 |  |  |  |
| Release overhead | baseline | 10 | 0.000 | 0.000 | 0.000 | 0.000 |  |  |  |
| Random actions | baseline | 10 | 0.000 | 0.000 | 0.000 | 0.000 |  |  |  |
| Do nothing | baseline | 10 | 0.000 | 0.000 | 0.000 | 0.000 |  |  |  |

"Lost" columns: mean points lost against the reference on the same seeds, split by cause (see bomber/analysis.py).
