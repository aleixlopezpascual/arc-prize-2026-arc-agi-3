# Design Document: Duck V7 Architecture (Fable Layer Diagnostic Intelligence + Full Perception Stack)

**Date:** 2026-10-08  
**Author:** Aleix López  
**Status:** Approved for Implementation Planning  
**Target:** ARC Prize 2026 (ARC-AGI-3) — Fuse Duck V6 perception & scheduling with Fable 5 diagnostic intelligence to push LB beyond 35%–40%+

---

## 1. Context & Motivation

### 1.1 Progression & Empirical Learnings
- **Duck Centroid V1 (`30.19%` LB, Rank #152):** Demonstrated the power of geometric object centroids and established the golden rule that Franzen's guaranteed round-robin scheduling (giving all 110 games active rounds before priority pruning) is essential for maximizing aggregate leaderboard score.
- **Duck V4 (`56.81%` Demo Benchmark):** Established a major local benchmark record (+10.09% over V1, 48/65 levels cleared) by introducing sandbox perception primitives (`candidate_clicks()`, `object_at()`, `is_border`, zero-prompt-drift `solved_memory`).
- **Duck V5 (`24.31%` LB):** Fixed the runtime null check and added `bfs_path()`, but proved that Shiiin9's $D'$ queueing starved unstarted games from playing Level 1.
- **Duck V6 (In Flight):** Fused Duck V4/V5 perception & search & null-safety with Franzen's round-robin scheduler and a 185k token sink cap (`bm.solver.max_generated_tokens_per_game = 185000`).

### 1.2 The Opportunity: Fable 5 & Astra Diagnostics
Competitive research from Aleksei Provorov's Fable 5 and the newly published Astra architecture (`vinhdang2006/fable-astra-play-arc-3-handbook-harness`) revealed the primary failure mode of LLM agents on long ARC-3 puzzles:
1. **Lack of Indicator Perception:** Agents frequently fail to notice when a move updates a 2x2 legend mark, score counter, or item tray on the periphery of the board.
2. **Blindness to Step Limits:** Countdown / fuel bars on the edges of the grid deplete silently until the level abruptly resets, wasting the entire action sequence.
3. **Context Collapse on Dragging Levels:** On difficult puzzles taking $>30,000$ tokens, the model loses track of which controls worked in what states and repeats failed action patterns.
4. **The Proven Solution:** Factual, non-speculative diagnostic summaries (computed deterministically by the harness from raw frames) that alert on indicator changes, warn of low fuel, and pin control-effect ledgers only when a level stalls.

---

## 2. High-Level Architecture

```
                       [SGLang Engine (Qwen 3.8 Flash-Next)]
                                         │
            Prompt Templates & Prefix    │  Byte-Static Prefix Cache
            (Preserves >93% Hit Rate)    │  (Unchanged on fast levels)
                                         ▼
                              [ToolAgent Dispatch]
                        ┌────────────────┴────────────────┐
                        ▼                                 ▼
             [Fable Diagnostic Engine]         [Python Tool Sandbox]
             • Small far change detector       • candidate_clicks()
             • Step budget bar run-length      • object_at(r, c)
             • Indicator state memory          • bfs_path(start, goal)
             • Dragging-level pinned log       • current_frame.solved_memory
             • Strict opt-in env flag          • detect_indicators() (new)
               (ARC3_FABLE_LAYER=1)            • detect_budget() (new)
```

### Invariants
1. **Fast-Level Invariance:** Fast levels (<15,000 tokens) receive zero dynamic text in user prompts, keeping SGLang prefix caching at peak efficiency.
2. **Zero-Model Dependency:** All diagnostic facts are computed deterministically from 64x64 integer grids; no LLM calls are made for diagnostics.
3. **Defensive Fail-Open Contract:** Any detector ambiguity, missing key, or unexpected frame shape returns empty/None without raising exceptions.
4. **Environment Isolation:** Fable diagnostics are governed by `ARC3_FABLE_LAYER="1"`. When unset or `"0"`, the harness behaves 100% identically to Duck V6.
5. **Full Backward Compatibility:** Retains all Duck V6 capabilities (`candidate_clicks`, `object_at`, `is_border`, `bfs_path`, null-safe `solved_memory`, Franzen round-robin scheduler, 185k token cap).

---

## 3. Detailed Component Specifications

### 3.1 Core Perception Module (`src/perception/fable_core.py`)
Ported as a pure standard-library module, providing:
- **`diff_cells(a, b)`**: Returns coordinates `(r, c)` differing between two 2D grids.
- **`components8(cells)`**: Computes 8-connected components among changed cells.
- **`_bar_like(before, after, comp, box)`**: Identifies edge-aligned countdown/timer bars to avoid misinterpreting them as game indicators.
- **`small_far_changes(before, after, ...)`**: Identifies small patches (2–16 cells) changing $\ge 8$ cells away from the primary moving object cluster.
- **`detect_budget(frames, min_actions=3)`**: Evaluates frame sequences to detect linear fuel/countdown bars, computing `cap`, `used`, `left`, `rate`, and estimated `remaining` actions.
- **`budget_alert(b, first_time)`**: Generates a single alert line when fuel drops to $\le 25\%$ or $\le 12$ actions remain.
- **`Ledger` class**:
  - Tracks per-key statistics: `n`, `changed`, `noop`, `first_noop`.
  - Estimates `move_signature(key)` (e.g., `"light green cells shifted right 1"`).
  - Maintains `marks` and generates indicator notes (`kind: "first"`, `"lost"`, `"again"`).
  - Emits `key_lines()` and `digest_lines()`.

### 3.2 Sandbox Exposure (`python_tool_sandbox.py`)
Expose lightweight diagnostic helpers inside the Python sandbox REPL:
- **`detect_indicators(before=None, after=None)`**: Programmatically inspects small distant patch changes between two frames.
- **`detect_budget(frames=None)`**: Programmatically inspects current step-budget bar and remaining actions.

### 3.3 Harness Injection & Pinned Level Log (`tool_agent.py`)
Surgically patched into `ToolAgent`:
1. **Methods:** Injects `_fl_on()`, `_fl_core()`, `_fl_sync()`, `_fl_opener_lines()`, `_fl_maybe_pin()`, `_fl_restore_pinned()`, and `_fl_forget_pin()`.
2. **Turn Opener (`_build_user_prompt`):** Appends `self._fl_opener_lines(current_frame, history_entries)` directly after the valid actions line when `ARC3_FABLE_LAYER=1`.
3. **Level Reset:** Calls `self._fl_forget_pin()` on level transitions.
4. **Dragging Level Pinning:** After `ARC3_FABLE_PIN_TOKENS` (default 30,000 tokens on a single level), appends a factual `LEVEL LOG` to history messages and maintains it at the head of history across context trims.

### 3.4 Notebook & Enhancement Patch (`submissions/duck_v7/`)
- **`submissions/duck_v7/apply_enhancements_v7.py`**:
  - Updates `segmentation.py` (bbox, centroid, is_border).
  - Updates `prompts.py` (candidate_clicks, object_at, bfs_path, solved_memory).
  - Updates `python_tool_sandbox.py` (injects helpers).
  - Updates `tool_agent.py` (null-safe solved_memory + Fable layer hooks).
  - Writes `inference/agent/fable_layer_core.py`.
- **`submissions/duck_v7/notebook.ipynb`**:
  - Sets `os.environ["ARC3_FABLE_LAYER"] = "1"`.
  - Sets `bm.solver.max_generated_tokens_per_game = 185000`.
  - Franzen round-robin scheduler active (no Shiiin9 queue overrides).
- **`submissions/duck_v7/kernel-metadata.json`**:
  - ID: `aleixlopez/arc-agi-3-duck-v7`.
  - Title: `ARC-AGI-3 Duck V7`.

---

## 4. Verification Plan

1. **Unit Testing (`tests/test_fable_core.py`):**
   - Test `diff_cells`, `components8`, and `small_far_changes` with mock grids.
   - Test indicator change detection (first mark, mark lost/reverted).
   - Test `detect_budget` and `budget_alert` across a sequence of simulated decreasing bar frames.
   - Test `Ledger` feeding and `move_signature` computation.
2. **Integration & Dry-Run Patch Test (`tests/test_duck_v7.py`):**
   - Dry-run `apply_enhancements_v7.py` against `input/taaf_source/src/ARC3-Inference`.
   - Compile all patched files (`segmentation.py`, `python_tool_sandbox.py`, `tool_agent.py`, `fable_layer_core.py`).
   - Validate that with `ARC3_FABLE_LAYER="0"` and `"1"`, all hooks initialize cleanly.
3. **Notebook & Metadata Validation (`tests/test_duck_v7_notebook.py`):**
   - Verify notebook JSON structure, cells, metadata ID, and environment flags.
