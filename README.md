# Canadair Firefighting

A reinforcement-learning environment about a skill agents are asked for all the time and rarely
tested on: **learn an unknown system with a few costly experiments, then act once, without
feedback.**

A Canadair-style firefighting aircraft must deliver water to five wildfire hotspots. Where a
water load lands depends on the air it falls through: its drag, a wind that strengthens and turns
with altitude, and the updraft above a fire. None of this is known in advance. The agent gets ten
test drops over a calibration fire to find out, then commits to five real drops it never sees land.

```bash
python run_eval.py
```

That one command plays the reference solution, five scripted heuristics and five baselines on
ten seeds, checks the result against the real MCP server, replays any stored frontier-model
transcripts, and writes `results/summary.md` and `results/report.html` (an interactive viewer:
scores, 3D replay of every drop, transcript of every mission). The scripted evaluation takes
about 30 seconds; stored transcript replay and attribution add time as the results folder grows.
It needs only Python 3.10+. `pip install -r requirements.txt` adds the MCP server check.

## Results

The headline table is `results/presented.md`, rebuilt by `python run_eval.py`. Each model is
compared with the reference on the worlds (seeds) it played. Default configuration: 6 m scoring
radius. Scripted agents are deterministic: same seed, same score.

| Agent | Missions | Mean | Range | Reference, same seeds | Below the reference | Refused by safety filter |
|---|---|---|---|---|---|---|
| **Reference solution** | 10 seeds | **0.86** | 0.72 to 0.94 | | | |
| Claude Opus 5.5 | 9 (seeds 1 to 3) | 0.85 | 0.74 to 0.94 | 0.90 | 7 of 9 | 0 of 9 |
| Claude Sonnet 5.5 | 9 | 0.73 | 0.62 to 0.84 | 0.90 | 9 of 9 | 0 of 9 |
| Claude Sonnet 4.5 | 9 | 0.31 | 0.00 to 0.60 | 0.90 | 9 of 9 | 0 of 9 |
| Claude Haiku 5.5 | 9 | not measurable | | | | 9 of 9 |
| Stops fitting early (heuristic) | 10 seeds | 0.60 | 0.00 to 0.89 | | | |
| One flight condition (heuristic) | 10 seeds | 0.74 | 0.63 to 0.90 | | | |
| Assumes uniform wind (heuristic) | 10 seeds | 0.39 | 0.13 to 0.60 | | | |
| Ignores the smoke column (heuristic) | 10 seeds | 0.19 | 0.00 to 0.40 | | | |
| Trusts priors (heuristic) | 10 seeds | 0.04 | 0.00 to 0.22 | | | |
| Stop early (baseline) | 10 seeds | 0.04 | 0.00 to 0.08 | | | |
| Do nothing, calibrate only, release overhead, random actions (baselines) | 10 seeds each | 0.00 | | | | |

On 60 seeds the reference averages 0.846, with a minimum of 0.71.

**What the models show.**

- Claude Sonnet 5.5 and Sonnet 4.5 are below the reference in every mission. Sonnet 5.5 loses
  mostly while fitting (0.16 of its gap); Sonnet 4.5 loses while fitting (0.38) and on the choice
  of experiments (0.11).
- Claude Opus 5.5 comes close: 0.85 against 0.90, below the reference in 7 of 9 missions. Its
  first run made it clear that our reference fitted worse than Opus. The reference now ends its
  fit with a least-squares step on every measurement, the aircraft's wind readings included
  (0.825 to 0.846 on 60 seeds). The gap to Opus is real but narrow.
- Claude Haiku 5.5 cannot be measured: the provider's safety filter stops every mission early
  with the current wording. The wording describes the firefighting task directly and was not tuned
  to get past the filter. Under an earlier wording it completed 3 of 9 missions (0.64 to 0.94).

Earlier runs (previous wording, 10 m radius, the first Haiku retest) are kept in `results/llm/`
and `results/archive/`, listed in `results/summary.md` and under "Earlier runs" in the viewer.
`results/presented.json` decides which runs make the headline table.

**What is and is not established.** The reference, the baselines, the reward and its exploit
tests are measured and reproducible with the command above. The five heuristics are *not* LLM
runs: each is the reference with one decision degraded, which measures what that decision is
worth. Model transcripts are in `results/llm/`; `run_eval.py` replays them to check their scores.
Nine missions per model are a small sample. To run a model:

