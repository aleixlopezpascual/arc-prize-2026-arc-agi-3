# Phase 2 Foundation Design: Perception, Action Guards & Utility Subsystems

- **Date:** 2026-10-01
- **Status:** Approved
- **Target Competition:** Kaggle `arc-prize-2026-arc-agi-3` (ARC Prize 2026 - ARC-AGI-3)

---

## 1. Executive Summary

Following deep analysis of the Milestone 1 (Tufa Labs) and Milestone 2 (Daniel Franzen, 27.89% LB) winning architectures, this design establishes the foundational reasoning and perception layer for all future ARC-AGI-3 agents in our workspace.

The subsystem delivers four modular, high-performance components:
1. **Object Segmentation (`src/perception/segmentation.py`):** 4-connected component extraction with D4 rotation-canonical signatures, rotational symmetry order detection, and boundary contour extraction.
2. **Frame Difference Detection (`src/perception/frame_diff.py`):** Bipartite matching between consecutive board states, categorizing transitions into `moved`, `rotated`, `appeared`, `disappeared`, `changed_color`, and `resized`.
3. **No-op Repeat Guard (`src/guards/noop_repeat_guard.py`):** Border-cropped interior state hashing (immune to shrinking HUD timer bars) with overridable action blocking to eliminate wasted turns.
4. **Retained Functions Utility (`src/utils/retained_functions.py`):** AST-based function validation and namespace restoration, allowing Python-REPL agents to persist helper functions across turns without context overhead.

---

## 2. Component Specifications

### 2.1. Object Segmentation (`src/perception/segmentation.py`)
- **Input:** 2D grid of color integers ($H \times W$, values $0$–$15$).
- **Connected Components:** Groups adjacent cells sharing the same color into component dictionaries.
- **Rotation-Canonical D4 Signatures:**
  - Normalizes cell coordinates to origin `(min_row, min_col) = (0, 0)`.
  - Rotates normalized cells by $90^\circ$ clockwise across all 4 orientations ($0^\circ, 90^\circ, 180^\circ, 270^\circ$).
  - Computes sha1 hashes of each rotated variant and selects the lexicographically minimum hash as the canonical identity.
  - Determines clockwise rotation angle relative to canonical form ($0^\circ, 90^\circ, 180^\circ, 270^\circ$).
  - Detects symmetry order ($4$ for 4-fold rotational symmetry, $2$ for 2-fold, $1$ for asymmetric).
  - Computes color-independent shape hash allowing cross-color geometric matching.
- **Output:** List of `ObjectNode` structures containing:
  - `id`: Unique integer id per frame.
  - `color`: Integer color (or character code).
  - `canonical_hash`: Invariant shape+color identifier.
  - `shape_hash`: Color-free geometric shape hash.
  - `rotation`: Clockwise rotation degrees relative to canonical.
  - `rotational_symmetry`: Order of symmetry ($1, 2, 4$).
  - `bbox`: `[min_r, min_c, max_r, max_c]`.
  - `pixels`: Number of constituent cells.
  - `boundary`: Corner points tracing outer perimeter.

### 2.2. Frame Difference Detection (`src/perception/frame_diff.py`)
- **Input:** Two 2D grids (`before_grid`, `after_grid`) or lists of segmented object nodes.
- **Matching Algorithm:**
  - Identifies unchanged objects (identical coordinates and shape hash).
  - **Phase A (Color Changes):** Exact pair matching on same bounding box and shape hash but different color.
  - **Phase B (Resized Components):** Greedy bipartite matching of same-color objects with bounding-box intersection-over-smaller-area $\ge 0.5$.
  - **Motion & Rotation Classification:**
    - Objects with matching canonical shape and color but differing bounding box position are assigned to `moved`.
    - Objects with matching canonical shape but differing rotation angle are assigned to `rotated`.
    - Remaining unmatched components are categorized into `appeared` or `disappeared`.
- **Output:**
  ```python
  {
      "changed_cell_count": int,
      "moved": list[dict],
      "rotated": list[dict],
      "appeared": list[dict],
      "disappeared": list[dict],
      "changed_color": list[dict],
      "resized": list[dict],
  }
  ```

### 2.3. No-op Repeat Guard (`src/guards/noop_repeat_guard.py`)
- **Interior State Hash:** Hashes cells strictly inside a configurable border margin (default: 4 cells), filtering out outer HUD step/time budget bars that shrink deterministically.
- **Action Normalization:** Converts engine actions (`ACTION1`..`ACTION7`), model labels (`UP`, `DOWN`), and complex actions with coordinates (`ACTION6(row=X, col=Y)`) into normalized signatures.
- **Override Slot Mechanics:**
  - When `should_block(state_hash, action_sig)` detects a known no-op, it returns `True` and arms an override slot `(state_hash, action_sig)`.
  - If the agent immediately repeats the exact same action, the guard allows it to execute and clears the slot, ensuring no false-positive hardlocks on cooldown mechanics.
- **Lifecycle Management:** Automatically purges state tables upon level transitions (`note_level(level_idx)`).

### 2.4. Retained Functions Utility (`src/utils/retained_functions.py`)
- **AST Parsing (`prepare_functions`):**
  - Parses code snippets using Python's standard `ast` module.
  - Rejects functions modifying global variables, using decorators, or featuring non-literal default values.
  - Preserves explicit `import` and `from ... import ...` statements contained inside or preceding the function.
- **Namespace Restoration (`restore_functions`):**
  - Compiles and loads validated function definitions into clean execution scopes without carrying over state snapshots or mutable board structures.

---

## 3. Testing & Verification Suite

- `tests/test_segmentation.py`: Tests 4-connected components, rotation invariance (0, 90, 180, 270 deg), symmetry orders, and color-free shape matching.
- `tests/test_frame_diff.py`: Tests moved objects, rotated objects, color changes, and resizing detection.
- `tests/test_noop_guard.py`: Tests HUD border exclusion, no-op detection, and single-slot override execution.
- `tests/test_retained_funcs.py`: Tests valid function retention, rejection of globals/decorators, and clean namespace restoration.
