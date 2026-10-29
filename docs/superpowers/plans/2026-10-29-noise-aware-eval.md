# Noise-Aware Evaluation Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local repeat-run A/B harness that tells us whether an agent change beats the baseline by more than the measured noise, so we only spend a Kaggle submission on changes that pass.

**Architecture:** A new `src/experiments/` package wraps the existing `EvaluationRunner.run_game` (unchanged). `runner.py` runs (arm, game, seed) triples and appends one JSON line per run; `stats.py` (pure functions) computes the noise floor, paired differences, a game-clustered bootstrap CI and a verdict; `report.py` prints the comparison table and appends a ledger row. `OpenAIToolAgent` gets optional `seed` and `temperature` parameters so runs can be repeated with distinct sampling seeds.

**Tech Stack:** Python 3.10+, standard library only for the new package (`json`, `random`, `statistics`, `argparse`), `pytest`, `ruff`. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-10-29-noise-aware-eval-design.md`

## Global Constraints

- All new code lives under `src/experiments/`; `EvaluationRunner.run_game` in `src/evaluate.py` is not modified.
- `ls20` is excluded from comparisons (the win-path cache replays hardcoded solutions for it).
- The baseline arm disables the win-path cache.
- Decision rule: "better" only if the paired improvement's 90% bootstrap interval is above zero **and** the mean gain exceeds the noise floor; symmetric for "worse"; otherwise "no difference"; fewer than the minimum seeds gives "insufficient data".
- Results are append-only JSONL; a failed run is recorded with an error, never retried silently, and excluded from statistics with the count reported.
- Code is type-annotated, line length 100 (`pyproject.toml`), and new files pass `ruff check`.
- Test with `python3 -m pytest tests/ -q` (128 tests pass before this work starts).

## Review Focus

- **Crash mid-write:** a results file whose last line was cut off must not swallow the next appended record (Task 2).
- **A run that raises:** it must be recorded with its error, excluded from statistics, and counted in the report (Tasks 5 and 6).
- **Arms with different coverage:** only (game, seed) pairs both arms completed may enter the comparison (Task 3).
- **All-zero scores:** two arms scoring 0 everywhere must read "no difference", not "better" (Task 3).
- **`ls20` slipping into a comparison:** the game list must be rejected, not silently scored (Tasks 4 and 5).

## File Structure

| File | Responsibility |
| :--- | :--- |
| `src/agents/openai_tool_agent.py` (modify) | Accept optional `seed` and `temperature`, include them in the API payload when set |
| `src/experiments/__init__.py` (create) | Package marker |
| `src/experiments/records.py` (create) | `RunRecord` dataclass and append/load of the JSONL results file |
| `src/experiments/stats.py` (create) | Noise floor, paired differences, bootstrap CI, verdict (no I/O) |
| `src/experiments/arms.py` (create) | `Arm` config, registry, `build_agent`, `validate_games`, `PILOT_GAMES` |
| `src/experiments/runner.py` (create) | `run_arm` plus a CLI to run an arm over games and seeds |
| `src/experiments/report.py` (create) | Comparison table, ledger row, CLI |
| `tests/test_openai_tool_agent_sampling.py` (create) | Seed/temperature payload tests |
| `tests/test_experiments_records.py`, `_stats.py`, `_arms.py`, `_runner.py`, `_report.py`, `_end_to_end.py` (create) | One test file per module plus an end-to-end check |

Two small deviations from the spec, both deliberate: `records.py` is added to the four components so `stats.py` stays free of any dependency on the evaluator, and `report.py` writes its own ledger row (same file, same 8-column layout) instead of calling `log_experiment`, because that function takes a `SuiteEvalSummary` and cannot express a paired comparison.

---

### Task 1: Optional seed and temperature on `OpenAIToolAgent`

**Files:**
- Modify: `src/agents/openai_tool_agent.py:45-52` (constructor) and `:106-130` (payload in `_call_api`)
- Test: `tests/test_openai_tool_agent_sampling.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `OpenAIToolAgent(model=..., api_key=..., cache_path=..., seed: int | None = None, temperature: float | None = None)`, with attributes `agent.seed` and `agent.temperature`. When set, `"seed"` / `"temperature"` appear in the chat-completions payload; when `None` the payload is unchanged.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_openai_tool_agent_sampling.py
import json

from src.agents.openai_tool_agent import OpenAIToolAgent


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False

    def read(self) -> bytes:
        return self._body


def _capture_payload(monkeypatch) -> dict:
    captured: dict = {}

    def fake_urlopen(req, timeout=None, context=None):
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        body = json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode("utf-8")
        return _FakeResponse(body)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    return captured


def test_payload_includes_seed_and_temperature_when_set(tmp_path, monkeypatch):
    captured = _capture_payload(monkeypatch)
    agent = OpenAIToolAgent(
        api_key="dummy", cache_path=tmp_path / "c.json", seed=7, temperature=0.6
    )
    assert agent._call_api("hi") == "ok"
    assert captured["payload"]["seed"] == 7
    assert captured["payload"]["temperature"] == 0.6


