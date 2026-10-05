# Duck V4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify Duck V4 with in-sandbox perception primitives (`candidate_clicks`, `object_at`, `is_border`) and zero-prompt-drift solved memory (`current_frame.solved_memory`), keeping prompt prefixes 100% byte-static to preserve SGLang's >93% KV-cache hit rate.

**Architecture:** Extend segmentation with boundary/HUD detection (`is_border`), inject pure Python perception helpers (`object_at`, `candidate_clicks`) and cross-level memory (`solved_memory`) into `_SANDBOX_BOOTSTRAP` runtime globals, record level-clear events in `ToolAgent`, statically document these capabilities in `prompts.py`, and package as `submissions/duck_v4/`.

**Tech Stack:** Python 3.12, SGLang Pennyroyal v2.5.3, Qwen 3.8 Flash-Next, pytest, nbformat, Kaggle API.

**Spec:** `docs/superpowers/specs/2026-10-05-duck-v4-design.md`

## Global Constraints

- SGLang system prompt prefix and user prompt templates must remain **100% byte-identical** across levels (no dynamic prompt injections).
- All cross-level memory is transmitted exclusively via JSON runtime state payload into the sandbox environment.
- Defensive error handling: all sandbox helpers return `[]` or `None` on empty or invalid inputs; zero unhandled `AttributeError` or `IndexError` exceptions.
- Session isolation: memory is cleared between different game instances (`_cleared_level_memories.clear()`).
- All tests must pass locally via `pytest tests/` before deployment.

## Review Focus

1. **Border detection on single-cell or unusual grids:** A 1x1 grid or non-square grid must not cause division by zero or index out of range in `is_border`.
2. **Missing or None frame passed to candidate_clicks / object_at:** If `current_frame` is not yet bound or explicitly passed as `None`, helpers must return safe fallbacks (`[]` and `None`) rather than raising.
3. **Out-of-bounds coordinates passed to object_at:** Calling `object_at(-1, 999)` returns `None` without exception.
4. **Prompt prefix invariance check:** `_build_user_prompt` called on level 1 vs level 3 with identical actions must produce identical structural output with no memory strings appended.
5. **Memory serialization on game over:** If a level is reset due to game over or death, `_cleared_level_memories` preserves previously cleared levels and does not crash or erase prior verified progress.

---

### Task 1: Add `is_border` Detection to Segmentation

**Files:**
- Modify: `src/perception/segmentation.py`
- Test: `tests/test_duck_v4_segmentation.py`

**Interfaces:**
- Consumes: `_segment_layer(grid: Sequence[Sequence[str]], color_chars: str) -> dict[str, Any]`
- Produces: Each node dict in `segmentation["nodes"]` includes `'is_border': bool`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_duck_v4_segmentation.py`:
```python
import pytest
from src.perception.segmentation import segment_layer

def test_is_border_detection_outer_strip():
    # 10x10 grid with top row filled with 'B' (border/HUD bar) and center containing a 2x2 'R' object
    grid = [['.' for _ in range(10)] for _ in range(10)]
    for c in range(10):
        grid[0][c] = 'B'
    grid[4][4] = 'R'
    grid[4][5] = 'R'
    grid[5][4] = 'R'
    grid[5][5] = 'R'
    
    seg = segment_layer(grid, ".BR")
    nodes = seg["nodes"]
    
    border_node = next(n for n in nodes if n["color"] == 'B')
    center_node = next(n for n in nodes if n["color"] == 'R')
    
    assert border_node["is_border"] is True
    assert center_node["is_border"] is False

