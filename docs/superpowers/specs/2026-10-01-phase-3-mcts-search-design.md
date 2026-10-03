# Phase 3 Design: MCTS / Best-First Planning with Perception-Guided Search

- **Date:** 2026-10-01
- **Status:** Approved
- **Target Competition:** Kaggle `arc-prize-2026-arc-agi-3` (ARC Prize 2026 - ARC-AGI-3)

---

## 1. Executive Summary

Phase 3 implements an LLM-guided, perception-aware search subsystem. Instead of simple reactive policy prediction, the agent will simulate short action sequences ("probes") and evaluate them using the perception modules implemented in Phase 2. This allows the agent to rank candidate branches based on immediate semantic feedback (e.g., "object moved," "line cleared") before committing to a move.

---

## 2. System Architecture

```
arc-prize-2026-arc-agi-3/
├── src/
│   ├── search/
│   │   ├── __init__.py           # Exports: BranchEvaluator, SearchAwareAgent
│   │   ├── branch_evaluator.py   # Harness for running offline action probes
│   │   └── action_selector.py    # LLM branch-ranking logic
├── tests/
│   ├── test_search.py            # Unit tests for branch simulation
│   └── test_search_integration.py# End-to-end integration with public environments
```

---

## 3. Detailed Component Specifications

### 3.1. Search-Aware Agent Contract (`src/search/action_selector.py`)
- **Integration:** Extends `BaseAgent` (or acts as a Mixin) to handle the lookahead logic.
- **`should_search(frame)`:** Heuristic to trigger search when complexity (actions available, board objects, or failure history) exceeds thresholds.
- **Loop:**
    1. **Branch Generation:** Agent proposes 3–5 candidate action *sequences* via prompt.
    2. **Probe Simulation:** `BranchEvaluator` steps the environment, capturing `FrameData` snapshots.
    3. **Perception Scoring:** `compute_frame_diff()` evaluates the semantic change.
    4. **Ranking:** Agent receives diff reports and selects the sequence maximizing the objective function (e.g., proximity to goal).

### 3.2. Evaluation Harness (`src/search/branch_evaluator.py`)
- **Lookahead Controller:** Safely forks or steps the environment forward.
- **State Recovery:** Ensures the original environment state is restored (via environment rollback or reset/replay) after the probe sequence completes, guaranteeing simulation side effects do not leak into the main episode.
- **Action Guard Integration:** Probes are filtered through `NoopRepeatGuard` to discard ineffective exploration branches before execution.

---

## 4. Testing & Verification Strategy

1. **Unit Tests (`tests/test_search.py`):**
   - Mocked Environment: Test `run_probe` restores environment state.
   - Verify `ActionSelector` correctly picks the best sequence based on mocked `frame_diff` rewards.
2. **Integration Test (`tests/test_search_integration.py`):**
   - Execute search-enabled `stochastic_goose` on a small subset of 3–5 public environments.
   - Verify that search agents produce higher or equal scores compared to the Phase 2 baseline.
3. **Verification Criterion:**
   - Must show improved score on public environments in `docs/experiments.md`.

---

## 5. Success Criteria

- Implementation of `BranchEvaluator` capable of offline sequences simulation.
- Successful integration of perception-based scoring into `StochasticGoose` agent decision-making.
- Improved baseline score on public environment games recorded in the experiment ledger.