```bash
cp .env.example .env      # put your key and model in .env (ignored by git)
python run_llm.py --seeds 3 --runs 3
python run_eval.py        # replays the transcripts, attributes lost points, updates the report
```

`.env` selects the model. With `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY`, a Claude model
plays through the official Anthropic SDK (`pip install anthropic`; default model
`claude-opus-5-5`, adaptive thinking, prompt caching, server-side refusal fallbacks unless
`LLM_FALLBACKS=off`; the transcript records which model served). With `LLM_PROVIDER=gemini`,
`openai` or `openrouter` and `LLM_API_KEY`, or `--base-url` for any OpenAI-compatible endpoint,
the generic loop is used. Either way the model gets a one-paragraph instruction and the seven
mission tools: no shell, no code execution. Expect roughly 1.5 to 3 million input tokens per
mission (about 140 tool calls with a growing context); with prompt caching most of them are
cache reads.

To look at results, open `results/report.html` in a browser. It is a single self-contained file,
rebuilt by every `python run_eval.py`.

## The mission

| Tool | What it does | Cost |
|---|---|---|
| `get_mission` | full briefing: rules, known physics, unknowns, budgets, scoring | free |
| `test_drop(heading, altitude, speed, x, y)` | calibration drop: noisy impact point, fall time, smoke flag, wind measured at the aircraft's own altitude | 1 of 10 test drops |
| `compare(hypothesis)` | for every test drop so far, predicted minus observed impact and fall time under the agent's hypothesis | 1 of 120 calculations |
| `simulate(hypothesis, drop)` | predicted impact of any drop under the agent's hypothesis | 1 of 120 calculations |
| `begin_operation` | ends calibration for good, reveals the five wildfire hotspots and their flight constraints | free |
| `drop(target, heading, altitude, speed, x, y)` | the real water drop: one per hotspot, no feedback | 1 per hotspot |
| `declare_done` | ends the mission | free |

A hypothesis is six numbers: `drag`, `wind_speed`, `wind_dir`, `shear`, `veer`, `updraft`. The
briefing states the full physics; those six numbers are the only thing hidden. `simulate` and
`compare` never see the real air, they evaluate whatever hypothesis the agent passes.

Each hotspot imposes a heading, altitude and speed window, revealed only at
`begin_operation`. So a test drop cannot simply be repeated on a target: the agent needs a
model that holds at altitudes, speeds and headings it may not have tested, and through a smoke
column of a different strength.

**Score.** For each hotspot, `max(0, 1 - d / 6 m)` where `d` is the distance from the true
impact to the fire centre. A hotspot that never receives a drop scores -0.5 (it keeps burning).
The mission score is the mean over the five hotspots, floored at 0.

## Why this setting

