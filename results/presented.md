# Headline results

Each model is compared with the reference on the same worlds (same seeds). A mission ended by the model provider's safety filter scores 0 and is counted separately: it says nothing about how the model plays.

| Agent | Missions | Mean score | Range | Reference on the same seeds | Missions below the reference | Refused by safety filter | Lost: experiments | Lost: fitting | Lost: aiming |
|---|---|---|---|---|---|---|---|---|---|
| **Reference solution** | 10 seeds | **0.86** | 0.72 to 0.94 | | | | | | |
| Claude Opus 5.5 | 9 | 0.85 | 0.74 to 0.94 | 0.90 | 7 of 9 | 0 of 9 | 0.02 | 0.01 | 0.01 |
| Claude Sonnet 5.5 | 9 | 0.73 | 0.62 to 0.84 | 0.90 | 9 of 9 | 0 of 9 | 0.04 | 0.16 | -0.03 |
| Claude Sonnet 4.5 | 9 | 0.31 | 0.00 to 0.60 | 0.90 | 9 of 9 | 0 of 9 | 0.11 | 0.38 | 0.09 |
| Claude Haiku 5.5 | 9 | not measurable | | | | 9 of 9 | | | |
| Stops fitting early (heuristic) | 10 seeds | 0.60 | 0.00 to 0.89 | | | | | | |
| One flight condition (heuristic) | 10 seeds | 0.74 | 0.63 to 0.90 | | | | | | |
| Assumes uniform wind (heuristic) | 10 seeds | 0.39 | 0.13 to 0.60 | | | | | | |
| Ignores the smoke column (heuristic) | 10 seeds | 0.19 | 0.00 to 0.40 | | | | | | |
| Trusts priors (heuristic) | 10 seeds | 0.04 | 0.00 to 0.22 | | | | | | |
| Stop early (baseline) | 10 seeds | 0.04 | 0.00 to 0.08 | | | | | | |
| Calibrate, never drop (baseline) | 10 seeds | 0.00 | 0.00 to 0.00 | | | | | | |
| Release overhead (baseline) | 10 seeds | 0.00 | 0.00 to 0.00 | | | | | | |
| Random actions (baseline) | 10 seeds | 0.00 | 0.00 to 0.00 | | | | | | |
| Do nothing (baseline) | 10 seeds | 0.00 | 0.00 to 0.00 | | | | | | |

Lost columns: mean points lost against the reference, split by the decision that lost them (see bomber/analysis.py). Model runs not listed in results/presented.json are in summary.md.
