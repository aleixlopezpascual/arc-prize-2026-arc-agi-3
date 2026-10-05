# Design Document: Duck V4 Architecture (Perception Primitives & Zero-Prompt-Drift Solved Memory)

**Date:** 2026-10-05  
**Author:** Aleix López  
**Status:** Approved for Implementation Planning  
**Target:** ARC Prize 2026 (ARC-AGI-3) — Push score from 30.19% toward 35%+ (Top 50 Global)

---

## 1. Context & Motivation

On October 5, 2026, **Duck Centroid V1** achieved an official competition score of **`30.19%`** on the unseen 110-game test set (Ref `56836213`, Global Rank #152). Duck Centroid V1 succeeded because of two surgical innovations:
1. Object bounding boxes (`bbox`) and geometric centers (`centroid`) added to `segmentation.py`.
2. Static documentation in `prompts.py` guiding Qwen 3.8 Flash-Next to target clicks (`ACTION6`) at exact object centers.

An intermediate experiment, **Duck Memory V3**, attempted to introduce cross-level memory and baseline pacing, but experienced a score collapse down to 26.11% on 10 demo games. Root-cause analysis of the logs revealed two critical findings:
1. **Silent Analyzer Crash:** `tool_agent.py` attempted to access `self.game.base_actions_per_level`, but `self` was `ToolAgent`, which had no `game` attribute. This caused an unhandled `AttributeError` that terminated all 10 demo games prematurely as `state=crashed`.
2. **Dynamic Prefix Cache Invalidation:** Injecting dynamic text (`"Knowledge from cleared levels: ..."`) into `_build_user_prompt` across level transitions invalidated SGLang's RadixAttention KV cache, degrading generation throughput.

### The Duck V4 Mandate
Duck V4 addresses these lessons directly by providing high-leverage perception primitives and cross-level memory **entirely inside the Python tool sandbox**, while keeping the system prompt and user prompt templates **100% byte-static** to preserve >93% KV-cache hit rate and 0% crash risk.

---

## 2. Architectural Design

```
                      [SGLang Engine (Qwen 3.8 Flash-Next)]
                                        │
           Static System Prompt Prefix  │  Byte-Static Prompt Templates
           (Documents candidate_clicks, │  (>93% RadixAttention KV Cache Hit)
            object_at, & solved_memory) │
                                        ▼
                             [ToolAgent Dispatch]
                                        │
           Passes `solved_memory` via   │  Python Code Execution
           JSON payload to Sandbox      │  (Ephemerally initialized)
                                        ▼
                        [Python Tool Sandbox Process]
     ┌──────────────────────────────────┴──────────────────────────────────┐
     ▼                                                                     ▼
[Perception Primitives]                                           [Cross-Level Memory]
• candidate_clicks(color, exclude_border)                         • current_frame.solved_memory
• object_at(row, col)                                             • global `solved_memory`
• Enhanced segmentation: `bbox`, `centroid`, `is_border`          (Cleared level action history,
                                                                   winning actions, level stats)
```

### Invariants
1. **Prompt Invariance:** Neither the system prompt nor `_build_user_prompt` will receive dynamic level-dependent text strings. Prompts remain 100% static across all levels of all games.
2. **Defensive Runtime Contract:** All sandbox helper functions handle empty objects, missing keys, and invalid inputs gracefully without throwing uncaught exceptions.
3. **Session Isolation:** Cleared level memory resets automatically between distinct games.

---

## 3. Detailed Component Specifications

### 3.1. Segmentation Enhancements (`segmentation.py`)
In `_segment_layer(grid, color_chars)`:
- Continue computing `bbox: [min_r, min_c, max_r, max_c]` and `centroid: [r_c, c_c]`.
- Add `is_border: bool` detection:
  ```python
  H, W = len(grid), len(grid[0]) if grid else 0
  is_border = (
      (min_r == 0 and max_r == 0 and len(cells) >= W * 0.75) or
      (min_r == H - 1 and max_r == H - 1 and len(cells) >= W * 0.75) or
      (min_c == 0 and max_c == 0 and len(cells) >= H * 0.75) or
      (min_c == W - 1 and max_c == W - 1 and len(cells) >= H * 0.75)
  )
  ```
- Each segmented node includes: `id`, `color`, `hash`, `rotation`, `rotational_symmetry`, `pose_hash`, `shape_hash`, `pixels`, `bbox`, `centroid`, `is_border`, `boundary`, `children`.

### 3.2. Sandbox Perception Helpers (`python_tool_sandbox.py`)
In `_SANDBOX_BOOTSTRAP`:
- **`object_at(row, col, frame=None)`**:
  - Arguments: `row: int`, `col: int`, `frame: FrameView | None = None`.
  - Resolution: Default `target_frame = frame if frame is not None else runtime_globals.get("current_frame")`.
  - Logic: Finds the object node whose `bbox` encloses `[row, col]` and contains `(row, col)` in its cell coordinates or boundary, or where `target_frame._grid[row][col]` matches node color. Returns the `node` dictionary or `None`.
- **`candidate_clicks(color=None, min_size=1, max_size=None, exclude_border=True, frame=None)`**:
  - Arguments:
    - `color: str | None`: Optional ARC color character filter.
    - `min_size: int`: Minimum pixel count (default 1).
    - `max_size: int | None`: Maximum pixel count (default None).
    - `exclude_border: bool`: Exclude boundary/HUD objects (default True).
    - `frame: FrameView | None`: Optional frame reference.
  - Returns: List of dictionaries sorted by pixel count descending:
    ```python
    [
        {
            "id": node["id"],
            "color": node["color"],
            "centroid": node["centroid"],
            "bbox": node["bbox"],
            "pixels": node["pixels"],
        },
        ...
    ]
    ```

### 3.3. Cross-Level Solved Memory (`tool_agent.py` & `python_tool_sandbox.py`)
- In `ToolAgent.__init__`:
  - `self._cleared_level_memories: list[dict[str, Any]] = []`
- In `ToolAgent._ensure_session`:
  - On new session / new game, reset `self._cleared_level_memories.clear()`.
- On action execution when `action_result.get("level_completed")`:
  - Record:
    ```python
    completed_level = max(1, int(summary.get("level") or 2) - 1)
    last_acts = summary.get("executed_actions") or []
    self._cleared_level_memories.append({
        "level": completed_level,
        "actions_taken": summary.get("executed_count", len(last_acts)),
        "winning_actions": [str(a) for a in last_acts[-5:]] if last_acts else [],
    })
    ```
- In `_serialized_runtime_state()`:
  - Add `"solved_memory": list(self._cleared_level_memories)` to the returned payload dictionary.
- In `python_tool_sandbox.py`:
  - Inside `FrameView`: `self.solved_memory = list(payload.get("solved_memory") or [])`.
  - In `_refresh_state()`:
    - `runtime_globals["solved_memory"] = list(state_payload.get("solved_memory") or [])`.

### 3.4. Static System Prompt Updates (`prompts.py`)
Add to `STRUCTURED_RUNTIME_STATE_ADDENDUM` in `prompts.py`:
```python
"- `candidate_clicks(color=None, min_size=1, max_size=None, exclude_border=True)` returns candidate click targets with their `centroid` [row, col], `bbox`, and `color`."
"- `object_at(row, col)` returns the segmented object node covering cell `(row, col)`, or `None`."
"- `current_frame.solved_memory` (also available as `solved_memory`) is a list of summaries from completed levels in this game: `[{'level': ..., 'actions_taken': ..., 'winning_actions': [...]}, ...]`. Core object mechanics and action patterns from earlier levels often carry forward."
```
Note: `_build_user_prompt` remains completely untouched.

---

## 4. Verification & Testing Plan

1. **Local Unit Tests:**
   - Create `tests/test_duck_v4_primitives.py` verifying:
     - `_segment_layer` correctly sets `is_border` on outer frames and `False` on interior puzzle pieces.
     - `candidate_clicks` filters by color, size, and border correctly.
     - `object_at` returns the correct node or `None` on boundary/empty inputs.
     - `solved_memory` serialization round-trips without data loss.
   - Run existing test suite (`pytest tests/`) ensuring 100% pass (37+ tests).
2. **Kernel Packaging Verification:**
   - Create `submissions/duck_v4/` containing `notebook.ipynb` and `kernel-metadata.json`.
   - Implement `apply_enhancements_v4.py` in Cell 3 applying the patches.
   - Validate that patching executes cleanly against local `taaf_source` without syntax or assertion errors.
3. **Kaggle GPU Demo Validation:**
   - Push `aleixlopez/arc-agi-3-duck-v4` to Kaggle GPU in demo mode (`TRUE_SUBMISSION = False`).
   - Confirm 0 crashes (`state != crashed` for all 10 games).
   - Verify mean score exceeds Duck Centroid V1 benchmark (>= 46.72%).
4. **Production Submission:**
   - Toggle `TRUE_SUBMISSION = True` and queue for daily competition submission.
