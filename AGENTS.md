# Repository Guidelines & Agent Operational Manual: ARC Prize 2026 - ARC-AGI-3

## 1. Project Purpose & Current Standing
This repository contains competitive agent implementations, evaluation harness code, perception and diagnostic modules, and submission pipelines for Kaggle's **ARC Prize 2026 - ARC-AGI-3** competition (`arc-prize-2026-arc-agi-3`).

- **Official Leaderboard Standing:** Team `Aleix López`, Rank **#362** (out of ~800+ teams).
- **Official Best Score:** **`30.19%`** (Ref `56836213`, Duck Centroid V1).
- **Latest Evaluated Submission:** **`Duck V11`** (Ref `57138832`, `49.27%` demo benchmark with 2 sweeps).
- **Reliability:** 10 / 10 clean Kaggle executions (0 crashes, 0 timeouts, 0 invalid parquet outputs).

---

## 2. Competition Environment & Serving Architecture

All production submissions operate on Kaggle's designated hardware:
- **Hardware Target:** Single **Nvidia RTX Pro 6000** GPU (48GB VRAM).
- **Docker Image:** Must be pinned to Python 3.12 (`gcr.io/kaggle-private-byod/python@sha256:57e612b484cf3df5026ee4dcc3cb176974b22b2bc0937fb1e16132a8be4cb13c`) because the Pennyroyal SGLang wheelhouse requires native `cp312` wheels.
- **Model Backbone:** `Qwen/Qwen3.8-Flash-Next` quantized with Intel AutoRound (`W4A16`), paired with `albucino/Qwen3.8-Flash-Next-W4A16-FP8PLE` (MTP draft model) for speculative decoding.
- **Serving Engine:** Pennyroyal SGLang v2.5.3 (John Pezzulli fork) achieving ~950–1,150 tokens/sec decode throughput.
- **Context Management:** 128k context window with hysteresis trimming (drops 58k tokens at 118k ceiling to maintain $>93\%$ RadixAttention prefix cache hit rate).
- **Competition Execution Limits:**
  - Submission rerun: 110 unseen private games executed concurrently over a strict 9-hour window.
  - Daily submission allowance: **1 submission per team per day**, resetting at **00:00 UTC**.

---

## 3. Core Engineering Invariants

### 3.1. Zero-Prompt-Drift Prefix Caching Rule
**NEVER inject dynamic, changing text into system prompts or early prompt prefixes.**  
SGLang's throughput relies on RadixAttention prefix caching. Invalidate the prefix, and decode speeds plummet from 1,000 tok/s to <200 tok/s.
- All cross-level memory (`solved_memory`) and reference budgets (`level_baseline`) must be passed **strictly via JSON runtime state** into the Python tool sandbox (`FrameView.solved_memory`, `FrameView.level_baseline`).
- Prompt templates in `prompts.py` must remain 100% byte-static across all levels.

### 3.2. Guaranteed Round-Robin Scheduling Rule
**NEVER adopt priority formulas that starve unstarted games (such as Shiiin9's $D'$).**  
In the 110-game private competition set, every single game must be guaranteed initial active rounds (`gate.acquire(_PRIORITY_UNTRIMMED_BASE - self._queue_position())`) so that all easy and medium games get on the board before pruning.

### 3.3. Unconstrained Token Allocation Rule
**NEVER hardcode an artificial per-game token sink cap (such as 185k tokens).**  
Deep multi-stage puzzles requiring 8–10 levels consume 200k–300k tokens to solve their highest-value levels. Let Franzen's natural Priority Snapshot formula $P=(A+B)\cdot C$ deprioritize stalled games gracefully without hard cutoff abortion.

### 3.4. Dynamic Wheelhouse Resolution Rule
In Kaggle sessions, competition datasets may mount under either `/kaggle/input/competitions/arc-prize-2026-arc-agi-3/` or `/kaggle/input/arc-prize-2026-arc-agi-3/`.  
Always resolve the wheelhouse dynamically:
```python
wheelhouse = next(
    iter(sorted(Path("/kaggle/input").glob("**/arc_agi_3_wheels"))),
    Path("/kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels"),
)
```

