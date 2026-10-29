# New & Unconsidered Public Notebooks Intelligence: ARC-AGI-3

*Date: October 30, 2026*  
*Harvested & Inspected from Kaggle Competition API (`arc-prize-2026-arc-agi-3`)*

---

## Executive Summary: Key Insights from the New Notebooks

A comprehensive deep-dive into newly posted, top-scoring, and unconsidered public kernels (downloaded to `notebooks/public_baselines/inspections/`) reveals several pivotal breakthroughs that redefine competition strategy:

1. **The Harness IS the Score (Gap Analysis by Cosmorin)**:
   Top leaderboard scores (71.48 by Fields Model, 68.91 by Tufa Labs) do **not** stem from larger models or in-run training; every top team freezes base weights (Qwen 27B INT4/W4A16). Performance is governed by **scaffolding discipline**: memory persistence, KV-cache-preserving prompt hygiene, and compute scheduling. A minor bug in a dynamic scheduler dropped a verified 45.32 baseline to 10.24 (-35 points).
2. **Oracle Calibration: Completion Loss (50.30) vs Efficiency Loss (2.30)**:
   Mathematical decomposition of 100 runs reveals that **50.30 of the 52.61 missing points are pure completion loss** (failing to finish levels). Action efficiency only accounts for **2.30 points**. Even provably optimal action sequences on cleared levels would only lift the score by 2.30 points. Crucially, **25.6% of all actions are wasted on levels that are never completed**.
3. **The Leaderboard is a Max-Statistic (Tantan0327 Paper Track)**:
   Repeated runs of identical code show an individual submission standard deviation of $\sim 3.0$ points. Leaderboard scores represent the maximum of independent draws, resting $\sim 2.0$ points above the true mean.
4. **"Slow, Not Stuck" Phenomenon**:
   Games historically deemed "unsolvable" steadily clear levels when given continuous 60-minute time slots. Hard token cutoffs (e.g., aborting at 110k tokens) severely penalized scores (-9.1 points) by killing solvable games like `r11l` and `ar25`.
5. **Inference Audit & Anti-Stagnation Probing (Stack S16 by Ondrewsha)**:
   Agents frequently hallucinate false rules ("UP does nothing", "doors are decorative") from a single sample and doubt correct goals. The **H3v2 Inference Audit** injects direct empirical probes (untried actions, unclicked objects, single-state retries) whenever stagnation is detected ($\ge 20\text{k}$ tokens without action).
6. **Infrastructure Hardening (Cold-Start Hold & Keepalive)**:
   Kaggle container startup latency currently delays notebook execution by up to 40 minutes, burning into the 9-hour submission budget. Extended server timeouts (55–90 min) and periodic `RESET` keepalives prevent premature 0.00 failures.

---

## Detailed Notebook Analyses

### 1. `ondrewsha/arc-agi-3-stack-s16` (Stack S16)
*Author*: Андрей Рябов (ondrewsha) | *Base*: Daniel Franzen M2 + TAAF  
*Local Inspection Directory*: `notebooks/public_baselines/inspections/stack-s16/`

#### Key Architectural Components:
- **H3v2 Inference Audit (`install_inference_audit`)**:
  - *Trigger Condition*: Fires when level tokens $\ge 30\text{k}$ (then every $+30\text{k}$), when $\ge 20\text{k}$ tokens are generated without executing an action (stagnation), or when $\ge 3$ assistant turns declare a goal impossible.
  - *Direct Intervention*: Computes a real-time coverage report and injects an actionable instruction at the top of the user prompt:
    > *"Unless your plan is making verified progress, do this now, one action at a time, comparing the board before and after: try each untried action once; click one or two never-clicked objects; retry the one-state action in another state."*
  - *HUD & Budget-Bar Masking*: Filters out budget bars, frames, and background regions ($\ge 10\%$ area) from click targets so the agent does not waste moves clicking HUD letters.