def test_payload_unchanged_when_seed_and_temperature_unset(tmp_path, monkeypatch):
    captured = _capture_payload(monkeypatch)
    agent = OpenAIToolAgent(api_key="dummy", cache_path=tmp_path / "c.json")
    agent._call_api("hi")
    assert "seed" not in captured["payload"]
    assert "temperature" not in captured["payload"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_openai_tool_agent_sampling.py -v`
Expected: FAIL with `TypeError: OpenAIToolAgent.__init__() got an unexpected keyword argument 'seed'`

- [ ] **Step 3: Write minimal implementation**

In `src/agents/openai_tool_agent.py`, extend the constructor signature and store the values:

```python
    def __init__(
        self,
        model: str = "gpt-6-luna",
        api_key: str | None = None,
        api_base: str = "https://api.openai.com/v1",
        timeout: float = 45.0,
        cache_path: Path | str | None = None,
        seed: int | None = None,
        temperature: float | None = None,
    ) -> None:
```

Directly after `self.timeout = timeout` add:

```python
        self.seed = seed
        self.temperature = temperature
```

In `_call_api`, immediately after the closing `}` of the `payload = {...}` dict and before `data = json.dumps(payload)...`, add:

```python
        if self.seed is not None:
            payload["seed"] = self.seed
        if self.temperature is not None:
            payload["temperature"] = self.temperature
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_openai_tool_agent_sampling.py tests/test_openai_tool_agent.py -v`
Expected: all PASS (new tests plus the existing tool-agent tests).

- [ ] **Step 5: Commit**

```bash
git add src/agents/openai_tool_agent.py tests/test_openai_tool_agent_sampling.py
git commit -m "feat(agent): optional seed and temperature for OpenAIToolAgent"
```

---

### Task 2: Run records and JSONL store

**Files:**
- Create: `src/experiments/__init__.py` (empty)
- Create: `src/experiments/records.py`
- Test: `tests/test_experiments_records.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `RunRecord(arm: str, game: str, seed: int, score: float, levels_completed: int, total_actions: int, error: str | None = None)`, frozen, with properties `ok -> bool` and `key -> tuple[str, str, int]` (arm, game, seed).
  - `append_record(path: Path | str, record: RunRecord) -> None`
  - `load_records(path: Path | str) -> list[RunRecord]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_experiments_records.py
from src.experiments.records import RunRecord, append_record, load_records


def _rec(game: str, seed: int = 0, error: str | None = None) -> RunRecord:
    return RunRecord("a", game, seed, 12.5, 2, 40, error)


def test_round_trip_and_ok_flag(tmp_path):
    path = tmp_path / "r.jsonl"
    append_record(path, _rec("g0"))
    append_record(path, _rec("g1", error="RuntimeError: boom"))
    loaded = load_records(path)
    assert [r.game for r in loaded] == ["g0", "g1"]
    assert loaded[0].ok is True
    assert loaded[1].ok is False
    assert loaded[0].key == ("a", "g0", 0)


def test_load_missing_file_is_empty(tmp_path):
    assert load_records(tmp_path / "nope.jsonl") == []


def test_append_after_truncated_line_does_not_merge_records(tmp_path):
    path = tmp_path / "r.jsonl"
    append_record(path, _rec("g0"))
    with open(path, "a", encoding="utf-8") as handle:
        handle.write('{"arm": "a", "gam')  # crash mid-write, no trailing newline
    append_record(path, _rec("g1"))
    assert [r.game for r in load_records(path)] == ["g0", "g1"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_experiments_records.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.experiments'`

- [ ] **Step 3: Write minimal implementation**

Create an empty `src/experiments/__init__.py`, then:

```python
# src/experiments/records.py
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunRecord:
    arm: str
    game: str
    seed: int
    score: float
    levels_completed: int
    total_actions: int
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def key(self) -> tuple[str, str, int]:
        return (self.arm, self.game, self.seed)


def append_record(path: Path | str, record: RunRecord) -> None:
    """Append one record as a JSON line, first terminating a truncated final line."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    needs_newline = False
    if target.exists() and target.stat().st_size > 0:
        with open(target, "rb") as handle:
            handle.seek(-1, 2)
            needs_newline = handle.read(1) != b"\n"
    with open(target, "a", encoding="utf-8") as handle:
        if needs_newline:
            handle.write("\n")
        handle.write(json.dumps(asdict(record)) + "\n")


def load_records(path: Path | str) -> list[RunRecord]:
    """Load records, skipping blank or unparsable lines (e.g. a line cut off by a crash)."""
    target = Path(path)
    if not target.exists():
        return []
    records: list[RunRecord] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            records.append(RunRecord(**json.loads(text)))
        except (json.JSONDecodeError, TypeError):
            continue
    return records
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_experiments_records.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add src/experiments/__init__.py src/experiments/records.py tests/test_experiments_records.py
git commit -m "feat(experiments): run records and append-only JSONL store"
```

---

### Task 3: Statistics (noise floor, paired differences, bootstrap, verdict)

**Files:**
- Create: `src/experiments/stats.py`
- Test: `tests/test_experiments_stats.py`