### 3.5. Sampling Temperature Invariant
Set `LOCAL_ANALYZER_TEMPERATURE = '0.6'`.  
Temperature 0.6 reduces spatial coordinate arithmetic errors, eliminates syntax retries, and drops total actions by >23% (under 1000 actions across 10 demo games), maximizing the squared efficiency score.

---

## 4. Directory Layout & Key Modules

```
├── src/
│   ├── config.py                           # Paths, constants, and 25 public game list
│   ├── metrics.py                          # Official competition squared-efficiency metric
│   ├── evaluate.py                         # Offline local evaluation runner
│   ├── agents/
│   │   ├── base.py                         # BaseAgent abstract interface
│   │   ├── random_agent.py                 # Random baseline agent
│   │   ├── stochastic_goose.py             # CNN-based public baseline agent
│   │   └── search_agent.py                 # Centroid & search-guided agent
│   ├── guards/
│   │   └── noop_repeat_guard.py            # Guard against repeated zero-effect actions
│   ├── perception/
│   │   ├── segmentation.py                 # 8-connected component segmentation, bbox, centroid, is_border
│   │   ├── centroids.py                    # Object centroid extraction and click prioritization
│   │   ├── sandbox_primitives.py           # In-sandbox helpers: candidate_clicks(), object_at(), detect_indicators()
│   │   └── fable_core.py                   # Fable 5 diagnostic engine (small_far_changes, detect_budget, Ledger)
│   ├── search/
│   │   ├── bfs_path.py                     # Native C-speed grid shortest-path BFS
│   │   └── action_selector.py              # Pruned action selection logic
│   └── utils/
│       └── solved_memory.py                # Defensive cross-level solved memory manager
├── submissions/
│   ├── duck_centroid_v1/                   # 30.19% LB Best Working Submission
│   ├── duck_v6/                            # Round-Robin + BFS + 185k Pacing (23.00% LB)
│   ├── duck_v7/                            # Fable 5 Diagnostics + 185k Pacing (24.51% LB, 46.11% Demo)
│   ├── duck_v8/                            # Unconstrained Scheduling + Fable 5 (25.46% LB)
│   ├── duck_v9/                            # Calibrated Fable 30k + Temp 0.6 (27.26% LB, 991 actions)
│   ├── duck_v10/                           # Level Baseline Awareness (26.68% LB, 50.45% Demo, 2 sweeps)
│   └── duck_v11/                           # Action-Budget Prompt Guidance (49.27% Demo, 2 sweeps, PENDING)
├── scripts/
│   ├── auto_submit_duck_*.py               # Autonomous deployment & midnight submit daemons
│   └── build_duck_*_patch.py               # Deterministic patch generators
├── docs/
│   ├── HANDOVER.md                         # Full session handover & state document
│   ├── experiments.md                      # Experiment tracking ledger
│   └── intel/                              # Reverse-engineered competitor intelligence
└── tests/                                  # 67/67 pytest unit & notebook validation tests (100% GREEN)
```

---

## 5. Verification & Testing Standards

- **Pre-Commit Verification:** Run the entire test suite before proposing any change:
  ```bash
  python3 -m pytest tests/ -v
  ```
- **Dry-Run Patch Verification:** Whenever updating enhancement scripts (`apply_enhancements_v*.py`), verify against the bundled `taaf_source` snapshot using a temporary directory dry-run test (see `tests/test_duck_v7.py`).
- **Notebook & Metadata Validation:** Every new submission package must have a dedicated test in `tests/test_duck_v*_notebook.py` confirming JSON syntax, cell counts, kernel metadata IDs, GPU flags, and environment variables.

---

## 6. Official Metric Reference
$$\text{Level Score} = \min\left(100.0, \left(\frac{\text{baseline\_actions}}{\text{agent\_actions}}\right)^2 \times 100.0\right) \quad (\text{if level completed, else } 0.0)$$
$$\text{Game Score} = \frac{\sum_{i=1}^L i \cdot s_i}{\sum_{i=1}^L i}$$
$$\text{Total Score} = \frac{1}{N} \sum_{g=1}^N \text{Game Score}_g \in [0\%, 100\%]$$

Because action efficiency is squared, **every unnecessary exploratory action quadratically penalizes the level score**. Search must be targeted, hypothesis-driven, and budgeted against `current_frame.level_baseline`.