- **H1 Solved-Level Memory v1.1 (`install_level_memory`)**:
  - Upon level completion, prompts the agent: `"LEVEL {n} SOLVED... write one short paragraph that starts with 'Rule for level {n}:' -- the goal, controls, and winning plan (<= 5 lines)."`.
  - Appends the distilled rule block to the **end of the system prompt only when history is trimmed/evicted**, preserving 100% of the SGLang KV cache prefix during active play.
- **SCH Priority Scheduler Calibration**:
  - `ARC3_PRIORITY_HUMAN_ACTIONS = 100` (up from 25): Keeps high-value, deep final levels (e.g., `tr87` L6 with 146 human actions) from decaying prematurely into starvation.
  - `ARC3_PRIORITY_TOKEN_SCALE = 40000` (down from 62000): Stagnant levels decay faster, conceding slots to active winners.
- **Harness Throughput Optimizations (TP & K3)**:
  - `ARC3_RESUME_PROMPT_IMAGES = 0` (K3): Avoids resending duplicate board images on resumption turns (+1.5% token economy).
  - Frame history serialized once per frame and read from memory (TP).
- **GW Start Retry & KA Keepalive**:
  - Retries initial game `RESET` up to 4 times (prevents a single startup drop from crashing the shared scorecard).

---

### 2. `cosmorin/why-1-is-1-arc-agi-3-gap-analysis` (Why #1 Is #1)
*Author*: cosmorin | *Local Inspection Directory*: `notebooks/public_baselines/inspections/gap-analysis/`

#### Empirical Autopsy & Findings:
- **The Score is the Scaffolding**:
  - Gold threshold: 38.22; #1: 71.48; baseline: ~23.39.
  - SOTA teams do **not** train weights inside the run. Test-Time Training (TTT) is an engineering trap: server restarts take $\sim 17$ minutes, wipe the KV cache, and model capacity is saturated by inference alone.
- **The Fatal Dynamic Scheduler Experiment**:
  - Replaced flat per-session budget with a dynamic remaining-budget divider.
  - Collapsed session deadlines from 29,500s to 900s; 96 of 100 runs terminated at 100 minutes. Score crashed from **45.32 down to 10.24 (-35 points)** with identical weights.
  - *Lesson*: Generous, flat per-session caps strictly beat clever dynamic starvation.
- **Transcript Autopsy**:
  - **Depth Truncation**: 100% of runs spent zero actions beyond the first un-cleared level.
  - Stalls burn 1,584 tokens/action vs 760 tokens/action on successful clears.
  - Board change does not equate to progress: unique board rate remained 0.96 during unproductive loops.
  - *Key Distilled Heuristic*: When stalled, immediately switch to cheap probe actions instead of generating elaborate deliberations.

---

### 3. `cosmorin/arc-agi-3-oracle-calibration-completion-vs-waste`
*Author*: cosmorin | *Local Inspection Directory*: `notebooks/public_baselines/inspections/oracle-calibration/`

#### Mathematical Score Decomposition (100 Runs, Mean 47.39):
$$\text{Missing Points (52.61)} = \text{Completion Loss (50.30)} + \text{Efficiency Loss (2.30)}$$

- **The Baseline Shield**:
  - In ARC-AGI-3 RHAE scoring, level score is $\min(115, (\text{baseline}/\text{actual})^2 \times 100)$ weighted by level number.
  - If a level is finished within the human baseline, extra inefficiency is capped and essentially free. Only 25 of 134 completed levels exceeded the baseline.
- **The Sunk Budget Sink**:
  - **25.6% of all actions** (5,432 / 21,217) were spent on levels that were never completed.
  - E.g., `su15` L4 is solvable in **9 actions**; the agent burned 309 actions across 4 passes without finishing.
- **Two Identifiable Action-Stream Bugs**:
  - *Pattern A (Cyclic Palette Clicks)*: Repeating clicks on identical coordinates without state change (e.g., `sc25` repeated 169 of 207 clicks).
  - *Pattern B (RESET-Separated Plan Repeats)*: Repeating the identical movement path after dying/resetting instead of altering the plan (e.g., `tu93`).