The setting is aerial wildfire suppression: a water load released by an air tanker is carried
by the wind while it falls, and the release point has to account for the wind at different
altitudes. The environment uses a Canadair-style firefighting aircraft and simplified fire
hotspots to make that decision process concrete. For real firefighting drops, the US Forest
Service measures ground patterns with cup-and-grid drop tests and reports that height, speed
and wind all move and reshape the pattern ([USFS drop guides](https://www.fs.usda.gov/rm/fire/pubs/htmlpubs/htm00572868/intro.htm)),
and a 2026 review lists the joint effect of fire plume, wind and drop height among the open
questions ([Fire, MDPI](https://www.mdpi.com/2571-6255/9/4/166)).

What the environment keeps from the real problem: release-point computation under a wind
profile that changes with altitude, a plume above the fire, costly calibration, no second
chance. What it simplifies, on purpose: the load is a point mass rather than a breaking liquid
column, terrain is flat, and the aircraft has no flight dynamics.

## Where the difficulty comes from

Every way of losing points is a decision, and the tools needed to do better are in the agent's
hands. The heuristics table above prices four of them:

1. **Which experiments to run.** Ten identical test drops fit the data perfectly and
   extrapolate badly (0.39). Shear and veer only show up if altitude varies. The updraft only
   shows up if some drops go through smoke, and is only separable from drag if the same
   condition is also flown in clear air.
2. **Whether to notice what the instruments say.** The wind readout changes with altitude in
   speed and direction. An agent that averages it away loses more than half of its score (0.37).
3. **When the fit is good enough.** One coarse pass over the parameters looks fine on the
   calibration drops and scores anywhere between 0.00 and 0.89 on the targets.
4. **How to aim inside a smoke column.** There, moving the release point by 1 m moves the
   impact by up to 2 m, so "shift by the predicted miss" overshoots and oscillates. The
   correction has to be damped or learned from the last two simulations.

`bomber/analysis.py` turns this into a measurement for any transcript, including an LLM's. It
replays two counterfactuals with the reference's own code on the same world: the reference
fitting on the agent's test drops, and the reference aiming with the agent's final hypothesis.
The differences split the gap into points lost to experiments, to fitting, and to aiming. The
report shows this split per agent.

**Fairness.** The reference plays through the same seven tools with the same budgets and reads
the same briefing. It never imports the physics. Its fitting uses nothing beyond "try a bit
less, try a bit more, keep the best", one parameter at a time, which an agent can do by hand
with `compare`. A test (`test_simulate_is_the_real_physics`) checks that aiming with the true
six numbers scores above 0.97, so nothing outside those six numbers is hidden.

## Reward integrity

`tests/test_exploits.py` attacks the reward; `python -m unittest discover -s tests` runs it.

| Attempt | Outcome |
|---|---|
| Do nothing, or never call `declare_done` | 0 |
| Calibrate carefully, never drop | 0 |
| Stop after two targets | 0.04 (untreated targets score -0.5) |
| Release overhead, random releases, fixed upstream offsets of 40 to 120 m | 0.00 (best offset: 0.004) |
| Repeat a test drop on a target | impossible: run-in windows are revealed after calibration and differ per target |
| Use real drops as experiments | impossible: `drop` returns no impact information, one drop per target |
| Read the score mid-mission | `declare_done` and the verifier's `/score` endpoint both end the mission first |
| NaN, infinities, strings, booleans, out-of-range values, unknown arguments, bad target ids | refused, nothing charged, no state change |
| Rebuild the hidden air from the public code by guessing the seed from the revealed hotspots (an agent with a shell finds it in 0.2 s) | defeated by a secret salt the Harbor tasks pass to the mission server (`BOMBER_SALT`); the agent's container cannot read it |
| Look for the hidden numbers in tool outputs and error messages | not present; `simulate` returns identical answers on worlds with different hidden air |
| Keep calling after the budget or after the end | refused |

Stored transcripts are replayed call by call by `run_eval.py`, which fails if a stored score is
not reproduced.

## Using it from a harness

```bash
python -m bomber.mcp_server                                  # MCP over stdio, seed from BOMBER_SEED
python -m bomber.mcp_server --transport http --port 8000     # streamable HTTP at /mcp, verifier at /score
python solve.py --seed 3 --transport mcp                     # the reference through the MCP server
python harbor/make_tasks.py --seeds 5                        # self-contained Harbor tasks, one per seed
```

The Harbor tasks follow Harbor's official multi-container MCP example: the agent in `main`, the
mission in a separate `mcp-server` container, `solution/solve.sh` running the reference, and
`tests/test.sh` writing the mission score to `/logs/verifier/reward.txt`. The server, HTTP
transport, solution and score endpoint are tested here; the Docker packaging itself has not
been run (no Docker daemon was available).

## Repository

```
bomber/            the environment: physics.py, world.py, episode.py (tools, rules, score),
                   mcp_server.py, analysis.py (lost-points attribution), report.py
agents/            reference.py, heuristics.py (reference with one decision degraded),
                   baselines.py, anthropic_agent.py (Claude loop, Anthropic SDK),
                   llm_agent.py (loop for OpenAI-compatible endpoints)
run_eval.py        the one command
run_llm.py         run a frontier model and store its transcripts
solve.py           the reference on one seed
export_dataset.py  reference missions as fine-tuning data (stretch goal scaffold, not yet used)
harbor/            Harbor task generator
tests/             rules, determinism, plumbing, exploits
results/           summary.md, summary.json, report.html
docs/DESIGN.md     design notes, calibration history, difficulty knobs
docs/GUIDE_FR.md   guide for the team, in French
```

All tunable numbers (budgets, noise, scoring radius, parameter ranges) are in
`bomber/config.py`. Any reported number should state the configuration it was produced with.
