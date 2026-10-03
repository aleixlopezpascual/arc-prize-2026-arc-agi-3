# Phase 4 Design: PerceptionSearchAgent & Click-Centroid Specialist

- **Date:** 2026-10-01
- **Status:** Approved
- **Target Competition:** Kaggle `arc-prize-2026-arc-agi-3` (ARC Prize 2026 - ARC-AGI-3)

---

## 1. Executive Summary

Phase 4 bridges our perception layer (`segment_grid`, `compute_frame_diff`), action guards (`NoopRepeatGuard`), and search harness (`BranchEvaluator`, `SearchAwareAgent`) into a complete, autonomous agent: the **`PerceptionSearchAgent`**.

Additionally, it solves the **click-coordinate bottleneck** by introducing a **Click-Centroid Specialist** (`src/perception/centroids.py`), replacing uniform random coordinate sampling for `ACTION6` with geometrically grounded candidate points (object centroids, bounding-box centers, and interactable tokens).

---

## 2. System Architecture

```
arc-prize-2026-arc-agi-3/
├── src/
│   ├── perception/
│   │   ├── __init__.py           # Exports: segment_grid, compute_frame_diff, extract_candidate_clicks
│   │   ├── segmentation.py       # D4 rotation-canonical components
│   │   ├── frame_diff.py         # Semantic state diffing
│   │   └── centroids.py          # Click-centroid extraction for ACTION6
│   └── agents/
│       ├── __init__.py           # Registers 'perception_search'
│       ├── search_agent.py       # PerceptionSearchAgent implementation
│       └── ...
└── tests/
    ├── test_centroids.py         # Tests for centroid extraction & ordering
    └── test_search_agent.py      # Tests for PerceptionSearchAgent decision loop
```

---

## 3. Detailed Component Specifications

### 3.1. Click-Centroid Specialist (`src/perception/centroids.py`)
- **Input:** 2D grid ($H \times W$) and optional `background_color`.
- **Filtering & Prioritization:**
  - Segments grid using `segment_grid()`.
  - Filters out background objects covering $\ge 40\%$ of grid cells.
  - Computes centroid `(mean_row, mean_col)` for each object.
  - Sorts candidates: small/compact objects first (typical puzzle tokens/switches), then medium objects.
  - Adds board center `(H // 2, W // 2)` as a fallback point if no objects are detected.
- **Output:** List of `(row, col)` tuples capped at `max_candidates` (default: 8).

### 3.2. PerceptionSearchAgent (`src/agents/search_agent.py`)
- **Inheritance:** `BaseAgent`, `SearchAwareAgent`.
- **Decision Loop:**
  1. Inspects `latest_frame.available_actions`.
  2. If `ACTION6` is available, extracts candidate click coordinates from `extract_candidate_clicks()`.
  3. Constructs a candidate action pool:
     - Available simple actions (`ACTION1`..`ACTION5`, `ACTION7`).
     - Coordinate actions: `ACTION6(r, c)` for each candidate click.
  4. Prunes candidates using `NoopRepeatGuard.should_block(state_hash, action)`.
  5. Computes heuristic scores for candidate branches using internal visual heuristics and `rank_branches()`.
  6. Returns the top-ranked action; falls back to epsilon-greedy selection if all branches have zero score.

---

## 4. Testing & Verification Suite

- `tests/test_centroids.py`:
  - Verify centroid coordinates match known geometry for rectangles and L-shapes.
  - Verify massive background objects (>40% area) are filtered out.
  - Verify fallback to grid center on blank/empty grids.
- `tests/test_search_agent.py`:
  - Verify `PerceptionSearchAgent` is registered in `AVAILABLE_AGENTS`.
  - Verify `choose_action()` produces valid `GameAction` instances with correct coordinate data for `ACTION6`.
  - Verify the agent does not crash on empty frames or missing actions.
- Full regression test run: all 31 existing tests must continue to pass.