---

### 4. `tantan0327/arc3-paper-cpu-reproduction` (Paper Track Reproduction)
*Author*: red-down (tantan0327) | *Repository*: `github.com/tantan0327/arc-agi-3-agent`  
*Local Inspection Directory*: `notebooks/public_baselines/inspections/paper-cpu-repro/`

#### Key Findings from *"The agent starts like an agent and stops like a coin flip"*:
1. **Leaderboard as a Max-Statistic**:
   - Evaluated daily submissions: standard deviation is $\sigma \approx 3.0$ at the 27-point mark.
   - Leaderboard score is the maximum of $N$ submissions, hovering $\sim 2.0$ points above the true mean.
2. **Allocation Simulator (`sched_sim.py`)**:
   - Event-driven simulation based on 213 real trajectories (`data/traces.json`). Proves that queue egalitarianism (removing `fresh_floor`) and $D'$ priority routing strictly outperform round-robin.
3. **"Slow, Not Stuck"**:
   - Solvable "hard" games take 40–60 minutes toInduce rules. Premature timeout allocation kills them.
4. **Symbolic Theory Induction & Goal Census**:
   - Fits transition theories and tracks which color the avatar enters on level-completing moves (goal census), driving a BFS theory planner without LLM calls.

---

### 5. `laimerbotrolenk/lb-score-31-21` (Adaptive Duck 31.21 LB)
*Author*: Laimer Botrolenk | *Score*: **31.21% LB**  
*Local Inspection Directory*: `notebooks/public_baselines/inspections/lb-score-31-21/`

#### Core Additions to Sandbox Globals:
- `board(frame)` & `scene(frame, colors, max_objects)`: Extracts connected components, inclusive bounding boxes, pixel areas, and interior centroid click coordinates.
- `bounded_search(start, successors, is_goal, heuristic, max_nodes=40000, max_depth=200, seconds=3.0)`: Uniform-cost search / A* with admissible heuristics and cycle pruning.
- `route(mask, start, goals, moves)`: Fast BFS grid pathfinder.
- `solve_toggle(button_masks, target, n_cells, max_nullity=18)`: Gaussian elimination over GF(2) with nullspace enumeration for minimum-click binary XOR switch puzzles.
- `check_model` & `make_verified_executor` (`follow_plan`): Replays observed transitions against an inferred simulator, executing actions and halting immediately at the first discrepancy.
- `normalize_notes(notes, level, max_bytes=16384)`: 16 KiB bounded JSON memory separating game and level scopes.

---

### 6. `bhuvneshrichhariya/arc3-silver-exp015-memory-coldstart` (Coldstart Hold)
*Author*: Bhuvnesh Richhariya | *Base*: EXP-002 + D' Priority + SLM  
*Local Inspection Directory*: `notebooks/public_baselines/inspections/memory-coldstart/`

#### Technique:
- **`_install_coldstart_hold(solver_mod)`**:
  - Intercepts `_HarnessGameSession._play_inner`.
  - Claims a warmup slot and, while the analyzer endpoint `/health` is unreachable, issues `_execute_auto_reset()` every 480 seconds (up to 3,000s / 50 min).
  - Keeps the Kaggle Gateway connection alive during slow 40+ minute model weight loading, completely eliminating 0.00 timeouts.

---

### 7. `habanwer/arcaid3-lexicon-view-dfranzen-m2` (ARCAID3 Lexicon View)
*Author*: Shehab Anwer | *Votes*: 37  
*Local Inspection Directory*: `notebooks/public_baselines/inspections/lexicon-view/`

#### Technique:
- Exposes `current_frame.code` (grid as multi-color symbol tiles with stable symbolic names) and `current_frame.objects`.
- **`scale_lock()`**: Enforces consistent block size per level across history frames to prevent sparse boards from flipping resolution.
- `current_frame.rules`: Inductive grammar learning (`when <action> [if <rel>] then <change>`) from observed state transitions.

---