def test_is_border_small_or_empty_grid():
    # Defensive check on 1x1 grid
    grid = [['A']]
    seg = segment_layer(grid, "A")
    assert "is_border" in seg["nodes"][0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_duck_v4_segmentation.py -v`
Expected: FAIL with `KeyError: 'is_border'`

- [ ] **Step 3: Implement minimal code in `src/perception/segmentation.py`**

In `src/perception/segmentation.py`, update `_segment_layer`:
```python
        H, W = len(grid), len(grid[0]) if grid else 0
        min_r = min(r for r, _ in cells)
        max_r = max(r for r, _ in cells)
        min_c = min(c for _, c in cells)
        max_c = max(c for _, c in cells)
        r_c = round(sum(r for r, _ in cells) / len(cells))
        c_c = round(sum(c for _, c in cells) / len(cells))

        is_border = False
        if H > 0 and W > 0:
            is_border = bool(
                (min_r == 0 and max_r == 0 and len(cells) >= W * 0.75) or
                (min_r == H - 1 and max_r == H - 1 and len(cells) >= W * 0.75) or
                (min_c == 0 and max_c == 0 and len(cells) >= H * 0.75) or
                (min_c == W - 1 and max_c == W - 1 and len(cells) >= H * 0.75)
            )

        nodes.append(
            {
                "id": cid,
                "color": color,
                "hash": signature[0],
                "rotation": signature[1],
                "rotational_symmetry": signature[2],
                "pose_hash": signature[3],
                "shape_hash": signature[4],
                "pixels": len(cells),
                "bbox": [min_r, min_c, max_r, max_c],
                "centroid": [r_c, c_c],
                "is_border": is_border,
                "boundary": [[r, c] for r, c in boundary],
                "children": children[cid],
            }
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_duck_v4_segmentation.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/perception/segmentation.py tests/test_duck_v4_segmentation.py
git commit -m "feat: add is_border detection to segmentation nodes"
```

---

### Task 2: Implement Sandbox Perception Primitives (`candidate_clicks` & `object_at`)

**Files:**
- Create: `src/perception/sandbox_primitives.py`
- Test: `tests/test_sandbox_primitives.py`

**Interfaces:**
- Consumes: `segmentation['nodes']`
- Produces:
  - `candidate_clicks(nodes: list[dict], color: str | None = None, min_size: int = 1, max_size: int | None = None, exclude_border: bool = True) -> list[dict]`
  - `object_at(nodes: list[dict], row: int, col: int) -> dict | None`

- [ ] **Step 1: Write the failing test**

Create `tests/test_sandbox_primitives.py`:
```python
import pytest
from src.perception.sandbox_primitives import candidate_clicks, object_at

def test_candidate_clicks_filtering():
    nodes = [
        {"id": 0, "color": "B", "pixels": 10, "centroid": [0, 5], "bbox": [0, 0, 0, 9], "is_border": True},
        {"id": 1, "color": "R", "pixels": 4, "centroid": [5, 5], "bbox": [4, 4, 5, 5], "is_border": False},
        {"id": 2, "color": "G", "pixels": 1, "centroid": [2, 2], "bbox": [2, 2, 2, 2], "is_border": False},
    ]
    # By default, exclude_border drops B
    targets = candidate_clicks(nodes)
    assert len(targets) == 2
    assert targets[0]["id"] == 1
    assert targets[1]["id"] == 2

    # Filter by color
    r_targets = candidate_clicks(nodes, color="R")
    assert len(r_targets) == 1
    assert r_targets[0]["color"] == "R"

    # Filter by min_size
    large_targets = candidate_clicks(nodes, min_size=2)
    assert len(large_targets) == 1
    assert large_targets[0]["pixels"] == 4

def test_object_at_lookup():
    nodes = [
        {"id": 1, "color": "R", "pixels": 4, "bbox": [4, 4, 5, 5], "is_border": False},
    ]
    assert object_at(nodes, 4, 4)["id"] == 1
    assert object_at(nodes, 5, 5)["id"] == 1
    assert object_at(nodes, 6, 6) is None
    assert object_at(nodes, -1, 0) is None

def test_primitives_empty_or_none():
    assert candidate_clicks(None) == []
    assert candidate_clicks([]) == []
    assert object_at(None, 0, 0) is None
    assert object_at([], 0, 0) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_sandbox_primitives.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `src/perception/sandbox_primitives.py`**

```python
"""Perception primitives injected into the Python tool sandbox."""
from __future__ import annotations

from typing import Any


def candidate_clicks(
    nodes: list[dict[str, Any]] | None,
    color: str | None = None,
    min_size: int = 1,
    max_size: int | None = None,
    exclude_border: bool = True,
) -> list[dict[str, Any]]:
    """Return filtered, sorted candidate click targets from object nodes."""
    if not nodes:
        return []

    candidates: list[dict[str, Any]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if exclude_border and node.get("is_border", False):
            continue
        if color is not None and node.get("color") != color:
            continue
        pixels = int(node.get("pixels", 0))
        if pixels < min_size:
            continue
        if max_size is not None and pixels > max_size:
            continue

        centroid = node.get("centroid")
        bbox = node.get("bbox")
        candidates.append({
            "id": node.get("id"),
            "color": node.get("color"),
            "centroid": list(centroid) if centroid else None,
            "bbox": list(bbox) if bbox else None,
            "pixels": pixels,
        })

    # Sort largest objects first by default
    candidates.sort(key=lambda item: item["pixels"], reverse=True)
    return candidates


def object_at(
    nodes: list[dict[str, Any]] | None,
    row: int,
    col: int,
) -> dict[str, Any] | None:
    """Find the object node covering cell (row, col)."""
    if not nodes:
        return None

    for node in nodes:
        if not isinstance(node, dict):
            continue
        bbox = node.get("bbox")
        if not bbox or len(bbox) != 4:
            continue
        min_r, min_c, max_r, max_c = bbox
        if min_r <= row <= max_r and min_c <= col <= max_c:
            return dict(node)

    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_sandbox_primitives.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/perception/sandbox_primitives.py tests/test_sandbox_primitives.py
git commit -m "feat: add sandbox perception primitives candidate_clicks and object_at"
```

---

### Task 3: Implement Solved Memory Handling & State Serialization

**Files:**
- Create: `src/utils/solved_memory.py`
- Test: `tests/test_solved_memory.py`

**Interfaces:**
- Consumes: Action result dictionaries from step execution
- Produces: `SolvedMemoryManager` providing `record_level_cleared(level, actions_taken, winning_actions)`, `get_memory_payload()`, and `reset()`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_solved_memory.py`:
```python
import pytest
from src.utils.solved_memory import SolvedMemoryManager

def test_solved_memory_lifecycle():
    mem = SolvedMemoryManager()
    assert mem.get_memory_payload() == []

    # Record Level 1 clear
    mem.record_level_cleared(level=1, actions_taken=18, winning_actions=["UP", "UP", "SPACE"])
    payload = mem.get_memory_payload()
    assert len(payload) == 1
    assert payload[0]["level"] == 1
    assert payload[0]["actions_taken"] == 18
    assert payload[0]["winning_actions"] == ["UP", "UP", "SPACE"]

    # Record Level 2 clear
    mem.record_level_cleared(level=2, actions_taken=25, winning_actions=["ACTION6(10, 12)", "SPACE"])
    payload = mem.get_memory_payload()
    assert len(payload) == 2
    assert payload[1]["level"] == 2

    # Reset for next game
    mem.reset()
    assert mem.get_memory_payload() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_solved_memory.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `src/utils/solved_memory.py`**

```python
"""Manager for cross-level solved memory, serialized safely into the sandbox."""
from __future__ import annotations

from typing import Any


class SolvedMemoryManager:
    """Tracks cleared level mechanics and winning action patterns across levels."""

    def __init__(self) -> None:
        self._memories: list[dict[str, Any]] = []

    def record_level_cleared(
        self,
        *,
        level: int,
        actions_taken: int,
        winning_actions: list[str] | None = None,
    ) -> None:
        """Record the verified solution of a level."""
        self._memories.append({
            "level": int(level),
            "actions_taken": int(actions_taken),
            "winning_actions": [str(a) for a in (winning_actions or [])[-5:]],
        })

    def get_memory_payload(self) -> list[dict[str, Any]]:
        """Return JSON-safe copy of cleared level memories."""
        return [dict(m) for m in self._memories]

    def reset(self) -> None:
        """Clear memories when starting a new game."""
        self._memories.clear()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_solved_memory.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/utils/solved_memory.py tests/test_solved_memory.py
git commit -m "feat: add SolvedMemoryManager for cross-level runtime tracking"
```

---

### Task 4: Construct `apply_enhancements_v4.py` and Dry-Run Patch Verification

**Files:**
- Create: `submissions/duck_v4/apply_enhancements_v4.py`
- Test: `tests/test_duck_v4_patch.py`

**Interfaces:**
- Consumes: Local `taaf_source` repository tree (`input/taaf_source/src/ARC3-Inference`)
- Produces: Patched `segmentation.py`, `python_tool_sandbox.py`, `tool_agent.py`, `prompts.py`
- Invariant: Zero `AttributeError: 'ToolAgent' object has no attribute 'game'` and zero dynamic text in `_build_user_prompt`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_duck_v4_patch.py`:
```python
import pytest
from pathlib import Path
import tempfile
import shutil
import subprocess

def test_dry_run_enhancements_v4():
    source_root = Path("input/taaf_source/src/ARC3-Inference")
    assert source_root.exists(), "ARC3-Inference source must exist for patch test"

    with tempfile.TemporaryDirectory() as tmp_dir:
        dest_root = Path(tmp_dir) / "ARC3-Inference"
        shutil.copytree(source_root, dest_root)

        patch_script = Path("submissions/duck_v4/apply_enhancements_v4.py")
        assert patch_script.exists()

        # Run patch script
        res = subprocess.run(
            ["python3", str(patch_script.resolve()), str(Path(tmp_dir).resolve())],
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0, f"Patch failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"

        # Verify segmentation has is_border
        seg_code = (dest_root / "inference/utils/segmentation.py").read_text()
        assert "is_border" in seg_code
        assert "centroid" in seg_code
        assert "bbox" in seg_code

        # Verify python_tool_sandbox has candidate_clicks and object_at and solved_memory
        sandbox_code = (dest_root / "inference/agent/python_tool_sandbox.py").read_text()
        assert "def candidate_clicks" in sandbox_code
        assert "def object_at" in sandbox_code
        assert "solved_memory" in sandbox_code

        # Verify tool_agent records solved memory into runtime state WITHOUT prompt mutation
        agent_code = (dest_root / "inference/agent/tool_agent.py").read_text()
        assert "_cleared_level_memories" in agent_code
        assert "Knowledge from cleared levels:" not in agent_code  # MUST NOT BE IN PROMPTS!

        # Verify prompts.py documents candidate_clicks
        prompts_code = (dest_root / "inference/agent/prompts.py").read_text()
        assert "candidate_clicks" in prompts_code
        assert "object_at" in prompts_code
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_duck_v4_patch.py -v`
Expected: FAIL (file does not exist yet)

- [ ] **Step 3: Create `submissions/duck_v4/apply_enhancements_v4.py`**

Write the script that surgically applies all 4 Duck V4 components:
1. `segmentation.py`: Injects `bbox`, `centroid`, and `is_border`.
2. `prompts.py`: Documents `bbox`, `centroid`, `candidate_clicks`, `object_at`, and `solved_memory`.
3. `tool_agent.py`: Tracks `_cleared_level_memories` and adds `"solved_memory"` to `_serialized_runtime_state()` without any dynamic text in prompts.
4. `python_tool_sandbox.py`: Injects `candidate_clicks()`, `object_at()`, and `solved_memory` into the sandbox bootstrap.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_duck_v4_patch.py -v`
Expected: PASS with 0 errors.

- [ ] **Step 5: Commit**

```bash
git add submissions/duck_v4/apply_enhancements_v4.py tests/test_duck_v4_patch.py
git commit -m "feat: implement Duck V4 enhancement patch and dry-run validation"
```

---

### Task 5: Build `submissions/duck_v4/notebook.ipynb` and `kernel-metadata.json`

**Files:**
- Create: `submissions/duck_v4/kernel-metadata.json`
- Create: `submissions/duck_v4/notebook.ipynb`
- Test: `tests/test_duck_v4_notebook.py`

**Interfaces:**
- Consumes: `submissions/duck_centroid_v1/notebook.ipynb` structure
- Produces: Valid Kaggle notebook with updated Cell 3 and metadata.

- [ ] **Step 1: Write the failing test**

Create `tests/test_duck_v4_notebook.py`:
```python
import json
from pathlib import Path

def test_duck_v4_notebook_validity():
    nb_path = Path("submissions/duck_v4/notebook.ipynb")
    meta_path = Path("submissions/duck_v4/kernel-metadata.json")

    assert nb_path.exists()
    assert meta_path.exists()

    meta = json.loads(meta_path.read_text())
    assert meta["id"] == "aleixlopez/arc-agi-3-duck-v4"
    assert meta["enable_gpu"] is True

    nb = json.load(open(nb_path))
    assert len(nb["cells"]) >= 20
    cell3_src = "".join(nb["cells"][3]["source"])
    assert "apply_enhancements_v4.py" in cell3_src
    assert "candidate_clicks" in cell3_src
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_duck_v4_notebook.py -v`
Expected: FAIL

- [ ] **Step 3: Create `kernel-metadata.json` and generate `notebook.ipynb`**

Generate `submissions/duck_v4/kernel-metadata.json`:
```json
{
  "id": "aleixlopez/arc-agi-3-duck-v4",
  "title": "ARC-AGI-3 Duck V4",
  "code_file": "notebook.ipynb",
  "language": "python",
  "kernel_type": "notebook",
  "is_private": true,
  "enable_gpu": true,
  "enable_internet": false,
  "keywords": [],
  "dataset_sources": [
    "dfranzen/pennyroyal-v253",
    "dfranzen/qwen38-flashnext-autoround-w4a16",
    "dfranzen/albucino-autoround-int4-mtp-draft",
    "dfranzen/taaf-source"
  ],
  "kernel_sources": [],
  "competition_sources": [
    "arc-prize-2026-arc-agi-3"
  ],
  "model_sources": []
}
```

Generate `submissions/duck_v4/notebook.ipynb` by cloning `submissions/duck_centroid_v1/notebook.ipynb` and replacing Cell 3 with the content of `submissions/duck_v4/apply_enhancements_v4.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_duck_v4_notebook.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add submissions/duck_v4/kernel-metadata.json submissions/duck_v4/notebook.ipynb tests/test_duck_v4_notebook.py
git commit -m "feat: assemble Duck V4 Kaggle notebook and kernel metadata"
```

---

### Task 6: Full Test Suite Verification & Pre-Flight Check

**Files:**
- Test: All tests in `tests/`
- Documentation: `docs/experiments.md`

- [ ] **Step 1: Run all repository tests**

Run: `pytest tests/ -v`
Expected: All 40+ tests pass with 0 failures.

- [ ] **Step 2: Verify git status and log in `docs/experiments.md`**

Update `docs/experiments.md` recording Duck V4 staging:
```markdown
| `sub-duck-v4` | 2026-10-05 | Duck V4: Centroids + In-Sandbox candidate_clicks/object_at + Zero-Prompt-Drift Solved Memory | - | - | - | Staged | Preserves 100% byte-static prompt prefixes for >93% KV cache hit rate while equipping model with click primitives and solved memory. |
```

- [ ] **Step 3: Commit**

```bash
git add docs/experiments.md
git commit -m "docs: log Duck V4 in experiment ledger"
```
