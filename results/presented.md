# Headline results

Each model is compared with the reference on the same worlds (same seeds). A mission ended by the model provider's safety filter scores 0 and is counted separately: it says nothing about how the model plays.

| Agent | Missions | Mean score | Range | Reference on the same seeds | Missions below the reference | Refused by safety filter | Lost: experiments | Lost: fitting | Lost: aiming |
|---|---|---|---|---|---|---|---|---|---|
| **Reference solution** | 10 seeds | **0.82** | 0.71 to 0.91 | | | | | | |
| Claude Sonnet 5.5 | 9 | 0.73 | 0.62 to 0.84 | 0.88 | 9 of 9 | 0 of 9 | 0.04 | 0.14 | -0.03 |
| Claude Sonnet 4.5 | 9 | 0.31 | 0.00 to 0.60 | 0.88 | 9 of 9 | 0 of 9 | 0.10 | 0.38 | 0.09 |
| Claude Haiku 5.5 | 9 | not measurable | | | | 9 of 9 | | | |
| Stops fitting early (heuristic) | 10 seeds | 0.60 | 0.00 to 0.89 | | | | | | |
| One flight condition (heuristic) | 10 seeds | 0.39 | 0.06 to 0.76 | | | | | | |
| Assumes uniform wind (heuristic) | 10 seeds | 0.37 | 0.04 to 0.67 | | | | | | |
| Ignores the smoke column (heuristic) | 10 seeds | 0.20 | 0.00 to 0.41 | | | | | | |
| Trusts priors (heuristic) | 10 seeds | 0.04 | 0.00 to 0.22 | | | | | | |
| Stop early (baseline) | 10 seeds | 0.03 | 0.00 to 0.07 | | | | | | |
| Calibrate, never drop (baseline) | 10 seeds | 0.00 | 0.00 to 0.00 | | | | | | |
| Release overhead (baseline) | 10 seeds | 0.00 | 0.00 to 0.00 | | | | | | |
| Random actions (baseline) | 10 seeds | 0.00 | 0.00 to 0.00 | | | | | | |
| Do nothing (baseline) | 10 seeds | 0.00 | 0.00 to 0.00 | | | | | | |

Lost columns: mean points lost against the reference, split by the decision that lost them (see bomber/analysis.py). Model runs not listed in results/presented.json are in summary.md.