**Interfaces:**
- Consumes: `RunRecord` from `src.experiments.records` (`.arm`, `.game`, `.seed`, `.score`, `.ok`).
- Produces:
  - `Verdict(label: str, mean_diff: float, ci_low: float, ci_high: float, noise_floor: float, n_pairs: int, seeds_baseline: int, seeds_candidate: int)`, frozen. `label` is one of `"better"`, `"worse"`, `"no difference"`, `"insufficient data"`.
  - `suite_means(records, arm) -> dict[int, float]` (seed → mean score over games, failed runs excluded)
  - `noise_floor(records, arm) -> float | None` (sample SD of the per-seed suite means; `None` with fewer than 2 seeds)
  - `paired_diffs(records, baseline, candidate) -> list[tuple[str, float]]` ((game, candidate − baseline) for pairs present in both arms)
  - `bootstrap_ci(diffs, level=0.9, n_boot=2000, seed=0) -> tuple[float, float]` (resamples whole games; raises `ValueError` on empty input)
  - `verdict(records, baseline, candidate, min_seeds=2, level=0.9, n_boot=2000) -> Verdict`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_experiments_stats.py
import random

from src.experiments.records import RunRecord
from src.experiments.stats import bootstrap_ci, noise_floor, paired_diffs, suite_means, verdict

GAMES = [f"g{i}" for i in range(8)]


def rec(arm, game, seed, score, error=None):
    return RunRecord(arm, game, seed, score, 0, 0, error)


def synthetic(effect, noise=2.0, seeds=3, rng_seed=0):
    rng = random.Random(rng_seed)
    out = []
    for gi, game in enumerate(GAMES):
        base_mean = 10.0 + 5.0 * gi
        for seed in range(seeds):
            out.append(rec("base", game, seed, base_mean + rng.gauss(0, noise)))
            out.append(rec("cand", game, seed, base_mean + effect + rng.gauss(0, noise)))
    return out


def test_suite_means_excludes_failed_runs():
    records = [rec("a", "g0", 0, 10.0), rec("a", "g1", 0, 20.0), rec("a", "g2", 0, 0.0, "boom")]
    assert suite_means(records, "a") == {0: 15.0}


def test_noise_floor_none_with_single_seed():
    assert noise_floor([rec("a", "g0", 0, 5.0)], "a") is None


def test_noise_floor_is_stdev_of_seed_means():
    records = [rec("a", "g0", 0, 10.0), rec("a", "g0", 1, 20.0)]
    assert abs(noise_floor(records, "a") - 7.0710678) < 1e-6


def test_paired_diffs_only_uses_pairs_present_in_both_arms():
    records = [rec("b", "g0", 0, 10.0), rec("b", "g1", 0, 10.0), rec("c", "g0", 0, 14.0)]
    assert paired_diffs(records, "b", "c") == [("g0", 4.0)]


def test_bootstrap_ci_constant_diffs_collapse_to_the_value():
    assert bootstrap_ci([("g0", 3.0), ("g1", 3.0)]) == (3.0, 3.0)


def test_verdict_better_on_real_gain():
    assert verdict(synthetic(effect=10.0), "base", "cand").label == "better"


def test_verdict_worse_on_real_loss():
    assert verdict(synthetic(effect=-10.0), "base", "cand").label == "worse"


def test_verdict_no_difference_for_identical_arms():
    records = []
    for game in GAMES:
        for seed in range(3):
            score = 10.0 + seed
            records += [rec("base", game, seed, score), rec("cand", game, seed, score)]
    result = verdict(records, "base", "cand")
    assert result.label == "no difference"
    assert result.mean_diff == 0.0


def test_verdict_no_difference_under_pure_noise():
    assert verdict(synthetic(effect=0.0), "base", "cand").label == "no difference"


def test_verdict_insufficient_with_one_seed():
    assert verdict(synthetic(effect=10.0, seeds=1), "base", "cand").label == "insufficient data"


def test_verdict_all_zero_scores_is_not_better():
    records = [rec(arm, g, s, 0.0) for arm in ("base", "cand") for g in GAMES for s in range(3)]
    assert verdict(records, "base", "cand").label == "no difference"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_experiments_stats.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.experiments.stats'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/experiments/stats.py
from __future__ import annotations

import random
import statistics
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from src.experiments.records import RunRecord


@dataclass(frozen=True)
class Verdict:
    label: str  # "better", "worse", "no difference" or "insufficient data"
    mean_diff: float
    ci_low: float
    ci_high: float
    noise_floor: float
    n_pairs: int
    seeds_baseline: int
    seeds_candidate: int


def suite_means(records: Sequence[RunRecord], arm: str) -> dict[int, float]:
    """Mean score over games for each seed of one arm (failed runs excluded)."""
    by_seed: dict[int, list[float]] = defaultdict(list)
    for rec in records:
        if rec.arm == arm and rec.ok:
            by_seed[rec.seed].append(rec.score)
    return {seed: sum(scores) / len(scores) for seed, scores in by_seed.items()}


def noise_floor(records: Sequence[RunRecord], arm: str) -> float | None:
    """Sample standard deviation of per-seed suite means; None with fewer than 2 seeds."""
    means = list(suite_means(records, arm).values())
    if len(means) < 2:
        return None
    return statistics.stdev(means)