### 8. `samuraiiii/priced-curiosity-ec` (Priced Curiosity)
*Author*: Satyam | *Local Inspection Directory*: `notebooks/public_baselines/inspections/priced-curiosity/`

#### Exact Marginal RHAE Cost Formulation:
- Computes exact drop in score for taking $k$ exploratory actions:
  $$d_k(A, B, k) = s(A, B) - s(A+k, B)$$
- Calculates threshold action count $a$ where marginal action cost drops below exploration benefit $\theta$:
  $$\text{thr\_approx}(B, k, \ell, L, \theta) = \left(\frac{2 k \ell B^2}{W \cdot \theta}\right)^{1/3}$$
- Implements `status_mask(g)` to automatically identify edge HUD and budget bars based on aspect ratio ($\ge 5$ or $\le 0.2$) and duplicated twins along borders.

---

### 9. `vickyfym/arc-agi-3-lalalia-final` (Lalalia 31.46 LB)
*Author*: Yiming Fang | *Score*: **31.46% LB**  
*Local Inspection Directory*: `notebooks/public_baselines/inspections/lalalia-final/`

- Paper Track entry *"Luck, Tokens and Memory: What Moves a Single-GPU LLM Agent on ARC-AGI-3"*.
- Verifies that appending solved-level summaries strictly during context eviction preserves prefix caching while boosting cross-level knowledge transfer.
- Implements `SERVER_STARTUP_TIMEOUT = 55 * 60` to survive platform latency.

---

## Synthesis & Comparison: Public Landscape vs Our Agent Lineage

| Capability / Strategy | Franzen M2 Baseline | Stack S16 (Ondrewsha) | Adaptive Duck 31.21 | Cosmorin Calibration | **Our Current Stack (Duck V20/V21)** |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Public LB Score** | 27.89% (33.68 V1) | ~30–31% (exp) | 31.21% | 26.16 LB (47.39 offline) | **30.22% (Practice) -> Target 35%+** |
| **Startup Shield** | 12m Timeout (Fragile) | 150m Wait + Keepalive | 12m Timeout | 90m Wait | **55m Timeout + Warmup Keepalive** |
| **Inference Audit** | ❌ None | **✅ H3v2 Stagnation Probes** | ❌ None | ❌ None | 🔄 In Development (Introspection Hint) |
| **Memory Retention** | ❌ Evicted | **✅ H1 Level Memory (eviction)**| ✅ 16 KiB JSON Notes | ✅ Rules in prompt | **✅ Solved-Level Memory + Win Cache** |
| **Scheduler Engine** | Round-Robin + Fresh-First | Calibrated Weights (100/40k)| Round-Robin | Flat Caps | **✅ Full $D'$ Priority Engine** |
| **Search & Geometry** | Basic ASCII + Zoom | Edge Band Filter | **✅ BFS, A*, XOR Solver** | Pattern A/B Guards | **✅ 5px Centroids, BFS, Retained Funcs**|
| **VRAM Safety** | 0.96 (OOM Spikes) | 0.96 | 0.96 | 0.93 | **✅ 0.93 (`expandable_segments:True`)** |

---

## Actionable Takeaways for Immediate Integration

1. **Adopt H3v2 Inference Audit Probing**:
   When the agent generates $>20\text{k}$ tokens without action or repeats identical coordinates (Pattern A), inject an empirical probe list: untried actions, never-clicked objects (excluding edge status bars), and single-state actions.
2. **Prioritize Completion Over Efficiency**:
   Do not terminate or over-constrain actions on levels that are still within or near human baseline. Never enforce hard token cutoffs (e.g. 110k cutoff), but decay scheduler priority via $D'$.
3. **Guard Against Sunk Action Sinks**:
   Detect Pattern A (cyclic palette clicking) and Pattern B (re-executing identical paths post-RESET). If no state change occurs after 3 repeated clicks or an identical retry fails, force an exploratory probe.
4. **Lock SGLang Prefix Cache at All Costs**:
   Memory and rule summaries must only be appended during eviction/trim events, never prepended or modified dynamically per turn.
