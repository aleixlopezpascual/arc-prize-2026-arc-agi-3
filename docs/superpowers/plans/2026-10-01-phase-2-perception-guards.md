# Phase 2 Foundation: Perception, Action Guards & Utility Subsystems Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the foundational Duck / Milestone 2 perception engine (connected components with D4 rotation-canonical signatures, semantic frame diffing), the no-op repeat action guard, and AST function retention utilities.

**Architecture:** Pure Python & NumPy modules organized into `src/perception/`, `src/guards/`, and `src/utils/`. Each subsystem provides clean functional APIs and data structures with zero heavyweight dependencies, fully verified through unit test suites.

**Tech Stack:** Python 3.12, NumPy, standard library (`ast`, `hashlib`, `collections`, `dis`), Pytest, Ruff.

**Spec:** `docs/superpowers/specs/2026-10-01-phase-2-perception-guards-design.md`

## Global Constraints

- Python >= 3.10 required across all modules.
- Code must pass `ruff check .` with line length 100.
- Zero heavyweight external vision dependencies (OpenCV/scikit-image prohibited; pure NumPy/stdlib only).
- All module interfaces must be stateless or provide explicit reset/lifecycle methods.
- TDD cycle must be strictly followed: test written first, verified RED, minimal code implemented, verified GREEN.

## Review Focus

1. **Empty / Homogeneous Grids:** Passing an empty grid `[]` or a solid single-color board must return valid data structures without throwing `IndexError` or `ValueError`.
2. **Rotational Symmetry Precision:** Symmetry order must evaluate to 4 for square shapes, 2 for symmetrical lines/bars, and 1 for asymmetric shapes (e.g. L-trominoes).
3. **Bounding Box Overlap Zero Protection:** Small bboxes with width or height 1 must calculate overlap ratios safely without divide-by-zero errors.
4. **No-op Override Re-Arming:** A blocked action must execute if immediately repeated (override), but the guard must re-arm so subsequent ineffective actions are blocked again.
5. **AST Safety & Import Scoping:** Functions with global variable mutation (`global x; x += 1`), decorators, or wildcard imports must be rejected defensively during AST validation.

---

### Task 1: Object Segmentation & D4 Rotation-Canonical Signatures

**Files:**
- Create: `src/perception/segmentation.py`
- Test: `tests/test_segmentation.py`

**Interfaces:**
- Produces: `segment_grid(grid: list[list[int]] | np.ndarray) -> list[dict]`, `ObjectNode`, `compute_object_signature(cells: set[tuple[int, int]], color: int)`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_segmentation.py
import pytest
import numpy as np
from src.perception.segmentation import segment_grid, compute_object_signature


def test_segment_grid_basic_shapes():
    # 5x5 grid with a 2x2 square of color 1 and an L-shape of color 2
    grid = [
        [0, 0, 0, 0, 0],
        [0, 1, 1, 0, 0],
        [0, 1, 1, 0, 0],
        [0, 2, 0, 0, 0],
        [0, 2, 2, 0, 0],
    ]
    nodes = segment_grid(grid, background_color=0)
    assert len(nodes) == 2

    # Verify color 1 (2x2 square) has 4-fold rotational symmetry
    square = next(n for n in nodes if n["color"] == 1)
    assert square["pixels"] == 4
    assert square["rotational_symmetry"] == 4
    assert square["bbox"] == [1, 1, 2, 2]

    # Verify color 2 (L-shape) has 1-fold symmetry (asymmetric)
    l_shape = next(n for n in nodes if n["color"] == 2)
    assert l_shape["pixels"] == 3
    assert l_shape["rotational_symmetry"] == 1
    assert l_shape["bbox"] == [3, 1, 4, 2]


def test_segment_grid_rotation_invariance():
    # Square rotated 90 degrees must have identical canonical hash
    cells_original = {(0, 0), (0, 1), (1, 0)}  # Corner L
    cells_rotated = {(0, 0), (1, 0), (1, 1)}   # Rotated 90 deg
    sig1 = compute_object_signature(cells_original, color=3)
    sig2 = compute_object_signature(cells_rotated, color=3)

    assert sig1["canonical_hash"] == sig2["canonical_hash"]
    assert sig1["shape_hash"] == sig2["shape_hash"]


def test_segment_grid_empty_or_solid():
    nodes_empty = segment_grid([], background_color=0)
    assert nodes_empty == []

    solid = [[0, 0], [0, 0]]
    nodes_solid = segment_grid(solid, background_color=0)
    assert nodes_solid == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_segmentation.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.perception'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/perception/segmentation.py
