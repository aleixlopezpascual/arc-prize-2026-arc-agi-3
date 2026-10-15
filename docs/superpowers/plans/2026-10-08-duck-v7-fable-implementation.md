# Duck V7 Architecture (Fable Layer + Perception + Search) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Duck V7, fusing Duck V6 perception primitives (`candidate_clicks`, `object_at`, `is_border`, `bfs_path`, null-safe `solved_memory`) and Franzen round-robin scheduling with Aleksei Provorov's Fable 5 diagnostic engine (indicator note tracking, low fuel budget alerts, and dragging-level pinned logs).

**Architecture:** Port the pure-Python Fable diagnostic engine into `src/perception/fable_core.py` and sandbox helpers. Surgically patch `tool_agent.py` and `python_tool_sandbox.py` in `submissions/duck_v7/apply_enhancements_v7.py` under the `ARC3_FABLE_LAYER="1"` environment gate. Fast levels remain byte-static (preserving SGLang's >93% KV-cache hit rate); dragging levels receive indicator alerts, low fuel warnings, and pinned factual control logs.

**Tech Stack:** Python 3.10+, Pytest, Kaggle CLI, SGLang / Qwen 3.8 Flash-Next.

**Spec:** `docs/superpowers/specs/2026-10-08-duck-v7-fable-design.md`

## Global Constraints

- Prompts on fast levels (<15,000 tokens) must receive 0 dynamic text in `_build_user_prompt` to preserve SGLang's RadixAttention KV-cache reuse rate.
- All diagnostic computations are deterministic, running on 64x64 integer grids with standard library Python only (no LLM generation for summaries).
- Fable diagnostics are strictly opt-in via `ARC3_FABLE_LAYER="1"`. When unset or `"0"`, behavior is identical to Duck V6.
- Retain guaranteed round-robin scheduling (`gate.acquire(_PRIORITY_UNTRIMMED_BASE - self._queue_position())`) and the 185k token cap (`bm.solver.max_generated_tokens_per_game = 185000`).
- Any detector failure, missing key, or unexpected format fails open (returns empty/None, never crashes).

## Review Focus

1. **Empty or Malformed Grids:** `diff_cells`, `small_far_changes`, and `detect_budget` called on empty or non-rectangular grids must return safe defaults without throwing exceptions.
2. **Animation / Redraw Storms:** When >60 cells or >6 distinct regions change at once, `small_far_changes` and `Ledger` must declare the frame `noisy` and suppress indicator notes rather than spamming context.
3. **Budget Bar Ambiguity:** Non-monotonic or bidirectional changes on edge lines must not be classified as a linear countdown budget bar.
4. **Level Log Message Alternation:** Injected pinned `LEVEL LOG` must insert a valid `(user, assistant)` message pair without creating two consecutive user turns.
5. **RadixAttention Cache Preservation:** `_fl_opener_lines()` must return empty lists on levels taking <15,000 tokens.

---

### Task 1: Core Fable Diagnostic Module (`src/perception/fable_core.py`)

**Files:**
- Create: `src/perception/fable_core.py`
- Create: `tests/test_fable_core.py`

**Interfaces:**
- Produces:
  - `diff_cells(a, b) -> list[tuple[int, int]]`
  - `components8(cells) -> list[list[tuple[int, int]]]`
  - `small_far_changes(before, after) -> list[dict[str, Any]]`
  - `detect_budget(frames, min_actions=3) -> dict[str, Any] | None`
  - `budget_alert(b, first_time=False) -> str`
  - `class Ledger: feed(action, result, before, after) -> list[dict]`, `key_lines() -> list[str]`, `digest_lines() -> list[str]`
  - `build_level_log(...) -> str`

- [ ] **Step 1: Write the failing test**

Create `tests/test_fable_core.py`:
```python
import pytest
from src.perception.fable_core import (
    diff_cells,
    components8,
    small_far_changes,
    detect_budget,
    budget_alert,
    Ledger,
    build_level_log,
)

def test_diff_cells_and_components8():
    grid_a = [[0] * 10 for _ in range(10)]
    grid_b = [[0] * 10 for _ in range(10)]
    grid_b[2][2] = 1
    grid_b[2][3] = 1
    grid_b[8][8] = 2

    diffs = diff_cells(grid_a, grid_b)
    assert set(diffs) == {(2, 2), (2, 3), (8, 8)}

    comps = components8(diffs)
    assert len(comps) == 2
    comp_sizes = sorted(len(c) for c in comps)
    assert comp_sizes == [1, 2]

def test_small_far_changes_indicator_detection():
    # 64x64 grid
    before = [[0] * 64 for _ in range(64)]
    after = [[0] * 64 for _ in range(64)]

    # Main moving object in center (e.g. 5x5 block moving)
    for r in range(30, 35):
        for c in range(30, 35):
            before[r][c] = 3
    for r in range(30, 35):
        for c in range(31, 36):
            after[r][c] = 3

    # Small indicator patch far away in top-left legend: 2x2 patch changes from color 1 to color 2
    for r in range(5, 7):
        for c in range(5, 7):
            before[r][c] = 1
            after[r][c] = 2

    patches = small_far_changes(before, after)
    assert len(patches) == 1
    p = patches[0]
    assert p["box"] == (5, 5, 6, 6)
    assert p["size"] == 4

def test_detect_budget_and_alert():
    frames = []
    # Row 0 is a 64-column bar of color 5 shrinking from the right
    for step in range(10):
        grid = [[0] * 64 for _ in range(64)]
        # Bar shrinking by 2 cells per step from length 40 down to 22
        bar_len = 40 - (step * 2)
        for c in range(bar_len):
            grid[0][c] = 5
        frames.append(grid)

    budget = detect_budget(frames)
    assert budget is not None
    assert budget["kind"] == "row"
    assert budget["index"] == 0
    assert budget["left"] == 22
    assert budget["rate"] == pytest.approx(2.0, abs=0.2)

    # Test alert when remaining actions are low
    alert_text = budget_alert(budget, first_time=False)
    assert "Step budget" in alert_text
    assert "row 0" in alert_text

def test_ledger_feed_and_key_lines():
    led = Ledger(level=1)
    grid1 = [[0] * 64 for _ in range(64)]
    grid2 = [[0] * 64 for _ in range(64)]
    # An inner move
    grid2[30][30] = 1

    events = led.feed("UP", {}, grid1, grid2)
    assert led.n_actions == 1
    assert led.keys["UP"]["changed"] == 1

    lines = led.key_lines()
    assert any("UP: pressed 1" in l for l in lines)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_fable_core.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.perception.fable_core'`

- [ ] **Step 3: Implement `src/perception/fable_core.py`**

Port the pure-Python Fable diagnostic engine into `src/perception/fable_core.py` (based on `fable_layer_core.py`).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_fable_core.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/perception/fable_core.py tests/test_fable_core.py
git commit -m "feat: implement Fable core diagnostic perception module"
```

---

### Task 2: Expose Diagnostic Helpers in Sandbox Primitives

**Files:**
- Modify: `src/perception/sandbox_primitives.py`
- Modify: `tests/test_sandbox_primitives.py`

**Interfaces:**
- Produces:
  - `detect_indicators(before=None, after=None) -> list[dict]`
  - `detect_budget(frames=None) -> dict | None`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_sandbox_primitives.py`:
```python
from src.perception.sandbox_primitives import detect_indicators, detect_budget_helper

def test_sandbox_diagnostic_helpers_safe_empty():
    assert detect_indicators(None, None) == []
    assert detect_budget_helper([]) is None

def test_sandbox_detect_indicators():
    before = [[0] * 64 for _ in range(64)]
    after = [[0] * 64 for _ in range(64)]
    # Main moving cluster
    for r in range(20, 25):
        for c in range(20, 25):
            before[r][c] = 1
            after[r][c+1] = 1
    # Distant indicator
    for r in range(5, 7):
        for c in range(5, 7):
            before[r][c] = 2
            after[r][c] = 3

    res = detect_indicators(before, after)
    assert len(res) == 1
    assert res[0]["size"] == 4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_sandbox_primitives.py -k "diagnostic" -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement `detect_indicators` and `detect_budget_helper` in `sandbox_primitives.py`**

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_sandbox_primitives.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/perception/sandbox_primitives.py tests/test_sandbox_primitives.py
git commit -m "feat: expose Fable diagnostic helpers in sandbox primitives"
```

---

### Task 3: Enhancement Script `apply_enhancements_v7.py` and Dry-Run Patch Verification

**Files:**
- Create: `submissions/duck_v7/apply_enhancements_v7.py`
- Create: `tests/test_duck_v7.py`

**Interfaces:**
- Consumes: Local `taaf_source` repository tree (`input/taaf_source/src/ARC3-Inference`)
- Produces: Patched `segmentation.py`, `python_tool_sandbox.py`, `tool_agent.py`, `prompts.py`, and written `fable_layer_core.py`.
- Invariant: Zero syntax errors, zero import errors, and all hooks compile cleanly under both `ARC3_FABLE_LAYER=0` and `ARC3_FABLE_LAYER=1`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_duck_v7.py`:
```python
import pytest
from pathlib import Path
import tempfile
import shutil
import subprocess
import py_compile

def test_dry_run_enhancements_v7():
    source_root = Path("input/taaf_source/src/ARC3-Inference")
    assert source_root.exists(), "ARC3-Inference source must exist for patch test"

    with tempfile.TemporaryDirectory() as tmp_dir:
        dest_root = Path(tmp_dir) / "ARC3-Inference"
        shutil.copytree(source_root, dest_root)

        patch_script = Path("submissions/duck_v7/apply_enhancements_v7.py")
        assert patch_script.exists(), "apply_enhancements_v7.py must exist"

        # Run patch script
        res = subprocess.run(
            ["python3", str(patch_script.resolve()), str(Path(tmp_dir).resolve())],
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0, f"Patch failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"

        # 1. Verify fable_layer_core.py was written and compiles
        fable_core = dest_root / "inference/agent/fable_layer_core.py"
        assert fable_core.exists()
        py_compile.compile(str(fable_core), doraise=True)

        # 2. Verify segmentation compiles and has is_border
        seg_file = dest_root / "inference/utils/segmentation.py"
        seg_code = seg_file.read_text()
        assert "is_border" in seg_code
        py_compile.compile(str(seg_file), doraise=True)

        # 3. Verify python_tool_sandbox compiles and has bfs_path, candidate_clicks, object_at
        sandbox_file = dest_root / "inference/agent/python_tool_sandbox.py"
        sandbox_code = sandbox_file.read_text()
        assert "def bfs_path" in sandbox_code
        assert "def candidate_clicks" in sandbox_code
        assert "def object_at" in sandbox_code
        py_compile.compile(str(sandbox_file), doraise=True)

        # 4. Verify tool_agent compiles and has Fable layer methods + null safety
        agent_file = dest_root / "inference/agent/tool_agent.py"
        agent_code = agent_file.read_text()
        assert "ARC3_FABLE_LAYER" in agent_code
        assert "_fl_opener_lines" in agent_code
        assert "if current_frame_payload is not None:" in agent_code
        py_compile.compile(str(agent_file), doraise=True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_duck_v7.py -v`
Expected: FAIL with `AssertionError: apply_enhancements_v7.py must exist`

- [ ] **Step 3: Implement `submissions/duck_v7/apply_enhancements_v7.py`**

Create `submissions/duck_v7/apply_enhancements_v7.py` embedding `fable_layer_core.py` and applying all Duck V6 enhancements plus the Fable 5 hooks.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_duck_v7.py -v`
Expected: PASS with 0 errors.

- [ ] **Step 5: Commit**

```bash
git add submissions/duck_v7/apply_enhancements_v7.py tests/test_duck_v7.py
git commit -m "feat: implement Duck V7 enhancement patch script and dry-run tests"
```

---

### Task 4: Build Duck V7 Notebook (`submissions/duck_v7/notebook.ipynb`) & Metadata

**Files:**
- Create: `submissions/duck_v7/kernel-metadata.json`
- Create: `submissions/duck_v7/notebook.ipynb`
- Create: `tests/test_duck_v7_notebook.py`

**Interfaces:**
- Consumes: Duck V6 notebook architecture and `apply_enhancements_v7.py`
- Produces: Valid Kaggle notebook with Fable layer active, round-robin scheduler preserved, and 185k token cap.

- [ ] **Step 1: Write the failing test**

Create `tests/test_duck_v7_notebook.py`:
```python
import json
from pathlib import Path

def test_duck_v7_notebook_validity():
    nb_path = Path("submissions/duck_v7/notebook.ipynb")
    meta_path = Path("submissions/duck_v7/kernel-metadata.json")

    assert nb_path.exists(), "submissions/duck_v7/notebook.ipynb must exist"
    assert meta_path.exists(), "submissions/duck_v7/kernel-metadata.json must exist"

    meta = json.loads(meta_path.read_text())
    assert meta["id"] == "aleixlopez/arc-agi-3-duck-v7"
    assert meta["title"] == "ARC-AGI-3 Duck V7"
    assert meta["enable_gpu"] is True

    nb = json.load(open(nb_path))
    assert len(nb["cells"]) >= 20

    cell3_src = "".join(nb["cells"][3]["source"])
    assert "apply_enhancements_v7.py" in cell3_src
    assert "candidate_clicks" in cell3_src
    assert "bfs_path" in cell3_src

    cell5_src = "".join(nb["cells"][5]["source"])
    assert "apply_enhancements_v7.py" in cell5_src
    assert "ARC3_FABLE_LAYER" in cell5_src

    cell17_src = "".join(nb["cells"][17]["source"])
    assert "bm.solver.max_generated_tokens_per_game = 185000" in cell17_src
    assert "ours_form_priority" not in cell17_src
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_duck_v7_notebook.py -v`
Expected: FAIL

- [ ] **Step 3: Create `kernel-metadata.json` and generate `notebook.ipynb`**

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_duck_v7_notebook.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add submissions/duck_v7/kernel-metadata.json submissions/duck_v7/notebook.ipynb tests/test_duck_v7_notebook.py
git commit -m "feat: assemble Duck V7 Kaggle notebook and kernel metadata"
```

---

### Task 5: Auto-Submit Daemon for Duck V7 (`scripts/auto_submit_duck_v7.py`)

**Files:**
- Create: `scripts/auto_submit_duck_v7.py`

**Interfaces:**
- Consumes: `submissions/duck_v7/` kernel files
- Produces: Autonomous deployment daemon staged to launch Duck V7 when ready.

- [ ] **Step 1: Implement `scripts/auto_submit_duck_v7.py`**

- [ ] **Step 2: Verify syntax and dry-run execution**

Run: `python3 -m py_compile scripts/auto_submit_duck_v7.py`
Expected: Clean compile with return code 0.

- [ ] **Step 3: Commit**

```bash
git add scripts/auto_submit_duck_v7.py
git commit -m "feat: add Duck V7 auto-submit daemon"
```