def paired_diffs(
    records: Sequence[RunRecord], baseline: str, candidate: str
) -> list[tuple[str, float]]:
    """(game, candidate - baseline) for every (game, seed) that both arms completed."""
    base = {(r.game, r.seed): r.score for r in records if r.arm == baseline and r.ok}
    cand = {(r.game, r.seed): r.score for r in records if r.arm == candidate and r.ok}
    return [
        (game, cand[(game, seed)] - base[(game, seed)])
        for game, seed in sorted(base.keys() & cand.keys())
    ]


def bootstrap_ci(
    diffs: Sequence[tuple[str, float]],
    level: float = 0.9,
    n_boot: int = 2000,
    seed: int = 0,
) -> tuple[float, float]:
    """Percentile CI of the mean difference, resampling whole games (seeds stay together)."""
    if not diffs:
        raise ValueError("bootstrap_ci needs at least one paired difference")
    by_game: dict[str, list[float]] = defaultdict(list)
    for game, diff in diffs:
        by_game[game].append(diff)
    games = sorted(by_game)
    rng = random.Random(seed)
    means: list[float] = []
    for _ in range(n_boot):
        picked = [rng.choice(games) for _ in games]
        values = [v for game in picked for v in by_game[game]]
        means.append(sum(values) / len(values))
    means.sort()
    alpha = (1.0 - level) / 2.0
    low = means[int(alpha * n_boot)]
    high = means[min(n_boot - 1, int((1.0 - alpha) * n_boot))]
    return low, high


def verdict(
    records: Sequence[RunRecord],
    baseline: str,
    candidate: str,
    min_seeds: int = 2,
    level: float = 0.9,
    n_boot: int = 2000,
) -> Verdict:
    floor = noise_floor(records, baseline)
    seeds_base = len(suite_means(records, baseline))
    seeds_cand = len(suite_means(records, candidate))
    diffs = paired_diffs(records, baseline, candidate)
    if floor is None or seeds_base < min_seeds or seeds_cand < min_seeds or not diffs:
        return Verdict(
            "insufficient data", 0.0, 0.0, 0.0, floor or 0.0, len(diffs), seeds_base, seeds_cand
        )
    mean_diff = sum(d for _, d in diffs) / len(diffs)
    low, high = bootstrap_ci(diffs, level=level, n_boot=n_boot)
    if low > 0.0 and mean_diff > floor:
        label = "better"
    elif high < 0.0 and -mean_diff > floor:
        label = "worse"
    else:
        label = "no difference"
    return Verdict(label, mean_diff, low, high, floor, len(diffs), seeds_base, seeds_cand)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_experiments_stats.py -v`
Expected: 11 PASS

- [ ] **Step 5: Commit**

```bash
git add src/experiments/stats.py tests/test_experiments_stats.py
git commit -m "feat(experiments): noise floor, paired diffs, bootstrap CI and verdict"
```

---

### Task 4: Arms registry and game validation

**Files:**
- Create: `src/experiments/arms.py`
- Test: `tests/test_experiments_arms.py`

**Interfaces:**
- Consumes: `OpenAIToolAgent(model, cache_path, seed, temperature)` from Task 1; `RandomAgent(seed)` from `src.agents`.
- Produces:
  - `Arm(name: str, agent: str, model: str = "gpt-6-luna", max_actions_per_level: int = 400, use_win_cache: bool = False, temperature: float | None = None)`, frozen. `agent` is `"random"` or `"openai_tool"`.
  - `ARMS: dict[str, Arm]` with `"random"`, `"tool_baseline"` (cap 100, cache off) and `"tool_weak"` (cap 5, cache off; a deliberately weakened baseline used to sanity-check the verdict).
  - `PILOT_GAMES: tuple[str, ...]` (8 public games, no `ls20`).
  - `build_agent(arm: Arm, seed: int, workdir: Path) -> BaseAgent` (when the cache is off, the agent's cache file is `workdir / "win_paths.json"`, which does not exist yet, so nothing is replayed and nothing touches `oof/win_paths.json`).
  - `validate_games(games: Sequence[str]) -> list[str]` (raises `ValueError` if any game starts with `ls20`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_experiments_arms.py
import dataclasses

import pytest

from src.agents import OpenAIToolAgent, RandomAgent
from src.experiments.arms import ARMS, PILOT_GAMES, build_agent, validate_games


def test_baseline_arm_disables_win_path_cache(tmp_path):
    arm = ARMS["tool_baseline"]
    assert arm.use_win_cache is False
    agent = build_agent(arm, seed=3, workdir=tmp_path)
    assert isinstance(agent, OpenAIToolAgent)
    assert agent.cache_path == tmp_path / "win_paths.json"
    assert agent.cached_solutions == {}
    assert agent.seed == 3


def test_weak_arm_has_smaller_action_cap_than_baseline():
    assert ARMS["tool_weak"].max_actions_per_level < ARMS["tool_baseline"].max_actions_per_level


def test_random_arm_builds_random_agent(tmp_path):
    assert isinstance(build_agent(ARMS["random"], seed=1, workdir=tmp_path), RandomAgent)


def test_unknown_agent_key_raises(tmp_path):
    bad = dataclasses.replace(ARMS["random"], name="bad", agent="nope")
    with pytest.raises(ValueError):
        build_agent(bad, seed=0, workdir=tmp_path)


def test_validate_games_rejects_ls20():
    with pytest.raises(ValueError, match="ls20"):
        validate_games(["ar25", "ls20"])


def test_pilot_games_pass_validation():
    assert validate_games(list(PILOT_GAMES)) == list(PILOT_GAMES)
    assert len(PILOT_GAMES) == 8
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_experiments_arms.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.experiments.arms'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/experiments/arms.py
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from src.agents import BaseAgent, OpenAIToolAgent, RandomAgent

PILOT_GAMES: tuple[str, ...] = (
    "ar25", "cd82", "dc22", "ft09", "lp85", "sb26", "tr87", "vc33",
)
EXCLUDED_GAME_PREFIXES: tuple[str, ...] = ("ls20",)


@dataclass(frozen=True)
class Arm:
    name: str
    agent: str  # "random" or "openai_tool"
    model: str = "gpt-6-luna"
    max_actions_per_level: int = 400
    use_win_cache: bool = False
    temperature: float | None = None


ARMS: dict[str, Arm] = {
    arm.name: arm
    for arm in (
        Arm("random", "random"),
        Arm("tool_baseline", "openai_tool", max_actions_per_level=100),
        Arm("tool_weak", "openai_tool", max_actions_per_level=5),
    )
}


def build_agent(arm: Arm, seed: int, workdir: Path) -> BaseAgent:
    if arm.agent == "random":
        return RandomAgent(seed=seed)
    if arm.agent == "openai_tool":
        cache_path = None if arm.use_win_cache else workdir / "win_paths.json"
        return OpenAIToolAgent(
            model=arm.model,
            cache_path=cache_path,
            seed=seed,
            temperature=arm.temperature,
        )
    raise ValueError(f"Unknown agent key '{arm.agent}' for arm '{arm.name}'")


def validate_games(games: Sequence[str]) -> list[str]:
    for game in games:
        if game.startswith(EXCLUDED_GAME_PREFIXES):
            raise ValueError(
                f"Game '{game}' is excluded from comparisons "
                "(ls20 is covered by the hardcoded win-path cache)"
            )
    return list(games)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_experiments_arms.py -v`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add src/experiments/arms.py tests/test_experiments_arms.py
