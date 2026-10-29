# Noise-Aware Evaluation Harness — Design

**Date:** 2026-10-29
**Status:** Draft, awaiting review

## Problem

Our leaderboard results since Oct 5 (23–30%) cannot be distinguished from one agent with a true mean near 26%.
Public write-ups of identical code show the same spread: Franzen's unmodified solution scored 21.01–31.47 across seven
draws (mean 25.77, SD 3.93), and one team found that none of 23 tested changes moved the hidden-game score. With one
Kaggle submission per day, we cannot tell whether a change helped. `src/evaluate.py` runs one agent over a list of games and
logs one score per run, with no repeats, no paired comparison and no variance estimate.

## Goal

Raise the expected leaderboard score on the 110 unseen games by making improvement measurable: a change is promoted to a
Kaggle submission only when a local, repeated, equal-budget comparison shows a gain larger than the measured noise.

## Non-goals

- Changing the Kaggle submission packages, the priority scheduler, or the `ls20` win-path cache.
- Building new agent capabilities. This work only measures.
- Replacing the Kaggle leaderboard as the final confirmation of a change.

## Assumptions and risks

- The Qwen/SGLang stack cannot run locally, so the local agent uses the OpenAI model (`gpt-6-luna`) as a stand-in. The
  harness measures harness and tool changes well and model-specific behavior poorly.
- The 25 public games are for local validation only. `ls20` is excluded from comparisons because the win-path cache
  replays hardcoded solutions for it.
- Arcade environments are assumed deterministic per game, so run-to-run noise comes from model sampling. Seeds therefore
  set sampling seed and temperature only. `src/agents/openai_tool_agent.py` may not accept a seed; the pilot must confirm
  this, and if it does not, the harness still works but cannot reproduce a specific run.
- Per-game cost is one local-model call per action. Budget is unknown until the pilot measures it.

## Measurement protocol

- **Arm:** a named config (agent, model, flags, per-game action and token cap). The baseline arm is the V12-style core with
  the win-path cache disabled.
- **Run:** one arm on one game with one seed under a fixed cap. Output is the per-game score from the scorecard, the same
  efficiency-weighted score `src/metrics.py` already computes.
- **Noise floor:** repeated baseline-vs-baseline runs; the spread of the suite mean (and of per-game scores) is the
  decision threshold.
- **Decision rule:** a candidate is "real" only if its paired improvement over the baseline has a 90% bootstrap interval
  above zero and a mean gain larger than the noise floor.

## Components

All new code lives under `src/experiments/`. `Evaluator.run_game` in `src/evaluate.py` is not modified.

1. `arms.py` — frozen `Arm` dataclass (name, agent class, model, flags, per-game action and token cap) and a registry so a
   run is selected by arm name, not by loose CLI flags. The baseline arm disables the `ls20` cache.
2. `runner.py` — wraps `Evaluator.run_game`. For each (arm, game, seed) it runs the game and appends one JSON line to a
   results file. A crash loses at most one run, and reruns skip lines already present.
3. `stats.py` — pure functions, no I/O: `paired_diff` (per-game difference, then mean), `bootstrap_ci` (resamples games
   and seeds, default 90% interval), `noise_floor` (spread of baseline-vs-baseline suite means), `verdict` (the decision
   rule above).
4. `report.py` — CLI that reads the results file and prints a table (arm, mean, interval, verdict). It records the
   outcome in `docs/experiments.md` through the existing `log_experiment` path so the ledger stays the single record.

## Data flow

`report.py` / CLI selects arms and games → `runner.py` runs (arm, game, seed) via `Evaluator.run_game` → one JSON line per
run in a results file → `stats.py` consumes those lines → `report.py` prints the table and logs to the ledger.

## Pilot (first deliverable)

3 seeds of the baseline arm on a fixed 8-game subset with a short action cap. It measures the real cost per run and the
actual spread, and confirms whether seeding works. If one baseline suite is too expensive to repeat, the fallback is fewer
games with more seeds, since seeds are what reveal variance.

## Error handling

- A run that raises is recorded as a failed line (arm, game, seed, error), not retried silently, and excluded from stats
  with the count reported.
- The results file is append-only JSONL; a truncated final line is ignored on load.
- `verdict` returns "insufficient data" when there are fewer than the minimum seeds per arm, rather than a verdict.

## Testing

- `stats.py`: unit tests on synthetic data with a known effect and known noise: the verdict fires on a real gain and stays
  quiet on pure noise.
- `runner.py`: tested with `RandomAgent` and a fake evaluator; covers resume after a partial results file and one line per run.
- `arms.py`: registry round-trip, and a check that the baseline arm disables the `ls20` cache.
- All new code passes `pytest tests/` and `ruff check` with type annotations, per CLAUDE.md.

## Success criteria

- The pilot yields a noise floor for the baseline arm and a measured cost per run.
- Given two arms where one is known to be better (for example, baseline vs. a deliberately weakened baseline), `verdict`
  identifies the better arm; given two copies of the baseline, it reports no difference.
- Every later change proposal (D', scheduler, prompts, primitives) can be evaluated with one command and one table.
