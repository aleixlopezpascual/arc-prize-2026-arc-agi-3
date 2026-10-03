# Phase 4: PerceptionSearchAgent & Centroid Specialist Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Click-Centroid Specialist to extract intelligent click coordinates from segmented objects, and build the `PerceptionSearchAgent` uniting perception, guards, and search into a single decision loop.

**Architecture:** Pure Python & NumPy modules in `src/perception/centroids.py` and `src/agents/search_agent.py`. Candidate actions combine simple actions with prioritized click-centroids, filtered through `NoopRepeatGuard` and scored via visual heuristics.

**Tech Stack:** Python 3.12, NumPy, arcengine, Pytest, Ruff.

**Spec:** `docs/superpowers/specs/2026-10-01-phase-4-search-agent-design.md`

## Global Constraints

- Python >= 3.10.
- All code must pass `ruff check .` with line length 100.
- Coordinate clicks (`ACTION6`) must produce valid `(row, col)` coordinates inside `[0, 63]`.
- All newly added components must have comprehensive unit tests adhering to TDD.

## Review Focus

1. **Background Area Threshold:** Objects covering $\ge 40\%$ of the board must not produce click centroids (filtering out the board itself).
2. **Centroid Ordering Priority:** Compact objects (likely interactive switches/tokens) must precede large sprawling components in candidate lists.
3. **Empty / Blank Grids:** A grid with no non-background objects must return the board center `(H//2, W//2)` as a safe fallback.
4. **Agent Registration:** `PerceptionSearchAgent` must be registered in `src/agents/AVAILABLE_AGENTS` as `"perception_search"` and be selectable via `--agent perception_search` in `src/evaluate.py`.
5. **Noop Guard Synchronization:** The agent must notify `NoopRepeatGuard` on each step to maintain the live dead-end ledger.

---

### Task 1: Click-Centroid Specialist (`src/perception/centroids.py`)

**Files:**
- Create: `src/perception/centroids.py`
- Modify: `src/perception/__init__.py`
- Test: `tests/test_centroids.py`

**Interfaces:**
- Consumes: `segment_grid` from `src.perception.segmentation`
- Produces: `extract_candidate_clicks(grid: Sequence[Sequence[int]] | np.ndarray, background_color: int | None = 0, max_candidates: int = 8) -> list[tuple[int, int]]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_centroids.py
import pytest
from src.perception.centroids import extract_candidate_clicks


def test_extract_candidate_clicks_basic():
    # 10x10 grid with background 0, small 2x2 square at rows 2-3, cols 2-3 (color 1),
    # and a 1x1 dot at row 7, col 8 (color 2)
    grid = [[0] * 10 for _ in range(10)]
    grid[2][2] = 1
    grid[2][3] = 1
    grid[3][2] = 1
    grid[3][3] = 1
    grid[7][8] = 2

    candidates = extract_candidate_clicks(grid, background_color=0, max_candidates=5)
    assert len(candidates) >= 2
    # Dot (1 pixel) is more compact, should be first
    assert candidates[0] == (7, 8)
    # Square centroid: row = 2 or 3, col = 2 or 3
    assert candidates[1] in [(2, 2), (2, 3), (3, 2), (3, 3)]


def test_extract_candidate_clicks_filters_large_background():
    # 10x10 grid where 60% of cells are color 4 (massive background) and 1 dot of color 5
    grid = [[4 if r < 6 else 0 for _ in range(10)] for r in range(10)]
    grid[8][8] = 5

    candidates = extract_candidate_clicks(grid, background_color=0)
    assert len(candidates) >= 1
    # Dot must be present
    assert (8, 8) in candidates
    # The massive color 4 area (>40% of grid) should NOT dominate
    assert candidates[0] == (8, 8)


def test_extract_candidate_clicks_fallback():
    # Blank 8x8 grid
    grid = [[0] * 8 for _ in range(8)]
    candidates = extract_candidate_clicks(grid, background_color=0)
    assert candidates == [(4, 4)]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_centroids.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/perception/centroids.py
from __future__ import annotations

from collections.abc import Sequence
import numpy as np

from src.perception.segmentation import segment_grid


def extract_candidate_clicks(
    grid: Sequence[Sequence[int]] | np.ndarray,
    background_color: int | None = 0,
    max_candidates: int = 8,
) -> list[tuple[int, int]]:
    arr = np.asarray(grid)
    if arr.ndim != 2 or arr.size == 0:
        return [(0, 0)]

    h, w = arr.shape
    total_pixels = h * w
    nodes = segment_grid(arr, background_color=background_color)

    # Filter out massive objects covering >= 40% of the entire grid
    valid_nodes = [n for n in nodes if n["pixels"] < 0.4 * total_pixels]

    if not valid_nodes:
        # Fallback to board center
        return [(h // 2, w // 2)]

    # Sort: smaller/more compact objects first (high probability of being tokens/buttons)
    valid_nodes.sort(key=lambda n: (n["pixels"], n["bbox"][0]))

    candidates: list[tuple[int, int]] = []
    seen = set()

    for node in valid_nodes:
        cells = node["cells"]
        # Integer centroid
        r_c = int(round(sum(r for r, _ in cells) / len(cells)))
        c_c = int(round(sum(c for _, c in cells) / len(cells)))
        # Clamp to grid bounds
        r_c = max(0, min(h - 1, r_c))
        c_c = max(0, min(w - 1, c_c))

        point = (r_c, c_c)
        if point not in seen:
            seen.add(point)
            candidates.append(point)
            if len(candidates) >= max_candidates:
                break

    if not candidates:
        candidates.append((h // 2, w // 2))

    return candidates
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_centroids.py -v`
Expected: PASS

