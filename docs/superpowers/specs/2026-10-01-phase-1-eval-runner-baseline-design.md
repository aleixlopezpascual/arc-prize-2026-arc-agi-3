# Phase 1 Design: Local Evaluation Runner, Baseline Benchmarking & Submission Packaging

- **Date:** 2026-10-01
- **Status:** Approved
- **Target Competition:** Kaggle `arc-prize-2026-arc-agi-3` (ARC Prize 2026 - ARC-AGI-3)

---

## 1. Executive Summary

Phase 1 establishes the empirical foundation for competitive development in ARC-AGI-3. The system enables:
1. Fast, reproducible offline evaluation of AI agents against the 25 public environment games in `input/environment_files/` using the official ARC-AGI execution engine.
2. Exact competition metric scoring via `src/metrics.py` (efficiency-squared level scoring, 1-indexed difficulty weighting, and arithmetic mean across games).
3. Implementation and evaluation of two baseline agents: `RandomAgent` (exploration lower bound) and `StochasticGoose` (Milestone 1 CNN action learner).
4. Automated packaging into self-contained Kaggle submission notebooks capable of running against the competition rerun gateway at `http://gateway:8001/` with fallback parquet generation for notebook commits.
5. Persistent experiment logging into `docs/experiments.md`.

---

## 2. System Architecture & Components

```
arc-prize-2026-arc-agi-3/
├── src/
│   ├── config.py                 # Paths, public games list, env constants
│   ├── metrics.py                # Pure competition metric computation
│   ├── evaluate.py               # Offline evaluation runner across public games
│   ├── package_submission.py     # Automated notebook packager for Kaggle
│   └── agents/
│       ├── __init__.py           # Agent registry (AVAILABLE_AGENTS)
│       ├── base.py               # Abstract BaseAgent contract
│       ├── random_agent.py       # Random baseline agent
│       └── stochastic_goose.py   # CNN action learner baseline (Tufa Labs)
├── tests/
│   ├── test_metrics.py           # Metric calculation tests (10/10 passing)
│   ├── test_evaluate.py          # Runner integration & mock tests
│   └── test_package_submission.py# Packaging validation tests
├── docs/
│   ├── competition-brief.md      # Strategic overview & constraints
│   ├── experiments.md            # Experiment tracking ledger
│   └── superpowers/specs/        # Architectural specifications
└── submissions/                  # Output submission notebooks (.ipynb)
```

---

## 3. Detailed Component Specifications

### 3.1. Unified Agent Contract (`src/agents/base.py`)
All agents adhere to a standardized interface compatible with ARC-AGI-3:
- `choose_action(frames: list[FrameData], latest_frame: FrameData) -> GameAction`: Returns selected action (e.g. `RESET`, `ACTION1`-`ACTION5`, `ACTION6(x, y)`, `ACTION7`).
- `is_done(frames: list[FrameData], latest_frame: FrameData) -> bool`: Signals whether the agent should terminate play (default: stops on `WIN` or `GAME_OVER`).
- `reset() -> None`: Clears internal episode memory between games.

### 3.2. Baseline Agents (`src/agents/`)
1. **`RandomAgent` (`src/agents/random_agent.py`):**
   - Reads `latest_frame.available_actions`.
   - Selects uniform random actions from simple actions, generating valid `(x, y)` coordinates if `ACTION6` is chosen.
   - Provides a sanity check for the evaluation pipeline.
2. **`StochasticGoose` (`src/agents/stochastic_goose.py`):**
   - Ports the Tufa Labs Milestone 1 winning architecture.
   - Converts 64×64 grids (0–15 color integers) into one-hot / normalized multi-channel feature maps + temporal step diffs.
   - Uses a compact CNN backbone to predict action distributions with epsilon-greedy exploration.
   - Updates weights upon level advancement or positive feedback.
   - Automatically utilizes Apple Silicon `mps` or `cpu` locally, and NVIDIA CUDA in Kaggle notebooks.

### 3.3. Offline Evaluation Engine (`src/evaluate.py`)
- **CLI Options:**
  - `--agent`: Registered agent name (`random`, `stochastic_goose`).
  - `--games`: Comma-separated game IDs (e.g. `ls20,ar25`) or `--all` for all 25 public games. Default: 3-game smoke test (`ls20,ar25,dc22`).
  - `--max-actions`: Action cap per level (default: 400) to protect against infinite exploration.
  - `--log-ledger`: Boolean flag to append results to `docs/experiments.md`.
- **Simulation Loop:**
  - Configures `OPERATION_MODE=offline` pointing to `input/environment_files/` using the official `Arcade` execution engine.
  - Tracks per-level: `baseline_actions`, `actions_taken`, and `completed`.
  - Calculates per-game score and total competition score via `src/metrics.py`.
  - Prints formatted terminal summary table.

### 3.4. Submission Packager (`src/package_submission.py`)
- Generates a standalone Jupyter notebook (`submissions/submission_<agent_name>.ipynb`) containing:
  - **Cell 1:** Offline wheel installation from `/kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels`.
  - **Cell 2:** Self-contained agent code written into `/kaggle/working/my_agent.py`.
  - **Cell 3:** Rerun gateway runner: polls `http://gateway:8001/api/games`, configures `.env`, registers agent into `ARC-AGI-3-Agents`, and runs `python main.py --agent myagent`.
  - **Cell 4:** Interactive edit mode fallback: generates dummy `submission.parquet` with columns `['row_id', 'game_id', 'end_of_game', 'score']` ensuring successful notebook save.

---

## 4. Testing & Verification Plan

1. **Unit Tests (`tests/test_metrics.py`):**
   - 10 unit tests already passing covering zero guards, efficiency quadratics, level weighting, and multi-game averaging.
2. **Evaluation Integration Tests (`tests/test_evaluate.py`):**
   - Verify that `evaluate.py` correctly runs `RandomAgent` on a smoke game (`ls20`) offline without crashes and computes a non-negative score.
3. **Packaging Validation Tests (`tests/test_package_submission.py`):**
   - Verify that `package_submission.py` creates a valid `.ipynb` file containing all 4 cells and correct syntax.

---

## 5. Experiment Tracking & Success Criteria

- Successful execution of smoke test on `ls20,ar25,dc22` for both `RandomAgent` and `StochasticGoose`.
- Full 25-game benchmark recorded in `docs/experiments.md`.
- Generated submission notebook verified in `submissions/`.
