# Phase 1: Local Evaluation Runner, Baseline Benchmarking & Submission Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a robust offline evaluation runner for the 25 ARC-AGI-3 public environments, integrate and benchmark Random and Stochastic Goose baseline agents, and establish an automated Kaggle submission packaging pipeline.

**Architecture:** Use the official `arc_agi.Arcade` execution engine in offline mode against `input/environment_files/`, execute agents implementing a standard `BaseAgent` contract, score trajectories using the exact `src/metrics.py` formula, export standalone self-contained Kaggle submission notebooks via `src/package_submission.py`, and log results to `docs/experiments.md`.

**Tech Stack:** Python 3.12, `arc_agi` 0.9.8, `arcengine` 0.1.0, PyTorch, Pytest, Ruff.

**Spec:** `docs/superpowers/specs/2026-10-01-phase-1-eval-runner-baseline-design.md`

## Global Constraints

- Python >= 3.10 required across all scripts and agents.
- All code must pass `ruff check .` with line length 100.
- All metrics and evaluations must use `src/metrics.py` as the single source of truth.
- Offline execution must load games from `input/environment_files/` with `OPERATION_MODE=offline`.
- Submissions must support `KAGGLE_IS_COMPETITION_RERUN` gateway (`http://gateway:8001/`) and provide a dummy `submission.parquet` fallback on non-rerun edit mode.

## Review Focus

1. **Coordinate action handling:** `ACTION6` requires `(x, y)` coordinates; agents or runners that treat `ACTION6` as a bare action or crash on coordinate inputs must be guarded.
2. **Action budget exhaustion:** Runaway exploration in `RandomAgent` or untrained policies must be terminated by `max_actions` without throwing exceptions or leaving open scorecards.
3. **Empty / No-op games:** If an agent immediately calls `is_done()` or errors out on level 0, the game score must gracefully evaluate to 0.0 without divide-by-zero errors.
4. **Offline scorecard lifecycle:** If a simulation run crashes midway, the scorecard must still close properly to prevent leaking stale sessions.
5. **Notebook self-containment:** Generated submission notebooks must embed the agent source verbatim without importing from `src/` so they execute independently on Kaggle.

---

### Task 1: Unified Agent Base Interface & Registry

**Files:**
- Create: `src/agents/base.py`
- Create: `src/agents/__init__.py`
- Test: `tests/test_agents.py`

**Interfaces:**
- Consumes: `arcengine.FrameData`, `arcengine.GameAction`, `arcengine.GameState`
- Produces: `BaseAgent` class with abstract `choose_action()`, default `is_done()`, and `reset()`; `AVAILABLE_AGENTS` registry dict in `src/agents/__init__.py`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_agents.py
from arcengine import FrameData, GameAction, GameState
import pytest
from src.agents.base import BaseAgent


class DummyAgent(BaseAgent):
    def choose_action(self, frames: list[FrameData], latest_frame: FrameData) -> GameAction:
        return GameAction.ACTION1


def test_base_agent_interface():
    agent = DummyAgent()
    frame = FrameData(state=GameState.NOT_FINISHED, levels_completed=0, available_actions=[1, 2])
    assert not agent.is_done([], frame)
    assert agent.choose_action([], frame) == GameAction.ACTION1

    win_frame = FrameData(state=GameState.WIN, levels_completed=1, available_actions=[1, 2])
    assert agent.is_done([], win_frame)

    over_frame = FrameData(state=GameState.GAME_OVER, levels_completed=0, available_actions=[1, 2])
    assert agent.is_done([], over_frame)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_agents.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.agents.base'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/agents/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence
from arcengine import FrameData, GameAction, GameState


class BaseAgent(ABC):
    """Abstract base class for all ARC-AGI-3 agents."""

    @abstractmethod
    def choose_action(
        self,
        frames: Sequence[FrameData],
        latest_frame: FrameData,
    ) -> GameAction | tuple[GameAction, tuple[int, int]]:
        """Choose the next action given frame history and latest frame."""
        pass

    def is_done(
        self,
        frames: Sequence[FrameData],
        latest_frame: FrameData,
    ) -> bool:
        """Return True if agent should terminate play for this environment."""
        return latest_frame.state in (GameState.WIN, GameState.GAME_OVER)

    def reset(self) -> None:
        """Reset internal episodic state between games."""
        pass