---

### Task 2: PerceptionSearchAgent Implementation

**Files:**
- Create: `src/agents/search_agent.py`
- Modify: `src/agents/__init__.py`
- Test: `tests/test_search_agent.py`

**Interfaces:**
- Consumes: `BaseAgent`, `SearchAwareAgent`, `NoopRepeatGuard`, `extract_candidate_clicks`
- Produces: `PerceptionSearchAgent` registered in `AVAILABLE_AGENTS` as `"perception_search"`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_search_agent.py
import pytest
from arcengine import FrameData, GameAction, GameState

from src.agents import AVAILABLE_AGENTS
from src.agents.search_agent import PerceptionSearchAgent


def test_search_agent_registered():
    assert "perception_search" in AVAILABLE_AGENTS
    assert AVAILABLE_AGENTS["perception_search"] is PerceptionSearchAgent


def test_search_agent_action6_with_centroids():
    agent = PerceptionSearchAgent(seed=42)
    # Frame with ACTION6 available and a 5x5 grid containing a clickable dot
    grid = [[0] * 5 for _ in range(5)]
    grid[1][2] = 3

    frame = FrameData(
        state=GameState.NOT_FINISHED,
        levels_completed=0,
        available_actions=[6],
        frame=[grid],
    )
    action = agent.choose_action([], frame)
    assert action == GameAction.ACTION6
    assert hasattr(action, "action_data")
    assert action.action_data.x == 1
    assert action.action_data.y == 2


def test_search_agent_simple_actions():
    agent = PerceptionSearchAgent(seed=42)
    frame = FrameData(
        state=GameState.NOT_FINISHED,
        levels_completed=0,
        available_actions=[1, 2],
        frame=[[[0, 0], [0, 0]]],
    )
    action = agent.choose_action([], frame)
    assert action in (GameAction.ACTION1, GameAction.ACTION2)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_search_agent.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/agents/search_agent.py
from __future__ import annotations

import random
from collections.abc import Sequence

from arcengine import FrameData, GameAction

from src.agents.base import BaseAgent
from src.guards.noop_repeat_guard import NoopRepeatGuard, compute_interior_hash
from src.perception.centroids import extract_candidate_clicks
from src.search.action_selector import SearchAwareAgent


class PerceptionSearchAgent(BaseAgent, SearchAwareAgent):
    """Search-guided agent combining object centroid clicks and no-op pruning."""

    def __init__(self, seed: int | None = None, epsilon: float = 0.1) -> None:
        super().__init__(evaluator=None)
        self.rng = random.Random(seed)
        self.epsilon = epsilon
        self.guard = NoopRepeatGuard()
        self.current_level = 0

    def reset(self) -> None:
        self.guard.note_level(0)
        self.current_level = 0

    def choose_action(
        self,
        frames: Sequence[FrameData],
        latest_frame: FrameData,
    ) -> GameAction:
        available = latest_frame.available_actions
        if not available:
            return GameAction.RESET

        if latest_frame.levels_completed != self.current_level:
            self.current_level = latest_frame.levels_completed
            self.guard.note_level(self.current_level)

        grid = latest_frame.frame[0] if latest_frame.frame and len(latest_frame.frame) > 0 else []
        state_hash = compute_interior_hash(grid)

        # Build candidate action pool
        candidates: list[GameAction] = []

        for act_int in available:
            if act_int == 6:
                # ACTION6: generate coordinate clicks from segmented centroids
                clicks = extract_candidate_clicks(grid, max_candidates=6)
                for r, c in clicks:
                    act = GameAction.from_id(6)
                    act.set_data({"x": r, "y": c, "game_id": latest_frame.game_id})
                    candidates.append(act)
            else:
                candidates.append(GameAction.from_id(act_int))

        # Filter out candidates blocked by NoopRepeatGuard
        unblocked = [
            c for c in candidates if not self.guard.should_block(state_hash, c.name if c != GameAction.ACTION6 else f"ACTION6({c.action_data.x},{c.action_data.y})")
        ]

        active_pool = unblocked if unblocked else candidates

        if self.rng.random() < self.epsilon or len(active_pool) == 1:
            chosen = self.rng.choice(active_pool)
        else:
            # Prefer ACTION6 clicks over random simple actions when objects exist
            click_actions = [a for a in active_pool if a == GameAction.ACTION6]
            if click_actions and self.rng.random() < 0.6:
                chosen = self.rng.choice(click_actions)
            else:
                chosen = self.rng.choice(active_pool)

        return chosen
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_search_agent.py -v`
Expected: PASS

---

### Task 3: Integration Verification & Regression Testing

**Files:**
- Modify: `src/perception/__init__.py`, `src/agents/__init__.py`
- Verify: Full pytest suite passes (`34+` tests) and `ruff check` is green.

- [ ] **Step 1: Run complete test suite**

Run: `python3 -m pytest tests/ -v`
Expected: 34+ passed

- [ ] **Step 2: Run ruff check**

Run: `python3 -m ruff check src/ tests/`
Expected: All checks passed!