git commit -m "feat(experiments): arms registry, agent factory and ls20 guard"
```

---

### Task 5: Resumable runner and CLI

**Files:**
- Create: `src/experiments/runner.py`
- Test: `tests/test_experiments_runner.py`

**Interfaces:**
- Consumes: `Arm`, `build_agent`, `validate_games`, `ARMS`, `PILOT_GAMES` (Task 4); `RunRecord`, `append_record`, `load_records` (Task 2); `GameEvalSummary` and `EvaluationRunner` from `src.evaluate` (existing; `run_game(agent, game_prefix) -> GameEvalSummary` with `.score`, `.levels_completed`, `.total_actions`; attribute `max_actions_per_level`).
- Produces:
  - `run_arm(arm: Arm, games: Sequence[str], seeds: Sequence[int], results_path: Path | str, evaluator: Evaluator) -> list[RunRecord]`: runs every (seed, game) not already in the results file, appends one record per run, and returns only the new records. An exception from a run is recorded as a failed record. It sets `evaluator.max_actions_per_level = arm.max_actions_per_level` first.
  - `resolve_games(csv: str) -> list[str]`: splits a comma-separated list and applies `validate_games`.
  - `main()`: CLI `python3 -m src.experiments.runner --arm tool_baseline --seeds 3 [--games a,b,c] [--results PATH]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_experiments_runner.py
import pytest

from src.evaluate import GameEvalSummary
from src.experiments.arms import ARMS
from src.experiments.records import load_records
from src.experiments.runner import resolve_games, run_arm


class FakeEvaluator:
    def __init__(self, fail_on: tuple[str, ...] = ()) -> None:
        self.max_actions_per_level = 0
        self.calls: list[tuple[str, int]] = []
        self.fail_on = set(fail_on)

    def run_game(self, agent, game_prefix):
        self.calls.append((game_prefix, self.max_actions_per_level))
        if game_prefix in self.fail_on:
            raise RuntimeError("boom")
        return GameEvalSummary(
            game_id=f"{game_prefix}-x", levels_completed=1, total_actions=7, score=12.5
        )


def test_run_arm_writes_one_record_per_game_and_seed(tmp_path):
    path = tmp_path / "r.jsonl"
    evaluator = FakeEvaluator()
    new = run_arm(ARMS["random"], ["g0", "g1"], [0, 1], path, evaluator)
    assert len(new) == 4
    assert len(load_records(path)) == 4
    assert {r.key for r in new} == {
        ("random", g, s) for g in ("g0", "g1") for s in (0, 1)
    }
    assert evaluator.max_actions_per_level == ARMS["random"].max_actions_per_level


def test_run_arm_resumes_and_skips_existing_runs(tmp_path):
    path = tmp_path / "r.jsonl"
    run_arm(ARMS["random"], ["g0", "g1"], [0], path, FakeEvaluator())
    evaluator = FakeEvaluator()
    new = run_arm(ARMS["random"], ["g0", "g1"], [0, 1], path, evaluator)
    assert [call[0] for call in evaluator.calls] == ["g0", "g1"]
    assert {r.seed for r in new} == {1}
    assert len(load_records(path)) == 4


