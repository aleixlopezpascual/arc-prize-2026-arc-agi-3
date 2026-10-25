# Duck V17: Adaptive Armor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Duck V17 combining Kaggle platform timeout armor (55m startup, 900s HTTP retry, warmup reset keepalive), Candidate G's bounded 16 KiB JSON memory & exact toggle solvers, and Duck V12's proven 58.42% demo engine.

**Architecture:** Duck V17 hardens our submission against the late-October Kaggle dataset cache crisis (avoiding the 0.00 score trap) while injecting test-time exact algebraic reasoning (`solve_toggle` over GF(2)), bounded graph search (`route`, `bounded_search`), and adaptive verified execution (`follow_plan`) directly into the Python REPL sandbox without system prompt drift.

**Tech Stack:** Python 3.10+, NumPy, Jupyter Notebook (`nbformat`), Pytest, Kaggle API, SGLang Pennyroyal, Qwen3.8-Flash-Next.

**Spec:** `docs/intel/top_solutions_research.md` (Section 7)

## Global Constraints

- Zero prompt drift: Sandbox extensions and memory MUST NOT modify system prompt tokens dynamically during gameplay, preserving SGLang's >93% KV cache hit rate.
- Infra robustness: Startup timeout must be $\ge 55$ minutes with 900s HTTP retry backoff and a warmup reset action to prevent Kaggle gateway inactivity cancellation.
- Memory budget: In-sandbox JSON `notes` dict must be hard-capped at 16 KiB with automatic compaction to prevent memory leaks across multi-level games.
- Backward compatibility: All 88 existing pytest unit tests must remain 100% green.
- Round-robin queue fairness: Retain Franzen's admission gate (`gate.acquire(2000000 - waiting_order)`) so all 110 competition games get on the board.

## Review Focus

1. `solve_toggle` handles degenerate button systems (empty masks, zero target, or over-constrained unsolvable targets) gracefully without unhandled exceptions.
2. `normalize_notes` enforces structural bounds ($\le 16\text{ KiB}$) and isolates level-specific notes when level changes occur.
3. `bounded_search` respects strict time ($< 10\text{s}$) and node bounds ($< 200,000$) even on cyclic state graphs.
4. `follow_plan` halts execution on the first prediction mismatch, returning a clean diagnostic dict without crashing.
5. `submissions/duck_v17/notebook.ipynb` contains valid JSON, preserves GPU metadata (`RTX PRO 6000`), and embeds the 55-minute startup shield.

---

### Task 1: Exact Algebraic Toggle Solver (`solve_toggle`)

**Files:**
- Modify: `src/perception/sandbox_primitives.py`
- Test: `tests/test_sandbox_primitives.py`

**Interfaces:**
- Produces: `solve_toggle(button_masks: list[int], target: int, n_cells: int | None = None, max_nullity: int = 18) -> dict`
- Returns: `dict(solvable: bool, indices: list[int] | None, clicks: int, minimal: bool, nullity: int)`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_sandbox_primitives.py`:
```python
def test_solve_toggle_exact():
    from src.perception.sandbox_primitives import solve_toggle
    # Button 0 toggles cell 0 (mask 1)
    # Button 1 toggles cells 0 and 1 (mask 3)
    # Button 2 toggles cell 1 (mask 2)
    # Target: turn on cell 1 only (target 2)
    res = solve_toggle([1, 3, 2], target=2)
    assert res["solvable"] is True
    assert res["indices"] == [2] or len(res["indices"]) == 1
    assert res["clicks"] == 1
    assert res["minimal"] is True