```

```python
# src/agents/__init__.py
from typing import Type
from src.agents.base import BaseAgent

AVAILABLE_AGENTS: dict[str, Type[BaseAgent]] = {}

__all__ = ["BaseAgent", "AVAILABLE_AGENTS"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_agents.py -v`
Expected: PASS

---

### Task 2: Random Agent Implementation

**Files:**
- Create: `src/agents/random_agent.py`
- Modify: `src/agents/__init__.py`
- Test: `tests/test_agents.py`

**Interfaces:**
- Consumes: `BaseAgent`, `arcengine.GameAction`, `arcengine.FrameData`
- Produces: `RandomAgent` registered as `"random"` in `AVAILABLE_AGENTS`.

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_agents.py
from src.agents.random_agent import RandomAgent
from src.agents import AVAILABLE_AGENTS


def test_random_agent_action_selection():
    agent = RandomAgent(seed=42)
    frame = FrameData(
        state=GameState.NOT_FINISHED,
        levels_completed=0,
        available_actions=[1, 2, 3],
    )
    action = agent.choose_action([], frame)
    assert action in (GameAction.ACTION1, GameAction.ACTION2, GameAction.ACTION3)


def test_random_agent_action6_coordinates():
    agent = RandomAgent(seed=42)
    # Available action is only ACTION6 (integer 6)
    frame = FrameData(
        state=GameState.NOT_FINISHED,
        levels_completed=0,
        available_actions=[6],
    )
    action = agent.choose_action([], frame)
    # Expect either GameAction or (GameAction, (x, y))
    assert action == GameAction.ACTION6 or (isinstance(action, tuple) and action[0] == GameAction.ACTION6)


def test_random_agent_registered():
    assert "random" in AVAILABLE_AGENTS
    assert AVAILABLE_AGENTS["random"] is RandomAgent
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_agents.py -k "test_random_agent" -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.agents.random_agent'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/agents/random_agent.py
from __future__ import annotations

import random
from typing import Sequence
from arcengine import FrameData, GameAction
from src.agents.base import BaseAgent


class RandomAgent(BaseAgent):
    """Uniformly samples from available actions with coordinate generation for ACTION6."""

    def __init__(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed)

    def choose_action(
        self,
        frames: Sequence[FrameData],
        latest_frame: FrameData,
    ) -> GameAction:
        available = latest_frame.available_actions
        if not available:
            return GameAction.RESET

        action_int = self.rng.choice(available)
        action = GameAction(action_int)

        if action == GameAction.ACTION6:
            # Generate valid grid coordinates (default 64x64 bounds)
            # arcengine supports action.coordinates or raw GameAction.ACTION6
            x = self.rng.randint(0, 63)
            y = self.rng.randint(0, 63)
            action.coordinates = (x, y)

        return action
```

```python
# Modify src/agents/__init__.py
from typing import Type
from src.agents.base import BaseAgent
from src.agents.random_agent import RandomAgent

AVAILABLE_AGENTS: dict[str, Type[BaseAgent]] = {
    "random": RandomAgent,
}

__all__ = ["BaseAgent", "RandomAgent", "AVAILABLE_AGENTS"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_agents.py -v`
Expected: PASS (4 passed)

---

### Task 3: Offline Evaluation Engine (`src/evaluate.py`)

**Files:**
- Create: `src/evaluate.py`
- Test: `tests/test_evaluate.py`

**Interfaces:**
- Consumes: `arc_agi.Arcade`, `src.config.ENVIRONMENTS_DIR`, `src.metrics.compute_game_score`, `src.metrics.compute_competition_score`, `src.agents.AVAILABLE_AGENTS`
- Produces: `EvaluationRunner` class and `main()` CLI entrypoint.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_evaluate.py
import pytest
from src.evaluate import EvaluationRunner
from src.agents.random_agent import RandomAgent


def test_evaluation_runner_single_game():
    runner = EvaluationRunner(max_actions_per_level=10)
    agent = RandomAgent(seed=42)
    # Run against public game 'ls20'
    summary = runner.run_game(agent=agent, game_prefix="ls20")
    assert summary.game_id.startswith("ls20")
    assert summary.total_actions > 0
    assert summary.score >= 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_evaluate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.evaluate'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/evaluate.py
from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

from src.agents import AVAILABLE_AGENTS, BaseAgent
from src.config import ENVIRONMENTS_DIR, PUBLIC_GAMES
from src.metrics import compute_competition_score, compute_game_score

logger = logging.getLogger("evaluate")


@dataclass
class GameEvalSummary:
    game_id: str
    levels_completed: int
    total_actions: int
    score: float
    level_outcomes: list[tuple[int, int, bool]] = field(default_factory=list)


@dataclass
class SuiteEvalSummary:
    agent_name: str
    total_score: float
    total_levels_completed: int
    total_actions: int
    game_summaries: list[GameEvalSummary] = field(default_factory=list)


class EvaluationRunner:
    def __init__(
        self,
        environments_dir: Path | str = ENVIRONMENTS_DIR,
        max_actions_per_level: int = 400,
    ) -> None:
        self.environments_dir = str(environments_dir)
        self.max_actions_per_level = max_actions_per_level
        self.arcade = Arcade(
            operation_mode=OperationMode.OFFLINE,
            environments_dir=self.environments_dir,
        )

    def _resolve_game_id(self, game_prefix: str) -> str:
        envs = self.arcade.get_environments()
        for env in envs:
            if env.game_id.startswith(game_prefix):
                return env.game_id
        raise ValueError(f"Game prefix '{game_prefix}' not found in {self.environments_dir}")

    def run_game(self, agent: BaseAgent, game_prefix: str) -> GameEvalSummary:
        agent.reset()
        full_game_id = self._resolve_game_id(game_prefix)
        card_id = self.arcade.open_scorecard()

        try:
            env = self.arcade.make(full_game_id, scorecard_id=card_id)
            if env is None:
                raise RuntimeError(f"Failed to create environment for {full_game_id}")

            frame = env.reset()
            frames = [frame]
            action_count = 0
            level_action_count = 0

            while not agent.is_done(frames, frame):
                action = agent.choose_action(frames, frame)
                frame = env.step(action)
                frames.append(frame)
                action_count += 1
                level_action_count += 1

                if frame.state in (GameState.WIN, GameState.GAME_OVER):
                    break

                if level_action_count >= self.max_actions_per_level:
                    break

            scorecard = self.arcade.close_scorecard(card_id)
        except Exception:
            self.arcade.close_scorecard(card_id)
            raise

        # Extract levels outcome from scorecard
        env_score_list = scorecard.find_environment(game_prefix) if scorecard else None
        level_outcomes: list[tuple[int, int, bool]] = []
        score = 0.0
        levels_completed = 0

        if env_score_list and env_score_list.runs:
            best_run = max(env_score_list.runs, key=lambda r: r.score)
            score = best_run.score
            levels_completed = best_run.levels_completed
            actions = best_run.level_actions or []
            baselines = best_run.level_baseline_actions or []
            scores = best_run.level_scores or []
            for a, b, s in zip(actions, baselines, scores):
                level_outcomes.append((b, a, s > 0.0))
        else:
            score = 0.0

        return GameEvalSummary(
            game_id=full_game_id,
            levels_completed=levels_completed,
            total_actions=action_count,
            score=score,
            level_outcomes=level_outcomes,
        )

    def run_suite(
        self,
        agent: BaseAgent,
        agent_name: str,
        games: Sequence[str],
    ) -> SuiteEvalSummary:
        summaries: list[GameEvalSummary] = []
        for game in games:
            summary = self.run_game(agent, game)
            summaries.append(summary)

        game_scores = [s.score for s in summaries]
        total_score = compute_competition_score(game_scores)
        total_levels = sum(s.levels_completed for s in summaries)
        total_actions = sum(s.total_actions for s in summaries)

        return SuiteEvalSummary(
            agent_name=agent_name,
            total_score=total_score,
            total_levels_completed=total_levels,
            total_actions=total_actions,
            game_summaries=summaries,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="ARC-AGI-3 Local Evaluation Runner")
    parser.add_argument(
        "--agent",
        choices=AVAILABLE_AGENTS.keys(),
        default="random",
        help="Agent identifier to evaluate",
    )
    parser.add_argument(
        "--games",
        type=str,
        default="ls20,ar25,dc22",
        help="Comma-separated game prefixes or '--all' for 25 public games",
    )
    parser.add_argument(
        "--max-actions",
        type=int,
        default=400,
        help="Max action count per level before termination",
    )
    parser.add_argument(
        "--log-ledger",
        action="store_true",
        help="Log experiment results into docs/experiments.md",
    )

    args = parser.parse_args()

    target_games = PUBLIC_GAMES if args.games.strip() == "--all" else [g.strip() for g in args.games.split(",")]
    agent_cls = AVAILABLE_AGENTS[args.agent]
    agent = agent_cls()

    runner = EvaluationRunner(max_actions_per_level=args.max_actions)
    print(f"\n🎮 Evaluating Agent '{args.agent}' across {len(target_games)} game(s)...")

    suite_summary = runner.run_suite(agent=agent, agent_name=args.agent, games=target_games)

    print("\n" + "=" * 65)
    print(f"{'Game ID':<20} | {'Levels':<8} | {'Actions':<8} | {'Score (%)':<10}")
    print("-" * 65)
    for g in suite_summary.game_summaries:
        print(f"{g.game_id:<20} | {g.levels_completed:<8} | {g.total_actions:<8} | {g.score:<10.2f}")
    print("=" * 65)
    print(f"Overall Competition Score: {suite_summary.total_score:.2f}%")
    print(f"Total Levels Cleared:      {suite_summary.total_levels_completed}")
    print(f"Total Actions Taken:       {suite_summary.total_actions}\n")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_evaluate.py -v`
Expected: PASS

---

### Task 4: Stochastic Goose CNN Baseline Agent

**Files:**
- Create: `src/agents/stochastic_goose.py`
- Modify: `src/agents/__init__.py`
- Test: `tests/test_agents.py`

**Interfaces:**
- Consumes: `BaseAgent`, PyTorch (`torch`, `torch.nn`), `arcengine.FrameData`, `arcengine.GameAction`
- Produces: `StochasticGoose` registered as `"stochastic_goose"` in `AVAILABLE_AGENTS`.

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_agents.py
from src.agents.stochastic_goose import StochasticGoose


def test_stochastic_goose_initialization():
    agent = StochasticGoose()
    frame = FrameData(
        state=GameState.NOT_FINISHED,
        levels_completed=0,
        available_actions=[1, 2, 3, 4],
    )
    action = agent.choose_action([], frame)
    assert action in (
        GameAction.ACTION1,
        GameAction.ACTION2,
        GameAction.ACTION3,
        GameAction.ACTION4,
    )


def test_stochastic_goose_registered():
    assert "stochastic_goose" in AVAILABLE_AGENTS
    assert AVAILABLE_AGENTS["stochastic_goose"] is StochasticGoose
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_agents.py -k "test_stochastic_goose" -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.agents.stochastic_goose'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/agents/stochastic_goose.py
from __future__ import annotations

import random
from typing import Sequence
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from arcengine import FrameData, GameAction
from src.agents.base import BaseAgent


class PolicyCNN(nn.Module):
    """Compact ConvNet mapping grid observations (16 colors) to action distributions."""

    def __init__(self, num_actions: int = 7) -> None:
        super().__init__()
        # Input: 16 channels (one-hot color states 0-15) over 64x64 grid
        self.conv1 = nn.Conv2d(16, 32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1)  # 32x32
        self.conv3 = nn.Conv2d(64, 64, kernel_size=3, stride=2, padding=1)  # 16x16
        self.pool = nn.AdaptiveAvgPool2d((4, 4))
        self.fc = nn.Linear(64 * 4 * 4, num_actions)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = F.relu(self.conv1(x))
        h = F.relu(self.conv2(h))
        h = F.relu(self.conv3(h))
        h = self.pool(h)
        h = h.view(h.size(0), -1)
        return self.fc(h)


class StochasticGoose(BaseAgent):
    """Tufa Labs Milestone 1 CNN action learner."""

    def __init__(self, epsilon: float = 0.2, seed: int = 42) -> None:
        self.rng = random.Random(seed)
        self.epsilon = epsilon
        self.device = torch.device(
            "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self.policy = PolicyCNN(num_actions=7).to(self.device)
        self.policy.eval()

    def _encode_grid(self, frame: FrameData) -> torch.Tensor:
        grid = np.zeros((64, 64), dtype=np.int64)
        if frame.frame and len(frame.frame) > 0:
            raw = frame.frame[0]
            if isinstance(raw, list) and len(raw) > 0 and isinstance(raw[0], list):
                h = min(len(raw), 64)
                w = min(len(raw[0]), 64)
                grid[:h, :w] = np.array(raw)[:h, :w]

        # One-hot encode 16 color channels: shape (1, 16, 64, 64)
        tensor_grid = torch.from_numpy(grid).long()
        one_hot = F.one_hot(tensor_grid, num_classes=16).permute(2, 0, 1).unsqueeze(0).float()
        return one_hot.to(self.device)

    def choose_action(
        self,
        frames: Sequence[FrameData],
        latest_frame: FrameData,
    ) -> GameAction:
        available = latest_frame.available_actions
        if not available:
            return GameAction.RESET

        # Epsilon-greedy exploration
        if self.rng.random() < self.epsilon:
            action_int = self.rng.choice(available)
        else:
            with torch.no_grad():
                x = self._encode_grid(latest_frame)
                logits = self.policy(x).squeeze(0).cpu().numpy()

                # Mask unavailable actions
                masked_logits = np.full_like(logits, -1e9)
                for act_id in available:
                    # arcengine action integers 1-7 map to 0-6
                    idx = act_id - 1
                    if 0 <= idx < len(logits):
                        masked_logits[idx] = logits[idx]

                action_int = int(np.argmax(masked_logits)) + 1

        action = GameAction(action_int)
        if action == GameAction.ACTION6:
            action.coordinates = (self.rng.randint(0, 63), self.rng.randint(0, 63))

        return action
```

```python
# Modify src/agents/__init__.py
from typing import Type
from src.agents.base import BaseAgent
from src.agents.random_agent import RandomAgent
from src.agents.stochastic_goose import StochasticGoose

AVAILABLE_AGENTS: dict[str, Type[BaseAgent]] = {
    "random": RandomAgent,
    "stochastic_goose": StochasticGoose,
}

__all__ = ["BaseAgent", "RandomAgent", "StochasticGoose", "AVAILABLE_AGENTS"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_agents.py -v`
Expected: PASS (6 passed)

---

### Task 5: Automated Submission Packaging (`src/package_submission.py`)

**Files:**
- Create: `src/package_submission.py`
- Test: `tests/test_package_submission.py`

**Interfaces:**
- Consumes: Agent source code from `src/agents/`, `src.config.SUBMISSION_DIR`
- Produces: `submissions/submission_<agent_name>.ipynb` with 4 complete cells.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_package_submission.py
import json
from pathlib import Path
import pytest
from src.package_submission import package_agent_submission


def test_package_submission_creates_valid_notebook(tmp_path: Path):
    output_path = tmp_path / "submission_random.ipynb"
    package_agent_submission(agent_name="random", output_path=output_path)

    assert output_path.exists()
    with open(output_path) as f:
        nb = json.load(f)

    assert "cells" in nb
    assert len(nb["cells"]) == 4
    # Cell 0: pip install wheels
    assert "pip install" in "".join(nb["cells"][0]["source"])
    # Cell 1: agent code inlined
    assert "RandomAgent" in "".join(nb["cells"][1]["source"])
    # Cell 2: gateway rerun logic
    assert "KAGGLE_IS_COMPETITION_RERUN" in "".join(nb["cells"][2]["source"])
    # Cell 3: dummy parquet
    assert "submission.parquet" in "".join(nb["cells"][3]["source"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_package_submission.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.package_submission'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/package_submission.py
from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path

from src.agents import AVAILABLE_AGENTS
from src.config import SUBMISSION_DIR


def package_agent_submission(agent_name: str, output_path: Path | str) -> Path:
    if agent_name not in AVAILABLE_AGENTS:
        raise ValueError(f"Unknown agent '{agent_name}'. Available: {list(AVAILABLE_AGENTS.keys())}")

    agent_cls = AVAILABLE_AGENTS[agent_name]
    agent_source = inspect.getsource(agent_cls)
    agent_module = inspect.getmodule(agent_cls)
    module_source = inspect.getsource(agent_module) if agent_module else agent_source

    cell_0_wheels = (
        "!pip install --no-index --find-links \\\n"
        "    /kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels \\\n"
        "    arc-agi python-dotenv\n"
    )

    cell_1_agent = f"%%writefile /kaggle/working/my_agent.py\n{module_source}\n"

    cell_2_rerun = """import os

if os.getenv('KAGGLE_IS_COMPETITION_RERUN'):
    # Wait for gateway to be ready
    !curl --fail --retry 999 --retry-all-errors --retry-delay 5 \\
          --retry-max-time 600 http://gateway:8001/api/games

    # Copy official framework to writable location
    !cp -r /kaggle/input/competitions/arc-prize-2026-arc-agi-3/ARC-AGI-3-Agents \\
           /kaggle/working/ARC-AGI-3-Agents

    # Copy custom agent into templates
    !cp /kaggle/working/my_agent.py \\
        /kaggle/working/ARC-AGI-3-Agents/agents/templates/my_agent.py

    # Minimal init with custom agent registration
    with open('/kaggle/working/ARC-AGI-3-Agents/agents/__init__.py', 'w') as f:
        f.write('''from typing import Type
from dotenv import load_dotenv
from .agent import Agent, Playback
from .swarm import Swarm
from .templates.random_agent import Random
from .templates.my_agent import MyAgent

load_dotenv()

AVAILABLE_AGENTS: dict[str, Type[Agent]] = {
    "random": Random,
    "myagent": MyAgent,
}
''')

    # Environment overrides for gateway
    with open('/kaggle/working/ARC-AGI-3-Agents/.env', 'w') as f:
        f.write('''SCHEME=http
HOST=gateway
PORT=8001
ARC_API_KEY=competition-key
ARC_BASE_URL=http://gateway:8001/
OPERATION_MODE=online
ENVIRONMENTS_DIR=
RECORDINGS_DIR=/kaggle/working/server_recording
''')

    # Run agent against all 110 games
    !cd /kaggle/working/ARC-AGI-3-Agents && \\
        MPLBACKEND=agg \\
        python main.py --agent myagent
"""

    cell_3_dummy = """import os
if not os.getenv('KAGGLE_IS_COMPETITION_RERUN'):
    # Interactive / non-rerun commit mode dummy fallback
    import pandas as pd
    submission = pd.DataFrame(
        data=[['1_0', '1', True, 1]],
        columns=['row_id', 'game_id', 'end_of_game', 'score'])
    submission.to_parquet('/kaggle/working/submission.parquet', index=False)
    print("Dummy submission saved successfully for commit validation.")
"""

    notebook_dict = {
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.10.0"},
        },
        "nbformat": 4,
        "nbformat_minor": 4,
        "cells": [
            {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": cell_0_wheels},
            {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": cell_1_agent},
            {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": cell_2_rerun},
            {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": cell_3_dummy},
        ],
    }

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(notebook_dict, f, indent=2)

    return out_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Package ARC-AGI-3 Agent for Kaggle Submission")
    parser.add_argument(
        "--agent",
        choices=AVAILABLE_AGENTS.keys(),
        default="stochastic_goose",
        help="Agent name to package",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Target notebook destination path",
    )
    args = parser.parse_args()

    dest = Path(args.output) if args.output else SUBMISSION_DIR / f"submission_{args.agent}.ipynb"
    path = package_agent_submission(agent_name=args.agent, output_path=dest)
    print(f"✅ Packaged submission notebook generated at: {path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_package_submission.py -v`
Expected: PASS

---

### Task 6: Smoke Test Execution & Experiment Ledger Verification

**Files:**
- Modify: `docs/experiments.md`
- Verify: Run smoke tests and packaging via CLI

- [ ] **Step 1: Execute evaluation runner on smoke subset for Random and Stochastic Goose**

Run:
```bash
python3 -m src.evaluate --agent random --games ls20,ar25,dc22
python3 -m src.evaluate --agent stochastic_goose --games ls20,ar25,dc22
```
Expected: Both agents complete evaluation without crashes, displaying per-game action counts and scores.

- [ ] **Step 2: Generate submission notebook package**

Run:
```bash
python3 -m src.package_submission --agent stochastic_goose
```
Expected: Output created at `submissions/submission_stochastic_goose.ipynb`.

- [ ] **Step 3: Update `docs/experiments.md` with verified baseline scores**

Record the smoke test metrics into the ledger.

- [ ] **Step 4: Run full test suite to guarantee 100% clean status**

Run: `python3 -m pytest tests/ -v`
Expected: All tests pass.
