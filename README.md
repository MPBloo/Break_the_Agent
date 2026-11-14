# Water Bomber

A reinforcement-learning environment about a skill agents are asked for all the time and rarely
tested on: **learn an unknown system with a few costly experiments, then act once, without
feedback.**

An air tanker must hit five spot fires with one water drop each. Where a load lands depends on
the air it falls through: its drag, a wind that strengthens and turns with altitude, and the
updraft above a fire. None of this is known in advance. The agent gets ten test drops over a
calibration fire to find out, then commits to five real drops it never sees land.

```bash
python run_eval.py
```

That one command plays the reference solution, five scripted heuristics and five baselines on
ten seeds, checks the result against the real MCP server, replays any stored frontier-model
transcripts, and writes `results/summary.md` and `results/report.html` (an interactive viewer:
scores, 3D replay of every drop, transcript of every mission). It takes about 30 seconds and
needs only Python 3.10+. `pip install -r requirements.txt` adds the MCP server check.

## Results

Ten seeds, default configuration. Scripted agents are deterministic: same seed, same score.

| Agent | What it is | Mean | Min | Max |
|---|---|---|---|---|
| **Reference solution** | same tools, same budgets, better method | **0.89** | 0.83 | 0.95 |
| Stops fitting early | reference experiments, one coarse fitting pass | 0.68 | 0.00 | 0.93 |
| Assumes uniform wind | varied tests at one altitude, no shear, no veer | 0.56 | 0.17 | 0.80 |
| One flight condition | ten tests at the same heading, altitude, speed | 0.55 | 0.19 | 0.85 |
| Ignores the smoke column | careful clear-air tests, updraft left at zero | 0.36 | 0.10 | 0.54 |
| Trusts priors | one test drop, mid-range guesses, no fitting | 0.13 | 0.00 | 0.46 |
| Stop early | plays like the reference, stops after 2 of 5 targets | 0.06 | 0.03 | 0.08 |
| Calibrate, never drop | | 0.00 | 0.00 | 0.00 |
| Release overhead (no model) | | 0.00 | 0.00 | 0.00 |
| Random actions | | 0.00 | 0.00 | 0.00 |
| Do nothing | | 0.00 | 0.00 | 0.00 |

On 60 seeds the reference averages 0.895 and never falls below 0.80.

**What is and is not established.** The reference, the baselines, the reward and its exploit
tests are measured and reproducible with the command above. The five heuristics are *not* LLM
runs: each is the reference with one decision degraded, which measures what that decision is
worth. **No frontier model has been run yet in this repository** (no API key was available
where it was built). The harness for it is ready and tested against a mock endpoint:

```bash
export LLM_API_KEY=...
python run_llm.py --provider gemini --model <model id> --seeds 3 --runs 3
python run_eval.py        # replays the transcripts, attributes lost points, updates the report
```

`--provider` accepts `gemini`, `openai`, `anthropic`, `openrouter`; `--base-url` accepts any
OpenAI-compatible endpoint. The model plays in a plain tool-calling loop with the seven mission
tools: no shell, no code execution. Expect roughly 1.5 to 3 million input tokens per mission
without prompt caching (about 140 tool calls with a growing context).

## The mission

| Tool | What it does | Cost |
|---|---|---|
| `get_mission` | full briefing: rules, known physics, unknowns, budgets, scoring | free |
| `test_drop(heading, altitude, speed, x, y)` | calibration drop: noisy impact point, fall time, smoke flag, wind measured at the aircraft's own altitude | 1 of 10 test drops |
| `compare(hypothesis)` | for every test drop so far, predicted minus observed impact and fall time under the agent's hypothesis | 1 of 120 calculations |
| `simulate(hypothesis, drop)` | predicted impact of any drop under the agent's hypothesis | 1 of 120 calculations |
| `begin_operation` | ends calibration for good, reveals the five targets and their imposed run-in | free |
| `drop(target, heading, altitude, speed, x, y)` | the real drop: one per target, no feedback | 1 per target |
| `declare_done` | ends the mission | free |

A hypothesis is six numbers: `drag`, `wind_speed`, `wind_dir`, `shear`, `veer`, `updraft`. The
briefing states the full physics; those six numbers are the only thing hidden. `simulate` and
`compare` never see the real air, they evaluate whatever hypothesis the agent passes.

Each target imposes a heading, altitude and speed window ("run-in"), revealed only at
`begin_operation`. So a test drop cannot simply be repeated on a target: the agent needs a
model that holds at altitudes, speeds and headings it may not have tested, and through a smoke
column of a different strength.

**Score.** For each target, `max(0, 1 - d / 10 m)` where `d` is the distance from the true
impact to the fire centre. A target that never receives a drop scores -0.5 (it keeps burning).
The mission score is the mean over the five targets, floored at 0.

## Why this setting

The same procedure exists in practice. Military and humanitarian airdrops compute a release
point (CARP) from a wind profile measured by dropsondes released beforehand, and wind is the
largest error term in that calculation ([AFMAN 11-231](https://static.e-publishing.af.mil/production/1/af_a3/publication/afman11-231/afman11-231.pdf),
[Defense Update](https://defense-update.com/?p=20036)). For firefighting drops, the US Forest
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
   extrapolate badly (0.55). Shear and veer only show up if altitude varies. The updraft only
   shows up if some drops go through smoke, and is only separable from drag if the same
   condition is also flown in clear air.
2. **Whether to notice what the instruments say.** The wind readout changes with altitude in
   speed and direction. An agent that averages it away loses a third of its score (0.56).
3. **When the fit is good enough.** One coarse pass over the parameters looks fine on the
   calibration drops and scores anywhere between 0.00 and 0.93 on the targets.
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
| Stop after two targets | 0.06 (untreated targets score -0.5) |
| Release overhead, random releases, fixed upstream offsets of 40 to 120 m | 0.00 (best offset: 0.004) |
| Repeat a test drop on a target | impossible: run-in windows are revealed after calibration and differ per target |
| Use real drops as experiments | impossible: `drop` returns no impact information, one drop per target |
| Read the score mid-mission | `declare_done` and the verifier's `/score` endpoint both end the mission first |
| NaN, infinities, strings, booleans, out-of-range values, unknown arguments, bad target ids | refused, nothing charged, no state change |
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
                   baselines.py, llm_agent.py (frontier-model loop)
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