def test_solve_toggle_unsolvable():
    from src.perception.sandbox_primitives import solve_toggle
    # Parity conflict: only even bits togglable, odd bit required
    res = solve_toggle([2, 4], target=1)
    assert res["solvable"] is False
    assert res["indices"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_sandbox_primitives.py -k test_solve_toggle -v`
Expected: FAIL with `ImportError: cannot import name 'solve_toggle'`

- [ ] **Step 3: Implement `solve_toggle` in `src/perception/sandbox_primitives.py`**

```python
def solve_toggle(button_masks: list[int], target: int, n_cells: int | None = None, max_nullity: int = 18) -> dict:
    """Solve independent binary XOR toggles from measured button effects via GF(2) Gaussian elimination."""
    masks = [int(x) for x in button_masks]
    target = int(target)
    if target < 0 or any(x < 0 for x in masks) or len(masks) > 256:
        raise ValueError("Use at most 256 nonnegative button masks and target")
    required = max([target.bit_length()] + [m.bit_length() for m in masks])
    n_cells = required if n_cells is None else int(n_cells)
    if not required <= n_cells <= 4096:
        raise ValueError("n_cells must cover all mask bits and be <=4096")
    basis = {}
    nullspace = []
    for index, vector in enumerate(masks):
        combination = 1 << index
        while vector:
            pivot = vector.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = (vector, combination)
                break
            row, row_combination = basis[pivot]
            vector ^= row
            combination ^= row_combination
        if not vector:
            nullspace.append(combination)
    residual, solution = target, 0
    while residual:
        pivot = residual.bit_length() - 1
        if pivot not in basis:
            return dict(solvable=False, indices=None, minimal=False, nullity=len(nullspace), clicks=0)
        row, combination = basis[pivot]
        residual ^= row
        solution ^= combination
    minimal = len(nullspace) <= min(18, max(0, int(max_nullity)))
    if minimal:
        current, best, last_gray = solution, solution, 0
        for i in range(1, 1 << len(nullspace)):
            gray = i ^ (i >> 1)
            current ^= nullspace[(gray ^ last_gray).bit_length() - 1]
            last_gray = gray
            if current.bit_count() < best.bit_count():
                best = current
        solution = best
    else:
        for _ in range(3):
            for vector in nullspace:
                if (solution ^ vector).bit_count() < solution.bit_count():
                    solution ^= vector
    indices = [i for i in range(len(masks)) if solution & (1 << i)]
    check = 0
    for i in indices:
        check ^= masks[i]
    if check != target:
        raise AssertionError("Toggle solution failed verification")
    return dict(solvable=True, indices=indices, clicks=len(indices), minimal=minimal, nullity=len(nullspace))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_sandbox_primitives.py -k test_solve_toggle -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/perception/sandbox_primitives.py tests/test_sandbox_primitives.py
git commit -m "feat: add exact GF(2) solve_toggle algebraic puzzle solver"
```

---

### Task 2: State-Space Bounded Search & Route Primitives

**Files:**
- Create: `src/search/bounded_search.py`
- Test: `tests/test_bounded_search.py`

**Interfaces:**
- Produces: `freeze_state(value: Any) -> Any`
- Produces: `bounded_search(start, successors, is_goal, heuristic=None, max_nodes=40000, max_depth=200, seconds=3.0) -> dict`
- Produces: `route(mask, start, goals, moves=None) -> dict`

- [ ] **Step 1: Write the failing test**

Create `tests/test_bounded_search.py`:
```python
def test_freeze_state():
    from src.search.bounded_search import freeze_state
    d = {"b": 2, "a": [1, {"x": 3}]}
    frozen = freeze_state(d)
    assert hash(frozen) is not None

def test_bounded_search_simple():
    from src.search.bounded_search import bounded_search
    # Search from 0 to 5
    res = bounded_search(0, lambda s: [("INC", s + 1)], lambda s: s == 5)
    assert res["status"] == "solved"
    assert res["actions"] == ["INC"] * 5
    assert res["cost"] == 5.0

def test_route_simple_grid():
    from src.search.bounded_search import route
    # 3x3 open grid
    mask = [[True, True, True], [True, True, True], [True, True, True]]
    res = route(mask, (0, 0), [(2, 2)])
    assert res["status"] == "solved"
    assert res["cost"] == 4
    assert len(res["actions"]) == 4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_bounded_search.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.search.bounded_search'`

- [ ] **Step 3: Implement `src/search/bounded_search.py`**

Implement `freeze_state`, `bounded_search`, and `route` with strict monotonic deadlines and depth bounds.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_bounded_search.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/search/bounded_search.py tests/test_bounded_search.py
git commit -m "feat: add state freezing, bounded search, and route grid search primitives"
```

---

### Task 3: Adaptive JSON Memory Manager

**Files:**
- Create: `src/utils/adaptive_memory.py`
- Test: `tests/test_adaptive_memory.py`

**Interfaces:**
- Produces: `normalize_notes(notes: dict, level: int, max_bytes: int = 16384) -> dict`
- Produces: `solved_evidence(history: list[dict]) -> list[dict]`

- [ ] **Step 1: Write the failing test**

Create `tests/test_adaptive_memory.py`:
```python
def test_normalize_notes_bounds_and_reset():
    from src.utils.adaptive_memory import normalize_notes
    notes = {"game": {"rule": "doors open on yellow"}, "level": {"key": 1}, "_level": 1}
    # Stay on level 1
    norm = normalize_notes(notes, level=1)
    assert norm["level"] == {"key": 1}
    assert norm["game"]["rule"] == "doors open on yellow"

    # Advance to level 2 -> level notes cleared, game notes preserved
    norm2 = normalize_notes(norm, level=2)
    assert norm2["level"] == {}
    assert norm2["game"]["rule"] == "doors open on yellow"
    assert norm2["_level"] == 2

def test_normalize_notes_oversized_rejected():
    import pytest
    from src.utils.adaptive_memory import normalize_notes
    huge_notes = {"game": {"data": "x" * 20000}, "level": {}, "_level": 1}
    with pytest.raises(ValueError, match="16 KiB memory limit"):
        normalize_notes(huge_notes, level=1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_adaptive_memory.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `src/utils/adaptive_memory.py`**

Implement `normalize_notes` with JSON round-trip validation and `solved_evidence` to extract attempt tails and action counts from history without prompt injection.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_adaptive_memory.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/utils/adaptive_memory.py tests/test_adaptive_memory.py
git commit -m "feat: add bounded 16 KiB JSON memory manager and solved evidence tracker"
```

---

### Task 4: Verified Execution & Model Checker

**Files:**
- Create: `src/search/verified_executor.py`
- Test: `tests/test_verified_executor.py`

**Interfaces:**
- Produces: `check_model(predict_fn, encode_fn, transitions: list, limit: int = 24) -> dict`
- Produces: `make_verified_executor(get_frame_fn, act_fn)` returning `follow_plan(plan, predict_fn, encode_fn, max_actions=6)`

- [ ] **Step 1: Write the failing test**

Create `tests/test_verified_executor.py`:
```python
def test_follow_plan_stops_on_mismatch():
    from src.search.verified_executor import make_verified_executor
    frames = [{"val": 0}, {"val": 1}, {"val": 2}]
    idx = [0]
    def get_frame():
        return frames[idx[0]]
    def act(actions):
        idx[0] += len(actions)
        return {"executed": True, "executed_count": len(actions)}
    
    executor = make_verified_executor(get_frame, act)
    # Predicts increment by 1
    predict = lambda s, a: s + 1
    encode = lambda f: f["val"]
    
    # Plan with 3 actions, but frame 2 matches prediction. Suppose we give wrong prediction for step 2:
    predict_bad = lambda s, a: s + 2
    res = executor(["R", "R"], predict_bad, encode)
    assert res["stop"] == "prediction_mismatch"
    assert res["executed"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_verified_executor.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `src/search/verified_executor.py`**

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_verified_executor.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/search/verified_executor.py tests/test_verified_executor.py
git commit -m "feat: add check_model and verified executor follow_plan"
```

---

### Task 5: Build Duck V17 Submission Package & Generator

**Files:**
- Create: `scripts/build_duck_v17.py`
- Create: `submissions/duck_v17/kernel-metadata.json`
- Create: `submissions/duck_v17/apply_enhancements_v17.py`
- Modify: `submissions/duck_v17/notebook.ipynb` (generated)
- Test: `tests/test_duck_v17_notebook.py`

**Interfaces:**
- Produces: `build_duck_v17.py` generates clean, standalone notebook with:
  1. `SERVER_STARTUP_TIMEOUT = 55 * 60`
  2. `os.environ['ARC3_WARMUP_ACTION_GAMES'] = '1'`
  3. `os.environ['ARC3_HTTP_RETRY_INITIAL_SECONDS'] = '900'`
  4. Embedded `solve_toggle`, `route`, `bounded_search`, `normalize_notes`, `follow_plan`
  5. Duck V12/V15 foundation with temperature 0.6 and Fable 30k calibration.

- [ ] **Step 1: Write the failing test**

Create `tests/test_duck_v17_notebook.py`:
```python
def test_duck_v17_notebook_structure():
    import json
    from pathlib import Path
    nb_path = Path("submissions/duck_v17/notebook.ipynb")
    assert nb_path.exists()
    with open(nb_path) as f:
        nb = json.load(f)
    assert len(nb["cells"]) > 20
    text = json.dumps(nb)
    assert "SERVER_STARTUP_TIMEOUT = 55 * 60" in text or "55 * 60" in text
    assert "ARC3_WARMUP_ACTION_GAMES" in text
    assert "ARC3_HTTP_RETRY_INITIAL_SECONDS" in text
    assert "solve_toggle" in text
    assert "bounded_search" in text
    assert "normalize_notes" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_duck_v17_notebook.py -v`
Expected: FAIL because `submissions/duck_v17/notebook.ipynb` does not exist yet.

- [ ] **Step 3: Implement `scripts/build_duck_v17.py` and run it to produce the submission notebook**

Build `scripts/build_duck_v17.py`, synthesize all components into the validated notebook, and write `submissions/duck_v17/kernel-metadata.json`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_duck_v17_notebook.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/build_duck_v17.py submissions/duck_v17/ tests/test_duck_v17_notebook.py
git commit -m "feat: build Duck V17 submission package with infra armor and adaptive tools"
```

---

### Task 6: Autonomous Kaggle Submission Daemon (`auto_submit_duck_v17.py`)

**Files:**
- Create: `scripts/auto_submit_duck_v17.py`
- Test: Execute dry-run flag verification on `scripts/auto_submit_duck_v17.py`

- [ ] **Step 1: Write `scripts/auto_submit_duck_v17.py`**
- [ ] **Step 2: Verify dry-run push and submission limit checks**
- [ ] **Step 3: Commit**

```bash
git add scripts/auto_submit_duck_v17.py
git commit -m "feat: add autonomous submission script for Duck V17"
```

---

### Task 7: Full Verification Suite Run

**Files:**
- Execute: `python3 -m pytest tests/ -q`

- [ ] **Step 1: Run all test suites across the repository**
Expected: 95+ tests passed, 0 failures.
- [ ] **Step 2: Update `docs/experiments.md` with Duck V17 architecture notes**
- [ ] **Step 3: Commit**

```bash
git add docs/experiments.md
git commit -m "docs: record Duck V17 architecture in experiments ledger"
```