from __future__ import annotations

import hashlib
from typing import Sequence
import numpy as np


def _normalize_cells(cells: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    min_r = min(r for r, _ in cells)
    min_c = min(c for _, c in cells)
    return sorted((r - min_r, c - min_c) for r, c in cells)


def _rotate_cells_90(norm_cells: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    max_r = max(r for r, _ in norm_cells)
    return sorted((c, max_r - r) for r, c in norm_cells)


def _cells_hash(norm_cells: Sequence[tuple[int, int]], color_tag: str | int) -> str:
    payload = repr((color_tag, norm_cells)).encode()
    return hashlib.sha1(payload).hexdigest()[:16]


def compute_object_signature(
    cells: Sequence[tuple[int, int]] | set[tuple[int, int]],
    color: int,
) -> dict:
    if not cells:
        return {
            "canonical_hash": "",
            "rotation": 0,
            "rotational_symmetry": 1,
            "pose_hash": "",
            "shape_hash": "",
        }

    norm = _normalize_cells(list(cells))
    variants = [norm]
    for _ in range(3):
        variants.append(_rotate_cells_90(variants[-1]))

    hashes = [_cells_hash(v, color) for v in variants]
    shape_hashes = [_cells_hash(v, "__shape__") for v in variants]

    k = shape_hashes.index(min(shape_hashes))
    canonical = hashes[k]
    distinct = len(set(shape_hashes))
    symmetry = {1: 4, 2: 2, 4: 1}.get(distinct, 1)

    rotation = ((4 - k) % 4) * 90
    if symmetry == 4:
        rotation = 0
    elif symmetry == 2:
        rotation = rotation % 180

    shape_hash = _cells_hash(norm, "__shape__")
    return {
        "canonical_hash": canonical,
        "rotation": rotation,
        "rotational_symmetry": symmetry,
        "pose_hash": hashes[0],
        "shape_hash": shape_hash,
    }


def segment_grid(
    grid: Sequence[Sequence[int]] | np.ndarray,
    background_color: int | None = 0,
) -> list[dict]:
    if grid is None or len(grid) == 0:
        return []

    arr = np.asarray(grid)
    if arr.ndim != 2 or arr.size == 0:
        return []

    h, w = arr.shape
    visited = np.zeros((h, w), dtype=bool)
    nodes: list[dict] = []
    node_id = 0

    for r in range(h):
        for c in range(w):
            val = int(arr[r, c])
            if visited[r, c] or (background_color is not None and val == background_color):
                continue

            # 4-connected flood-fill
            queue = [(r, c)]
            visited[r, c] = True
            cells: list[tuple[int, int]] = []

            while queue:
                curr_r, curr_c = queue.pop()
                cells.append((curr_r, curr_c))
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = curr_r + dr, curr_c + dc
                    if 0 <= nr < h and 0 <= nc < w and not visited[nr, nc] and arr[nr, nc] == val:
                        visited[nr, nc] = True
                        queue.append((nr, nc))

            min_r = min(cr for cr, _ in cells)
            max_r = max(cr for cr, _ in cells)
            min_c = min(cc for _, cc in cells)
            max_c = max(cc for _, cc in cells)

            sig = compute_object_signature(cells, val)
            nodes.append({
                "id": node_id,
                "color": val,
                "canonical_hash": sig["canonical_hash"],
                "shape_hash": sig["shape_hash"],
                "rotation": sig["rotation"],
                "rotational_symmetry": sig["rotational_symmetry"],
                "pose_hash": sig["pose_hash"],
                "pixels": len(cells),
                "bbox": [min_r, min_c, max_r, max_c],
                "cells": cells,
            })
            node_id += 1

    return nodes
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_segmentation.py -v`
Expected: PASS

---

### Task 2: Frame Difference Detection & Semantic Change Classification

**Files:**
- Create: `src/perception/frame_diff.py`
- Create: `src/perception/__init__.py`
- Test: `tests/test_frame_diff.py`

**Interfaces:**
- Consumes: `segment_grid`, `compute_object_signature` from `src.perception.segmentation`
- Produces: `compute_frame_diff(before: Sequence[Sequence[int]], after: Sequence[Sequence[int]]) -> dict`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_frame_diff.py
import pytest
from src.perception.frame_diff import compute_frame_diff


def test_frame_diff_moved_and_changed_color():
    # 5x5 board: object 1 moves down, object 2 changes color from 3 to 4
    before = [
        [1, 1, 0, 3, 0],
        [1, 1, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
    ]
    after = [
        [0, 0, 0, 4, 0],
        [0, 0, 0, 0, 0],
        [1, 1, 0, 0, 0],
        [1, 1, 0, 0, 0],
        [0, 0, 0, 0, 0],
    ]
    diff = compute_frame_diff(before, after, background_color=0)

    assert diff["changed_cell_count"] > 0
    assert len(diff["moved"]) == 1
    assert diff["moved"][0]["color"] == 1
    assert diff["moved"][0]["from_bbox"] == [0, 0, 1, 1]
    assert diff["moved"][0]["to_bbox"] == [2, 0, 3, 1]

    assert len(diff["changed_color"]) == 1
    assert diff["changed_color"][0]["before_color"] == 3
    assert diff["changed_color"][0]["after_color"] == 4


def test_frame_diff_appeared_disappeared():
    before = [[1, 0], [0, 0]]
    after = [[0, 0], [0, 2]]
    diff = compute_frame_diff(before, after, background_color=0)

    assert len(diff["disappeared"]) == 1
    assert diff["disappeared"][0]["color"] == 1
    assert len(diff["appeared"]) == 1
    assert diff["appeared"][0]["color"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_frame_diff.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.perception.frame_diff'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/perception/frame_diff.py
from __future__ import annotations

from typing import Sequence
import numpy as np

from src.perception.segmentation import segment_grid


def _bbox_area(bbox: Sequence[int]) -> int:
    return max(0, bbox[2] - bbox[0] + 1) * max(0, bbox[3] - bbox[1] + 1)


def _overlap_ratio(b1: Sequence[int], b2: Sequence[int]) -> float:
    inter_r = min(b1[2], b2[2]) - max(b1[0], b2[0]) + 1
    inter_c = min(b1[3], b2[3]) - max(b1[1], b2[1]) + 1
    if inter_r <= 0 or inter_c <= 0:
        return 0.0
    smaller = min(_bbox_area(b1), _bbox_area(b2))
    return (inter_r * inter_c) / smaller if smaller > 0 else 0.0


def compute_frame_diff(
    before_grid: Sequence[Sequence[int]] | np.ndarray,
    after_grid: Sequence[Sequence[int]] | np.ndarray,
    background_color: int | None = 0,
) -> dict:
    arr_b = np.asarray(before_grid)
    arr_a = np.asarray(after_grid)

    changed_cells = int(np.sum(arr_b != arr_a)) if arr_b.shape == arr_a.shape else 0

    nodes_before = segment_grid(arr_b, background_color=background_color)
    nodes_after = segment_grid(arr_a, background_color=background_color)

    moved: list[dict] = []
    rotated: list[dict] = []
    changed_color: list[dict] = []
    resized: list[dict] = []
    appeared: list[dict] = []
    disappeared: list[dict] = []

    used_before: set[int] = set()
    used_after: set[int] = set()

    # Match identical objects (unchanged)
    for bi, nb in enumerate(nodes_before):
        for ai, na in enumerate(nodes_after):
            if ai in used_after:
                continue
            if nb["bbox"] == na["bbox"] and nb["pose_hash"] == na["pose_hash"] and nb["color"] == na["color"]:
                used_before.add(bi)
                used_after.add(ai)
                break

    # Phase A: Changed color (same bbox and shape_hash, different color)
    for bi, nb in enumerate(nodes_before):
        if bi in used_before:
            continue
        for ai, na in enumerate(nodes_after):
            if ai in used_after:
                continue
            if nb["bbox"] == na["bbox"] and nb["shape_hash"] == na["shape_hash"] and nb["color"] != na["color"]:
                changed_color.append({
                    "bbox": nb["bbox"],
                    "before_color": nb["color"],
                    "after_color": na["color"],
                    "pixels": nb["pixels"],
                })
                used_before.add(bi)
                used_after.add(ai)
                break

    # Phase B: Resized (same color, bbox overlap >= 0.5)
    for bi, nb in enumerate(nodes_before):
        if bi in used_before:
            continue
        for ai, na in enumerate(nodes_after):
            if ai in used_after:
                continue
            if nb["color"] == na["color"] and _overlap_ratio(nb["bbox"], na["bbox"]) >= 0.5:
                resized.append({
                    "color": nb["color"],
                    "from_bbox": nb["bbox"],
                    "to_bbox": na["bbox"],
                    "before_pixels": nb["pixels"],
                    "after_pixels": na["pixels"],
                })
                used_before.add(bi)
                used_after.add(ai)
                break

    # Phase C: Moved or Rotated (same color and canonical_hash)
    for bi, nb in enumerate(nodes_before):
        if bi in used_before:
            continue
        for ai, na in enumerate(nodes_after):
            if ai in used_after:
                continue
            if nb["color"] == na["color"] and nb["canonical_hash"] == na["canonical_hash"]:
                if nb["rotation"] != na["rotation"]:
                    rotated.append({
                        "color": nb["color"],
                        "from_bbox": nb["bbox"],
                        "to_bbox": na["bbox"],
                        "from_rotation": nb["rotation"],
                        "to_rotation": na["rotation"],
                    })
                else:
                    moved.append({
                        "color": nb["color"],
                        "from_bbox": nb["bbox"],
                        "to_bbox": na["bbox"],
                        "pixels": nb["pixels"],
                    })
                used_before.add(bi)
                used_after.add(ai)
                break

    for bi, nb in enumerate(nodes_before):
        if bi not in used_before:
            disappeared.append({
                "color": nb["color"],
                "bbox": nb["bbox"],
                "pixels": nb["pixels"],
            })

    for ai, na in enumerate(nodes_after):
        if ai not in used_after:
            appeared.append({
                "color": na["color"],
                "bbox": na["bbox"],
                "pixels": na["pixels"],
            })

    return {
        "changed_cell_count": changed_cells,
        "moved": moved,
        "rotated": rotated,
        "appeared": appeared,
        "disappeared": disappeared,
        "changed_color": changed_color,
        "resized": resized,
    }
```

```python
# src/perception/__init__.py
from src.perception.frame_diff import compute_frame_diff
from src.perception.segmentation import compute_object_signature, segment_grid

__all__ = ["compute_frame_diff", "compute_object_signature", "segment_grid"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_frame_diff.py -v`
Expected: PASS

---

### Task 3: No-op Repeat Action Guard

**Files:**
- Create: `src/guards/noop_repeat_guard.py`
- Create: `src/guards/__init__.py`
- Test: `tests/test_noop_guard.py`

**Interfaces:**
- Produces: `NoopRepeatGuard` with `observe()`, `should_block()`, `note_level()`, and `action_signature()`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_noop_guard.py
import pytest
from src.guards.noop_repeat_guard import NoopRepeatGuard, action_signature, compute_interior_hash


def test_action_signature_normalization():
    assert action_signature("action1") == "ACTION1"
    assert action_signature({"action": "ACTION6", "row": 10, "col": 20}) == "ACTION6(10,20)"
    assert action_signature("ACTION6(row=10, col=20)") == "ACTION6(10,20)"


def test_noop_repeat_guard_blocking_and_override():
    guard = NoopRepeatGuard()
    guard.note_level(1)

    state_hash = "abc123state"
    action = "ACTION1"

    # Initially not blocked
    assert not guard.should_block(state_hash, action)

    # Observe that this action caused zero interior change
    guard.observe(state_hash, action, gameplay_changed=False)

    # Next attempt in the same state should block
    assert guard.should_block(state_hash, action)

    # Immediate repetition (override): should_block returns False and allows execution
    assert not guard.should_block(state_hash, action)


def test_interior_hash_border_crop():
    # 6x6 grid where outer border has changing timer bar, interior 2x2 is identical
    grid1 = [
        [1, 1, 1, 1, 1, 1],
        [1, 0, 0, 0, 0, 1],
        [1, 0, 9, 9, 0, 1],
        [1, 0, 9, 9, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 1, 1],
    ]
    # Same interior 9s, but border timer changed from 1 to 2
    grid2 = [
        [2, 2, 2, 2, 2, 2],
        [2, 0, 0, 0, 0, 2],
        [2, 0, 9, 9, 0, 2],
        [2, 0, 9, 9, 0, 2],
        [2, 0, 0, 0, 0, 2],
        [2, 2, 2, 2, 2, 2],
    ]
    # Cropping border of 2 gives identical interior hashes
    h1 = compute_interior_hash(grid1, border_margin=2)
    h2 = compute_interior_hash(grid2, border_margin=2)
    assert h1 == h2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_noop_guard.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.guards'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/guards/noop_repeat_guard.py
from __future__ import annotations

import hashlib
import re
from collections import OrderedDict
from typing import Any, Sequence
import numpy as np

_DISPLAY_COORDS_RE = re.compile(
    r"^([A-Z0-9_]+)\(\s*(?:ROW\s*=\s*)?(-?\d+)\s*,\s*(?:COL\s*=\s*)?(-?\d+)\s*\)$"
)


def action_signature(action: Any) -> str:
    if isinstance(action, dict):
        name = str(action.get("action") or action.get("name") or "").strip().upper()
        row = action.get("row")
        col = action.get("col")
        if row is not None or col is not None:
            return f"{name}({row},{col})"
        return name

    text = " ".join(str(action or "").split()).upper()
    match = _DISPLAY_COORDS_RE.match(text)
    if match:
        return f"{match.group(1)}({match.group(2)},{match.group(3)})"
    return text


def compute_interior_hash(grid: Sequence[Sequence[int]] | np.ndarray, border_margin: int = 4) -> str:
    arr = np.asarray(grid)
    if arr.ndim != 2 or arr.size == 0:
        return ""
    h, w = arr.shape
    if h <= border_margin * 2 or w <= border_margin * 2:
        interior = arr
    else:
        interior = arr[border_margin : h - border_margin, border_margin : w - border_margin]
    return hashlib.sha1(interior.tobytes()).hexdigest()[:16]


class NoopRepeatGuard:
    def __init__(self, max_states: int = 512, max_actions: int = 16) -> None:
        self.max_states = max_states
        self.max_actions = max_actions
        self.states: OrderedDict[str, OrderedDict[str, None]] = OrderedDict()
        self.level: int | None = None
        self.armed_slot: tuple[str, str] | None = None

    def note_level(self, level: int) -> None:
        if level != self.level:
            self.level = level
            self.states.clear()
            self.armed_slot = None

    def observe(self, state_hash: str, action: Any, gameplay_changed: bool) -> None:
        sig = action_signature(action)
        if not state_hash or not sig:
            return

        if not gameplay_changed:
            entry = self.states.get(state_hash)
            if entry is None:
                entry = OrderedDict()
                self.states[state_hash] = entry
                while len(self.states) > self.max_states:
                    self.states.popitem(last=False)
            entry[sig] = None
            while len(entry) > self.max_actions:
                entry.popitem(last=False)
        else:
            entry = self.states.get(state_hash)
            if entry is not None and sig in entry:
                del entry[sig]
                if not entry:
                    del self.states[state_hash]

    def should_block(self, state_hash: str, action: Any) -> bool:
        sig = action_signature(action)
        if not state_hash or not sig:
            return False

        # Check if already armed for override
        if self.armed_slot == (state_hash, sig):
            self.armed_slot = None
            return False

        entry = self.states.get(state_hash)
        if entry is not None and sig in entry:
            self.armed_slot = (state_hash, sig)
            return True

        self.armed_slot = None
        return False
```

```python
# src/guards/__init__.py
from src.guards.noop_repeat_guard import (
    NoopRepeatGuard,
    action_signature,
    compute_interior_hash,
)

__all__ = ["NoopRepeatGuard", "action_signature", "compute_interior_hash"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_noop_guard.py -v`
Expected: PASS

---

### Task 4: Retained Functions AST Validation & Namespace Isolation

**Files:**
- Create: `src/utils/retained_functions.py`
- Create: `src/utils/__init__.py`
- Test: `tests/test_retained_funcs.py`

**Interfaces:**
- Produces: `prepare_functions()`, `restore_functions()`, `function_signature()`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_retained_funcs.py
import pytest
from src.utils.retained_functions import prepare_functions, restore_functions, function_signature


def test_prepare_valid_functions():
    code = """
import math

def distance(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)
"""
    kept, rejected = prepare_functions([code], available=["math"])
    assert "distance" in kept
    assert len(rejected) == 0
    assert function_signature(code) == "distance(x1, y1, x2, y2)"


def test_reject_dangerous_or_decorated_functions():
    # Mutates global variable
    code_global = """
def mutate():
    global counter
    counter += 1
"""
    kept, rejected = prepare_functions([code_global], available=[])
    assert "mutate" not in kept
    assert len(rejected) == 1

    # Uses decorator
    code_decorated = """
@some_dec
def my_func():
    return 42
"""
    kept2, rejected2 = prepare_functions([code_decorated], available=[])
    assert "my_func" not in kept2
    assert len(rejected2) == 1


def test_restore_functions_in_clean_namespace():
    code = """
def add_ten(x):
    return x + 10
"""
    ns = {}
    survivors, rejected = restore_functions([code], namespace=ns, available=[])
    assert "add_ten" in ns
    assert ns["add_ten"](5) == 15
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_retained_funcs.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.utils'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/utils/retained_functions.py
from __future__ import annotations

import ast
import dis
import types
from typing import Any, Sequence


def _import_statements(nodes: Sequence[ast.AST]) -> dict[str, str]:
    statements = {}
    for node in nodes:
        if isinstance(node, ast.Import):
            for alias in node.names:
                binding = alias.asname or alias.name.split(".")[0]
                statements[binding] = ast.unparse(ast.Import(names=[alias]))
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            for alias in node.names:
                if alias.name == "*":
                    raise ValueError("wildcard imports are not retained")
                statements[alias.asname or alias.name] = ast.unparse(
                    ast.ImportFrom(module=node.module, names=[alias], level=0)
                )
    return statements


def _source_parts(source: str, retain_imports: bool = True) -> tuple[ast.FunctionDef, dict[str, str]]:
    tree = ast.parse(source, "<retained>", "exec")
    if not tree.body or not isinstance(tree.body[-1], ast.FunctionDef):
        raise ValueError("only top-level function definitions can be retained")
    imports = _import_statements(tree.body[:-1]) if retain_imports else {}
    return tree.body[-1], imports


def function_signature(source: str) -> str:
    node, _ = _source_parts(source, retain_imports=False)
    return f"{node.name}({ast.unparse(node.args)})"


def _function_record(source: str) -> tuple[str, str, set[str]]:
    node, imports = _source_parts(source, retain_imports=True)
    if node.decorator_list:
        raise ValueError("decorated functions are not retained")

    tree = ast.Module(body=[node], type_ignores=[])
    code = next(c for c in compile(tree, "<retained>", "exec").co_consts if isinstance(c, types.CodeType))
    reads = set()
    pending = [code]

    while pending:
        curr = pending.pop()
        for instr in dis.get_instructions(curr):
            if instr.opname in ("LOAD_GLOBAL", "LOAD_NAME"):
                reads.add(instr.argval)
            elif instr.opname in ("STORE_GLOBAL", "DELETE_GLOBAL"):
                raise ValueError("functions that assign global variables are not retained")
        pending.extend(c for c in curr.co_consts if isinstance(c, types.CodeType))

    return node.name, source, reads - imports.keys()


def prepare_functions(
    sources: Sequence[str],
    available: Sequence[str] | set[str],
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    records: dict[str, tuple[str, set[str]]] = {}
    rejected: list[dict[str, Any]] = []

    for source in sources:
        name = "<unknown>"
        try:
            name, src, reads = _function_record(source)
            records[name] = (src, reads)
        except Exception as exc:
            rejected.append({"name": name, "reason": str(exc)})

    # Prune functions with missing dependencies
    avail_set = set(available)
    while True:
        dropped = []
        for name, (src, reads) in records.items():
            missing = reads - avail_set - records.keys()
            if missing:
                dropped.append(name)
                rejected.append({"name": name, "reason": f"missing dependencies: {missing}"})
        if not dropped:
            break
        for name in dropped:
            del records[name]

    return {name: val[0] for name, val in records.items()}, rejected


def restore_functions(
    sources: Sequence[str],
    namespace: dict[str, Any],
    available: Sequence[str] | set[str],
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    kept, rejected = prepare_functions(sources, available)
    failed = set()

    for name, source in kept.items():
        try:
            exec(compile(source, "<retained>", "exec"), namespace, namespace)
        except Exception as exc:
            failed.add(name)
            rejected.append({"name": name, "reason": f"exec failed: {exc}"})

    survivors = {name: src for name, src in kept.items() if name not in failed}
    return survivors, rejected
```

```python
# src/utils/__init__.py
from src.utils.retained_functions import (
    function_signature,
    prepare_functions,
    restore_functions,
)

__all__ = ["function_signature", "prepare_functions", "restore_functions"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_retained_funcs.py -v`
Expected: PASS

---

### Task 5: Integration Verification & Full Test Suite

**Files:**
- Modify: `tests/`
- Verify: Full pytest and ruff check pass

- [ ] **Step 1: Run complete test suite**

Run: `python3 -m pytest tests/ -v`
Expected: 22+ passed

- [ ] **Step 2: Run ruff check**

Run: `python3 -m ruff check src/ tests/`
Expected: All checks passed!
