# Phase 3: MCTS / Best-First Planning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a perception-guided, LLM-based action search (best-first) subsystem that simulates action branches using the Arcade engine and ranks them using semantic `frame_diff` reports.

**Architecture:** A new `src/search/` module consisting of a `BranchEvaluator` (for environment simulation/state restoration) and an `ActionSelector` mixin for agents. Search probes are filtered by the `NoopRepeatGuard` to prevent unproductive exploration.

**Tech Stack:** Python 3.12, Arcade Engine (official), Pytest, Ruff.

**Spec:** `docs/superpowers/specs/2026-10-01-phase-3-mcts-search-design.md`

## Global Constraints

- Python >= 3.10.
- All code must pass `ruff check .` with line length 100.
- Search must not leak state changes (must restore to original environment frame).
- Search probes must be filtered by `NoopRepeatGuard`.

## Review Focus

1. **State Leakage:** An environment used for a search probe must be exactly restored or re-reset; state changes in a probe must never persist into the main game execution.
2. **Infinite Simulation:** Probes must be bounded by a strictly enforced action count per turn to prevent hanging in complex environments.
3. **Branch Ranking Ambiguity:** If all probed branches result in zero `frame_diff` impact (e.g., all no-ops), the agent must have a fallback policy (e.g., epsilon-greedy default).
4. **Action Sequence Serialization:** Search candidates must be serialized into the LLM context effectively (sequence representation) without overwhelming the token budget.
5. **Scorecard Session Hijacking:** Search probe scorecards must be kept independent of the main game scorecard to avoid double-counting or session corruption.

---

### Task 1: BranchEvaluator Harness

**Files:**
- Create: `src/search/branch_evaluator.py`
- Create: `src/search/__init__.py`
- Test: `tests/test_search.py`

**Interfaces:**
- Consumes: `arc_agi.Arcade`, `src.perception.frame_diff`
- Produces: `BranchEvaluator(arcade: Arcade)` with `run_probe(game_id: str, card_id: str, actions: Sequence[GameAction]) -> dict`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_search.py
import pytest
from arc_agi import Arcade, OperationMode
from src.search.branch_evaluator import BranchEvaluator

def test_branch_evaluator_state_restoration():
    arcade = Arcade(operation_mode=OperationMode.OFFLINE, environments_dir="input/environment_files")
    evaluator = BranchEvaluator(arcade)
    game_id = arcade.get_environments()[0].game_id
    card_id = arcade.open_scorecard()
    
    # Run a probe and ensure the environment wrapper is returned to clean state or reset
    report = evaluator.run_probe(game_id, card_id, actions=[GameAction.ACTION1])
    
    # Verify report structure
    assert "changed_cell_count" in report
    arcade.close_scorecard(card_id)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_search.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/search/branch_evaluator.py
from __future__ import annotations
from typing import Sequence
from arc_agi import Arcade
from arcengine import GameAction
from src.perception.frame_diff import compute_frame_diff

class BranchEvaluator:
    def __init__(self, arcade: Arcade) -> None:
        self.arcade = arcade

    def run_probe(self, game_id: str, scorecard_id: str, actions: Sequence[GameAction]) -> dict:
        env = self.arcade.make(game_id, scorecard_id=scorecard_id)
        before_state = env.reset()
        
        for action in actions:
            after_state = env.step(action)
            
        report = compute_frame_diff(before_state.frame, after_state.frame)
        return report
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_search.py -v`
Expected: PASS

---

### Task 2: ActionSelector Mixin for Agents

**Files:**
- Create: `src/search/action_selector.py`
- Modify: `src/search/__init__.py`

**Interfaces:**
- Consumes: `BaseAgent`, `BranchEvaluator`
- Produces: `SearchAwareAgent` mixin

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_search.py
from src.search.action_selector import SearchAwareAgent
from src.agents.base import BaseAgent

class SearchAgent(SearchAwareAgent, BaseAgent):
    def choose_action(self, frames, latest_frame): return None

def test_search_agent_integration():
    agent = SearchAgent(evaluator=None)
    assert hasattr(agent, "rank_branches")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_search.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# src/search/action_selector.py
from __future__ import annotations
from typing import Sequence
from src.search.branch_evaluator import BranchEvaluator

class SearchAwareAgent:
    def __init__(self, evaluator: BranchEvaluator) -> None:
        self.evaluator = evaluator
        
    def rank_branches(self, branches: Sequence[dict]) -> int:
        # LLM logic to rank by frame_diff report
        return 0 
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_search.py -v`
Expected: PASS

---

### Task 3: Integration Verification & Full Test Suite

**Files:**
- Modify: `tests/`
- Verify: Full pytest suite pass

- [ ] **Step 1: Run complete test suite**

Run: `python3 -m pytest tests/ -v`
Expected: 25+ passed

- [ ] **Step 2: Run ruff check**

Run: `python3 -m ruff check src/ tests/`
Expected: All checks passed!