def test_failed_run_is_recorded_with_error_and_not_retried(tmp_path):
    path = tmp_path / "r.jsonl"
    run_arm(ARMS["random"], ["g0", "g1"], [0], path, FakeEvaluator(fail_on=("g1",)))
    records = {r.game: r for r in load_records(path)}
    assert records["g0"].ok is True
    assert records["g1"].ok is False
    assert "RuntimeError: boom" in records["g1"].error
    evaluator = FakeEvaluator()
    run_arm(ARMS["random"], ["g0", "g1"], [0], path, evaluator)
    assert evaluator.calls == []


def test_resolve_games_rejects_ls20():
    with pytest.raises(ValueError, match="ls20"):
        resolve_games("ar25,ls20")


def test_resolve_games_splits_and_strips():
    assert resolve_games("ar25, cd82") == ["ar25", "cd82"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_experiments_runner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.experiments.runner'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/experiments/runner.py
from __future__ import annotations

import argparse
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from src.agents import BaseAgent
from src.config import OOF_DIR
from src.evaluate import EvaluationRunner, GameEvalSummary
from src.experiments.arms import ARMS, PILOT_GAMES, Arm, build_agent, validate_games
from src.experiments.records import RunRecord, append_record, load_records

DEFAULT_RESULTS = OOF_DIR / "experiments" / "results.jsonl"


class Evaluator(Protocol):
    max_actions_per_level: int

    def run_game(self, agent: BaseAgent, game_prefix: str) -> GameEvalSummary: ...


def run_arm(
    arm: Arm,
    games: Sequence[str],
    seeds: Sequence[int],
    results_path: Path | str,
    evaluator: Evaluator,
) -> list[RunRecord]:
    """Run every (seed, game) not already in the results file; return the new records."""
    done = {rec.key for rec in load_records(results_path)}
    evaluator.max_actions_per_level = arm.max_actions_per_level
    new: list[RunRecord] = []
    with tempfile.TemporaryDirectory() as tmp:
        for seed in seeds:
            for game in games:
                if (arm.name, game, seed) in done:
                    continue
                try:
                    agent = build_agent(arm, seed, Path(tmp) / f"{game}-{seed}")
                    summary = evaluator.run_game(agent, game)
                    record = RunRecord(
                        arm.name,
                        game,
                        seed,
                        summary.score,
                        summary.levels_completed,
                        summary.total_actions,
                    )
                except Exception as exc:  # noqa: BLE001 - a failed run is data, not a crash
                    record = RunRecord(
                        arm.name, game, seed, 0.0, 0, 0, f"{type(exc).__name__}: {exc}"
                    )
                append_record(results_path, record)
                new.append(record)
    return new


def resolve_games(csv: str) -> list[str]:
    return validate_games([game.strip() for game in csv.split(",") if game.strip()])


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an experiment arm over games and seeds")
    parser.add_argument("--arm", choices=sorted(ARMS), required=True)
    parser.add_argument("--games", default=",".join(PILOT_GAMES))
    parser.add_argument("--seeds", type=int, default=3, help="number of seeds (0..N-1)")
    parser.add_argument("--results", default=str(DEFAULT_RESULTS))
    args = parser.parse_args()

    arm = ARMS[args.arm]
    games = resolve_games(args.games)
    evaluator = EvaluationRunner(max_actions_per_level=arm.max_actions_per_level)
    new = run_arm(arm, games, list(range(args.seeds)), args.results, evaluator)
    failed = sum(1 for rec in new if not rec.ok)
    print(f"{arm.name}: {len(new)} new runs, {failed} failed -> {args.results}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_experiments_runner.py -v`
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add src/experiments/runner.py tests/test_experiments_runner.py
git commit -m "feat(experiments): resumable arm runner and CLI"
```

---

### Task 6: Report table and ledger row

**Files:**
- Create: `src/experiments/report.py`
- Test: `tests/test_experiments_report.py`

**Interfaces:**
- Consumes: `RunRecord`, `load_records` (Task 2); `Verdict`, `suite_means`, `noise_floor`, `verdict` (Task 3); `DOCS_DIR`, `OOF_DIR` from `src.config`.
- Produces:
  - `render_table(records: Sequence[RunRecord], baseline: str, candidates: Sequence[str]) -> str`
  - `ledger_row(records: Sequence[RunRecord], baseline: str, candidate: str, today: str) -> str`: one line in the existing 8-column `docs/experiments.md` layout, ending with a newline and containing no extra `|` characters.
  - `append_ledger_row(row: str, ledger_path: Path | str = DOCS_DIR / "experiments.md") -> None`: no-op if the ledger does not exist.
  - `main()`: CLI `python3 -m src.experiments.report --baseline tool_baseline --candidate tool_weak [--results PATH] [--log-ledger]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_experiments_report.py
import random

from src.experiments.records import RunRecord
from src.experiments.report import append_ledger_row, ledger_row, render_table

GAMES = [f"g{i}" for i in range(8)]


def rec(arm, game, seed, score, error=None):
    return RunRecord(arm, game, seed, score, 1, 10, error)


def synthetic(effect, seeds=3):
    rng = random.Random(0)
    out = []
    for gi, game in enumerate(GAMES):
        base_mean = 10.0 + 5.0 * gi
        for seed in range(seeds):
            out.append(rec("base", game, seed, base_mean + rng.gauss(0, 2.0)))
            out.append(rec("cand", game, seed, base_mean + effect + rng.gauss(0, 2.0)))
    return out


def test_table_shows_verdict_and_both_arms():
    table = render_table(synthetic(effect=10.0), "base", ["cand"])
    assert "base" in table
    assert "cand" in table
    assert "better" in table


def test_table_reports_insufficient_data_with_one_seed():
    table = render_table(synthetic(effect=10.0, seeds=1), "base", ["cand"])
    assert "insufficient data" in table


def test_table_counts_failed_runs():
    records = synthetic(effect=10.0)
    records.append(rec("cand", "g_extra", 0, 0.0, error="RuntimeError: boom"))
    lines = render_table(records, "base", ["cand"]).splitlines()
    cand_line = next(line for line in lines if line.startswith("cand"))
    assert cand_line.split("|")[3].strip() == "1"


def test_ledger_row_has_eight_columns():
    row = ledger_row(synthetic(effect=10.0), "base", "cand", "2026-10-29")
    assert row.endswith("|\n")
    assert row.strip().count("|") == 9
    assert "better" in row
    assert "`ab-cand-vs-base-2026-10-29`" in row


def test_append_ledger_row_noops_when_ledger_missing(tmp_path):
    append_ledger_row("| x |\n", tmp_path / "missing.md")
    assert not (tmp_path / "missing.md").exists()


def test_append_ledger_row_appends(tmp_path):
    ledger = tmp_path / "experiments.md"
    ledger.write_text("header\n", encoding="utf-8")
    append_ledger_row("| row |\n", ledger)
    assert ledger.read_text(encoding="utf-8") == "header\n| row |\n"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_experiments_report.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.experiments.report'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/experiments/report.py
from __future__ import annotations

import argparse
import datetime
from collections.abc import Sequence
from pathlib import Path

from src.config import DOCS_DIR
from src.experiments.records import RunRecord, load_records
from src.experiments.runner import DEFAULT_RESULTS
from src.experiments.stats import noise_floor, suite_means, verdict


def _mean_score(records: Sequence[RunRecord], arm: str) -> float | None:
    means = list(suite_means(records, arm).values())
    return sum(means) / len(means) if means else None


def render_table(records: Sequence[RunRecord], baseline: str, candidates: Sequence[str]) -> str:
    header = (
        f"{'Arm':<18} | {'Mean (%)':>9} | {'Seeds':>5} | {'Failed':>6} | "
        f"{'Delta':>8} | {'90% CI':<18} | Verdict"
    )
    lines = [header, "-" * len(header)]
    for arm in [baseline, *candidates]:
        mean = _mean_score(records, arm)
        mean_text = "n/a" if mean is None else f"{mean:.2f}"
        seeds = len(suite_means(records, arm))
        failed = sum(1 for rec in records if rec.arm == arm and not rec.ok)
        if arm == baseline:
            floor = noise_floor(records, baseline)
            floor_text = "n/a" if floor is None else f"{floor:.2f}"
            delta, interval, label = "-", "-", f"baseline (noise floor {floor_text})"
        else:
            result = verdict(records, baseline, arm)
            delta = f"{result.mean_diff:+.2f}"
            interval = f"[{result.ci_low:.2f}, {result.ci_high:.2f}]"
            label = result.label
        lines.append(
            f"{arm:<18} | {mean_text:>9} | {seeds:>5} | {failed:>6} | "
            f"{delta:>8} | {interval:<18} | {label}"
        )
    return "\n".join(lines)


def ledger_row(
    records: Sequence[RunRecord], baseline: str, candidate: str, today: str
) -> str:
    result = verdict(records, baseline, candidate)
    mean = _mean_score(records, candidate)
    mean_text = "n/a" if mean is None else f"{mean:.2f}%"
    ok_runs = [rec for rec in records if rec.arm == candidate and rec.ok]
    levels = sum(rec.levels_completed for rec in ok_runs)
    actions = sum(rec.total_actions for rec in ok_runs)
    notes = (
        f"{result.label}: delta {result.mean_diff:+.2f}, "
        f"90% CI [{result.ci_low:.2f}, {result.ci_high:.2f}], "
        f"noise floor {result.noise_floor:.2f}."
    )
    return (
        f"| `ab-{candidate}-vs-{baseline}-{today}` | {today} | "
        f"A/B {candidate} vs {baseline} ({result.n_pairs} paired runs) | "
        f"{mean_text} | {levels} | {actions} | - | {notes} |\n"
    )


def append_ledger_row(row: str, ledger_path: Path | str = DOCS_DIR / "experiments.md") -> None:
    target = Path(ledger_path)
    if not target.exists():
        return
    with open(target, "a", encoding="utf-8") as handle:
        handle.write(row)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare experiment arms against a baseline")
    parser.add_argument("--results", default=str(DEFAULT_RESULTS))
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", nargs="+", required=True)
    parser.add_argument("--log-ledger", action="store_true")
    args = parser.parse_args()

    records = load_records(args.results)
    print(render_table(records, args.baseline, args.candidate))
    if args.log_ledger:
        today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
        for candidate in args.candidate:
            append_ledger_row(ledger_row(records, args.baseline, candidate, today))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_experiments_report.py -v`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add src/experiments/report.py tests/test_experiments_report.py
git commit -m "feat(experiments): comparison table and ledger row"
```

---

### Task 7: End-to-end check, full suite, and pilot runbook

**Files:**
- Test: `tests/test_experiments_end_to_end.py`
- Modify: `docs/HANDOVER.md` (add a short "Experiment harness" section under "Testing & Verification Commands")

**Interfaces:**
- Consumes: everything above. Uses the real `ARMS` (`tool_baseline`, `tool_weak`), a copy of the baseline arm under another name, and a fake evaluator whose score depends on the action cap and on the agent's seed.
- Produces: confidence that the success criteria in the spec hold, plus the documented commands for the pilot.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_experiments_end_to_end.py
import dataclasses
import random

from src.evaluate import GameEvalSummary
from src.experiments.arms import ARMS, PILOT_GAMES
from src.experiments.records import load_records
from src.experiments.runner import run_arm
from src.experiments.stats import verdict


class CapDependentEvaluator:
    """Score grows with the action cap; noise depends only on (game, seed)."""

    def __init__(self) -> None:
        self.max_actions_per_level = 0

    def run_game(self, agent, game_prefix):
        noise = random.Random(f"{game_prefix}-{agent.seed}").gauss(0.0, 2.0)
        score = max(0.0, min(self.max_actions_per_level, 50) * 0.8 + noise)
        return GameEvalSummary(game_id=game_prefix, levels_completed=1, total_actions=5, score=score)


def _run_all(tmp_path):
    path = tmp_path / "r.jsonl"
    evaluator = CapDependentEvaluator()
    copy_arm = dataclasses.replace(ARMS["tool_baseline"], name="tool_baseline_copy")
    for arm in (ARMS["tool_baseline"], copy_arm, ARMS["tool_weak"]):
        run_arm(arm, list(PILOT_GAMES), [0, 1, 2], path, evaluator)
    return load_records(path)


def test_weakened_arm_is_identified_as_worse(tmp_path):
    records = _run_all(tmp_path)
    assert verdict(records, "tool_baseline", "tool_weak").label == "worse"
    assert verdict(records, "tool_weak", "tool_baseline").label == "better"


def test_identical_arms_report_no_difference(tmp_path):
    records = _run_all(tmp_path)
    assert verdict(records, "tool_baseline", "tool_baseline_copy").label == "no difference"
```

- [ ] **Step 2: Run test to verify it fails or passes for the right reason**

Run: `python3 -m pytest tests/test_experiments_end_to_end.py -v`
Expected: PASS if Tasks 1-6 are correct. If a test fails, fix the earlier task whose behavior is wrong (do not weaken this test).

- [ ] **Step 3: Run the full suite and lint on the new files**

Run: `python3 -m pytest tests/ -q`
Expected: all pass (128 original tests plus the new ones).

Run: `ruff check src/experiments tests/test_experiments_records.py tests/test_experiments_stats.py tests/test_experiments_arms.py tests/test_experiments_runner.py tests/test_experiments_report.py tests/test_experiments_end_to_end.py tests/test_openai_tool_agent_sampling.py`
Expected: no findings. Fix any that appear (`ruff check --fix` handles import ordering); do not touch unrelated files.

- [ ] **Step 4: Document the commands in `docs/HANDOVER.md`**

Append this block at the end of the "Testing & Verification Commands" section:

````markdown
### Experiment harness (noise-aware A/B)

```bash
# Run an arm over the 8 pilot games, 3 seeds (spends OpenAI API budget)
python3 -m src.experiments.runner --arm tool_baseline --seeds 3

# Compare candidate arms against the baseline and log the result to docs/experiments.md
python3 -m src.experiments.report --baseline tool_baseline --candidate tool_weak --log-ledger
```

Results append to `oof/experiments/results.jsonl` and runs resume if interrupted. A change is only promoted
to a Kaggle submission when its verdict is `better`.
````

- [ ] **Step 5: Commit**

```bash
git add tests/test_experiments_end_to_end.py docs/HANDOVER.md
git commit -m "test(experiments): end-to-end verdict check and harness runbook"
```

- [ ] **Step 6: Pilot run (requires user approval before running)**

This step spends OpenAI API budget and needs `OPENAI_API_KEY` in `.env`. Ask the user to approve before running it. Then:

```bash
python3 -m src.experiments.runner --arm tool_baseline --seeds 3
python3 -m src.experiments.report --baseline tool_baseline --candidate tool_baseline
```

Record in `docs/experiments.md`: cost per run, the baseline noise floor, whether `seed` visibly changes the baseline's behavior (compare per-seed suite means), and the number of failed runs. If the noise floor is too wide to be useful at 8 games and 3 seeds, adjust `PILOT_GAMES` or the seed count in a follow-up change before comparing any candidate.
