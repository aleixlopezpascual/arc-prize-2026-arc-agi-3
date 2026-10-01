# ARC Prize 2026 - ARC-AGI-3 Competition Brief

## 1. Problem Formulation & Task Overview

**ARC-AGI-3** is an interactive frontier AI benchmark evaluating true generalization, exploration, hypothesis testing, and goal acquisition in unseen, hand-crafted 2D grid environments.

Unlike static ARC tasks (input-output grid pairs) or pre-trained game environments (e.g. Atari), ARC-AGI-3 requires an agent to:
- Interact dynamically with unknown environments through discrete actions.
- Observe multi-channel state grids (up to 64×64 with 16 color states `0`–`15`).
- Discover underlying game rules, transition dynamics, win conditions, and failure states on the fly.
- Advance through sequential levels of increasing difficulty per game.

### Agent Interface
Each agent implements two methods:
1. `choose_action(frames: list[FrameData], latest_frame: FrameData) -> GameAction`: Decides the next action.
   - Available actions: `RESET` (0), `ACTION1`–`ACTION5` (1–5), `ACTION6(x, y)` (6 with coordinates), `ACTION7` (7).
2. `is_done(frames: list[FrameData], latest_frame: FrameData) -> bool`: Determines when to stop exploring or give up on an environment.

---

## 2. Official Evaluation Metric

The competition evaluates **Completion** and **Efficiency** relative to human test-tester baselines.

### Mathematical Formulation
For each game $g \in \{1, \dots, N\}$ with $L$ levels:
1. **Per-Level Score ($s_i$):**
   - If level $i$ ($1 \le i \le L$) is completed:
     $$s_i = \min\left(100.0, \left(\frac{\text{baseline\_actions}_i}{\text{agent\_actions}_i}\right)^2 \times 100.0\right)$$
   - If level $i$ is not completed:
     $$s_i = 0.0$$
2. **Per-Game Score ($\text{Score}_g$):**
   - Levels are weighted by their 1-indexed difficulty: $w_i = i$.
   - The game score is the weighted average across all $L$ levels:
     $$\text{Score}_g = \frac{\sum_{i=1}^L w_i \cdot s_i}{\sum_{i=1}^L w_i}$$
   - Capped at maximum achievable weighted completion:
     $$\text{Score}_g \le \frac{\sum_{i: s_i > 0} w_i}{\sum_{i=1}^L w_i} \times 100.0$$
3. **Total Competition Score:**
   $$\text{Total Score} = \frac{1}{N} \sum_{g=1}^N \text{Score}_g \in [0\%, 100\%]$$

### Key Metric Properties
- **Quadratic Efficiency Penalty:** An agent taking twice as many actions as the human baseline scores only $(1/2)^2 = 25\%$ on that level. Taking 3× actions drops the score to $11\%$. Fast convergence to optimal policies is heavily rewarded.
- **Level Weighting:** Higher levels carry significantly more weight (Level 3 has $3\times$ the weight of Level 1). Solving later levels provides outsized score gains.
- **No Negative Scores:** Incomplete levels simply award 0 points.

---

## 3. Local Validation & Cross-Validation Scheme

### Data & Environment Assets
- **Local Public Games:** 25 games provided in `input/environment_files/`:
  `ar25`, `bp35`, `cd82`, `cn04`, `dc22`, `ft09`, `g50t`, `ka59`, `lf52`, `lp85`, `ls20`, `m0r0`, `r11l`, `re86`, `s5i5`, `sb26`, `sc25`, `sk48`, `sp80`, `su15`, `tn36`, `tr87`, `tu93`, `vc33`, `wa30`.
- **Private Competition Games:** 110 completely unseen games (55 public leaderboard, 55 private leaderboard).

### Validation Strategy: Game-Group Holdout
1. **Zero-Shot Generalization Split:**
   - Partition the 25 public games into 5 folds of 5 games each (stratified by game complexity / mechanics).
   - Never fit game-specific parameters or rules to the evaluation games.
2. **Deterministic Evaluation Harness:**
   - Run agents offline using the bundled `arc_agi` local engine and compute exact `EnvironmentScorecard` values via `src/metrics.py`.
   - Track both macro score (mean over all 25 games) and per-game level completion rates.

---

## 4. Known Community Traps & Operational Constraints

1. **Submission Architecture (Gateway Rerun):**
   - In Kaggle competition re-run mode (`KAGGLE_IS_COMPETITION_RERUN` is set), Kaggle hosts an internal gateway service at `http://gateway:8001/`.
   - The submission notebook must connect to this gateway via `ARC-AGI-3-Agents/main.py` using `OPERATION_MODE=online`.
   - In notebook edit mode, `submission.parquet` with columns `['row_id', 'game_id', 'end_of_game', 'score']` must be written as a fallback so the notebook can commit.
2. **Strict Time Budget (9h / 110 Games):**
   - 9 hours for 110 private games gives **~4.9 minutes per game** across all levels.
   - Any LLM inference or Monte Carlo Tree Search (MCTS) must enforce strict per-move and per-game timeout budgets to avoid notebook timeouts before finishing all games.
3. **Scorecard Idle Timeout:**
   - Scorecards auto-close if inactive for `STALE_MINUTES` (default 15 minutes). The agent loop must maintain active communication or close scorecards gracefully.
4. **Coordinate Action Support (`ACTION6`):**
   - Certain games require `ACTION6` with `(x, y)` coordinates. Agents unable to emit coordinates cannot solve games where click-to-interact is the primary mechanic.
5. **Overfitting to Public Mechanics:**
   - Solutions that rely on hand-crafted heuristics tailored to `ls20` or specific public games will score 0% on unseen private games. Meta-policies, object extraction, and domain-general planning are essential.

---

## 5. Phased Development Roadmap

- **Phase 1: Foundation & Local Metric Engine**
  - Implement and verify exact local metric calculator (`src/metrics.py` and `tests/test_metrics.py`).
  - Configure workspace conventions and automated testing suite.
  - Set up reproducible local evaluation script for public games.
- **Phase 2: Baseline Execution & Kaggle Packaging**
  - Run baseline agents (Random agent and Stochastic Goose / Tufa Labs harness) on local games.
  - Build submission packaging script that creates a Kaggle-ready notebook.
  - Log baseline scores into `docs/experiments.md`.
- **Phase 3: Perception, Modeling & Search**
  - Implement visual state representations (grid diffs, connected component / object detection, change masks).
  - Develop fast forward-model prediction and action-space pruning.
  - Explore hybrid heuristic/MCTS and LLM guidance within the ~4.9 min/game budget.
