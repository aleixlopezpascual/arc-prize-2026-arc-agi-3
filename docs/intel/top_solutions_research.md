# Deep Research: Top Kaggle Notebooks, Milestone Winners & Baseline Architecture Analysis

- **Date:** 2026-10-01
- **Scope:** Competitive intelligence, architectural comparison, and baseline roadmap for Kaggle ARC Prize 2026 (`arc-prize-2026-arc-agi-3`).
- **Sources Analyzed:**
  - Kaggle Leaderboard (Top 30 positions as of October 1, 2026)
  - Milestone 2 Winner Solution & Writeup (Daniel Franzen, Public LB: 27.89%)
  - Milestone 2 2nd & 3rd Place Solutions (Lord Han Solo: 23.84%, Siriki Lohit: 22.53%)
  - Milestone 1 Winner Solution & Writeup (Tufa Labs / Jeroen Cottaar: 1.21% -> 50.65% private)
  - Public Notebooks & Kernels (`tufa-labs-duck-harness`, `duck-qwen3-8-anim-base`, `taaf-flashnext`)
  - Forum Topics #744792, #744758, #717133, #687648, #687655

---

## 1. Executive Summary & Leaderboard Landscape

The leaderboard has undergone a dramatic leap over the past 3 months:
- **Milestone 1 (June 30, 2026):** Winning score was **1.21%** (Tufa Labs "The Duck").
- **Milestone 2 (September 30, 2026):** Top open-source public score surged to **27.89%** (Daniel Franzen), with private leaderboard tops currently reaching **50.65%** (Tufa Labs) and **40.97%** (Yi-Chia Chen).
- **Universal Consensus:** **100% of top-performing teams rely on the Tufa Labs Duck Harness / TAAF (Tufa ARC Action Framework)**. No team using isolated CNNs, raw MCTS, or pure rule-based heuristics is competitive on unseen private test games.
- **The Core Paradigm:** An LLM-in-the-loop agent running inside a stateful Python REPL tool. The game state, frame history, object segmentation, and diffs are exposed as Python objects. The agent writes and executes Python code to inspect boards, test hypotheses, simulate mechanics, and batch action sequences.

### Current Leaderboard Top Tier (as of 2026-10-01)
| Rank | Team / Competitor | Score (%) | Submission Date | Primary Framework & Model |
| :--- | :--- | :--- | :--- | :--- |
| **#1** | **Tufa Labs** | **50.65%** | 2026-09-30 | Proprietary TAAF / Duck evolution |
| **#2** | **Yi-Chia Chen** | **40.97%** | 2026-09-30 | Advanced TAAF / Duck variant |
| **#3** | **gng** | **34.77%** | 2026-10-01 | TAAF / Duck variant |
| **#4** | **markintell** | **34.21%** | 2026-10-01 | TAAF / Duck variant |
| **Top Public** | **Daniel Franzen** (`dfranzen`) | **27.89%** | 2026-09-30 | **TAAF Duck + Qwen3.8-Flash-Next (Milestone 2 Winner)** |
| Public #2 | Lord Han Solo (`lordhansolo`) | 23.84% | 2026-10-01 | TAAF Duck + Qwen3.8-Flash-Next NVFP4 |
| Public #3 | Siriki Lohit (`sirikilohit`) | 22.53% | 2026-09-30 | TAAF Duck + Qwen3.8-Flash-Next AutoRound |

---

## 2. Deep Dive: Top Public Baseline Architectures

### 2.1. The Foundation: Tufa Labs "The Duck" Harness (TAAF)
Authored by Jeroen Cottaar, Dries Smit, Harold Bessis, Isaiah Pressman, Michal Tešnar, and Stefano Viel.
- **Inspirations:** Symbolica’s ARCgentica (sub-agent orchestration) and RGB Agent (OpenCode REPL on execution logs).
- **Key Concepts:**
  1. **Python REPL Tool (`<python_tool>`):** The agent interacts with ARC-AGI-3 not by predicting single token actions, but by writing Python code that directly inspects `current_frame`, `history`, `game_id`, and calls `step(action)`.
  2. **Context Eviction:** Continuously trims older turns while keeping the system prompt and recent evidence.
  3. **Local Serving Stack:** Serves quantized frontier open-source LLMs inside Kaggle’s single GPU (RTX PRO 6000 with 96 GB VRAM) using `sglang` or `vLLM`.

---

### 2.2. The Milestone 2 Breakthrough: Daniel Franzen's Solution (27.89% LB)
Daniel Franzen open-sourced his complete code and writeup on September 30, 2026 (`dfranzen/arc-agi-3-milestone-2-solution`), achieving the highest public benchmark in the competition.

#### A. Model & Serving Architecture
- **Base Model:** **Qwen 3.8 Flash-Next** (massive upgrade over Qwen 3.6 27B and Qwen 3.8 27B).
- **Quantization & Memory Offloading:**
  - Weights: Intel AutoRound W4A16 quantization.
  - PLE Embedding Table: Unquantized BF16 PLE table offloaded to host system RAM (~95 GB).
  - Draft Model: Albucino INT4 MTP (Multi-Token Prediction) draft checkpoint for speculative decoding (3 speculative draft steps).
- **Server:** SGLang Pennyroyal fork (v2.5.3) patched with:
  - Low-M BF16 GEMM for faster matrix multiplication at small batch sizes.
  - Speculative memory budget fix.
  - Checkpoint prefetcher and parallel shard streaming.
- **Throughput:** Achieves ~950–1,150 peak decode tok/s and 10,550 tok/s prefill throughput.

#### B. Cache-Preserving Context Architecture (93.43% Cache Hit Rate)
- **Hysteresis Trimming:**
  - Context window: 131,072 tokens (128 Ki), reserving 12 Ki for output.
  - Traditional trimming drops just enough tokens to fit the next step, which constantly mutates the prompt prefix and forces expensive full re-prefills.
  - Franzen’s hysteresis drops a large block down to ~57 Ki in one go. The retained prefix then remains **100% cache-hot** across subsequent turns, yielding a **93.43% prefix cache reuse rate**!
- **Accurate Image Token Estimation:**
  - Instead of converting characters to tokens with arbitrary heuristics, counts image tokens strictly by grid dimensions and model vision patch/merge layout.
- **Retained Python Functions (`retained_functions.py`):**
  - Ordinary REPL snippets discard variables between calls.
  - Franzen’s harness extracts top-level Python helper functions written by the LLM (using AST parsing and dependency tracking) and restores them in future tool calls across the entire game.
  - Prevents the LLM from burning thousands of generation tokens repeatedly rewriting coordinate helpers, flood-fills, and boundary checks.

#### C. Priority-Based Game Scheduling Across 110 Games
Under Kaggle’s 9-hour limit across 110 games, spending equal time (~4.9 mins/game) is heavily suboptimal.
- **Active Streaming Pool:** 10 active concurrent game streams (matching SGLang’s optimal KV-cache concurrency limit), with all other games waiting frozen in background.
- **Priority Function:**
  $$P = (A + B) \cdot C$$
  - **$A$ (Immediate Score Potential):**
    $$A = \ell \cdot \left(\frac{25}{25 + a}\right)^2 \cdot \frac{55}{N(N+1)/2}$$
    where $\ell$ is current level (1-indexed), $a$ is actions spent on the level, and $N$ is total game levels. Penalizes action inefficiency quadratically matching the competition metric.
  - **$B$ (Continuation Value):** Opportunity to clear subsequent levels (lookup table: $\ge 3$ levels left $\to 8$; 2 levels left $\to 7$; 1 level left $\to 5$; 0 levels left $\to 0$). Fades linearly to 0 in the final 20% of competition runtime.
  - **$C$ (Stall Penalty):**
    $$C = 0.25 \cdot 2^{-(a/115)^2} + 0.75 \cdot 2^{-(t/62000)^2}$$
    Calibrated from 725 empirical level attempts to heavily de-prioritize games that have stalled on tokens $t$ or actions $a$.

#### D. Enhanced Perception & Diagnostics
- **10x Image Upscaling:** Replacing standard 4x with 10x upscaling produced an immediate measurable accuracy boost.
- **Difference Images:** Highlights pixels modified between turns in a distinct visual diff image.
- **Fatal Death Frame Exposure:** On `GAME_OVER`, exposes the exact death frame *before* auto-resetting, allowing the agent to diagnose hazard tiles and fuel/step-bar depletion.
- **Intermediate Animation Frames:** Exposes deduplicated intermediate animation frames and timelines as REPL variables, flagging "transient pixels" (crucial for games like `tn36`).
- **Rotation-Canonical Object Segmentation (`segmentation.py`):**
  Segments 4-connected components and computes rotation-invariant signatures (`_object_signature`) with canonical CW rotation degrees and symmetry orders (1, 2, 4).
- **`frame_diff()` Python Helper:** Exposes a structured diff function directly in Python (`moved`, `rotated`, `appeared`, `disappeared`, `changed_color`, `resized`).

#### E. Action Pruning & Guards
- **`UNDO` Action Exposed:** Exposes `ACTION7` as `UNDO`, enabling backtracking when an action makes a puzzle unsolvable (critical for games like `su15`).
- **No-op Repeat Guard (`noop_repeat_guard.py`):** Hashes interior board states (ignoring HUD/border step bars) and stops repetitive actions that produce 0 gameplay changes.
- **Batch No-op Guard:** Halts remaining actions in a multi-action queue if an action causes no interior change.
- **Stale-State Guard & Terminal-State Guard:** Stops further execution after death or level completion.

---

## 3. Comparison of the Top 3 Milestone 2 Winning Solutions

| Feature / Dimension | #1: Daniel Franzen (27.89%) | #2: Lord Han Solo (23.84%) | #3: Siriki Lohit (22.53%) |
| :--- | :--- | :--- | :--- |
| **Serving Stack** | SGLang Pennyroyal v2.5.3 | vLLM 0.29.1rc1 | SGLang Pennyroyal v2.5.0 |
| **Model Quantization** | AutoRound W4A16 + BF16 PLE | NVFP4 + FP8 mixed + BF16 PLE | AutoRound W4A16 + RadixArk FP8 PLE |
| **Speculative Decoding** | Albucino INT4 MTP (3 draft tokens) | Built-in MTP head (3 draft tokens) | RadixArk NVFP4 MTP (3 draft tokens) |
| **Concurrent Game Streams** | 10 active streams | 14 active streams | 16 active streams |
| **Context Window** | 128 Ki (trimming down to 57 Ki) | 127 Ki (trimming down to 81 Ki) | 69 Ki (trimming down to 45 Ki) |
| **Scheduler Policy** | Dynamic Priority $P=(A+B)\cdot C$ | 3,918s per-game cap, 8 waves | 2,400s slice + UCB scheduler |
| **Function Retention** | Retains Python helper functions across game | Retains tested Python modules | No Python state carried over |
| **Key Differentiator** | Hysteresis cache hit (93.4%), animation REPL | Fast vLLM NVFP4 throughput | Solved-level memory in system prompt |

---

## 4. What Failed: Anti-Patterns Documented by Top Teams

1. **Rigid Text-Based "World Model" Updates:**
   - Both Franzen and Tufa Labs discovered that asking the LLM to output rigid structured markdown summaries (e.g. `### World Model`) frequently broke due to regex parsing errors and polluted context with stale hallucinations.
   - Disabling the rigid world model and letting the model inspect real Python state + rolling context increased scores substantially.
2. **Naive Context Summarization:**
   - Attempting to compress past turns into textual summaries discarded fine-grained coordinate and pixel evidence needed for later levels.
3. **Composite Animation Overlays:**
   - Overlaying animation frames into a single blurred image degraded vision performance; exposing raw intermediate arrays in Python worked far better.
4. **Pure Reactive CNNs / Small Models Without Search:**
   - Standalone CNN policies (like Stochastic Goose without MCTS or LLM guidance) fail to generalize across the 110 diverse game mechanics, scoring near 0.00% on unseen test games.

---

## 5. Strategic Recommendations for Our Repository

Instead of building a simulator or custom solver from scratch, our project should adopt an **evolutionary strategy built upon the validated state of the art**:

### Phase 2 Implementation Roadmap
1. **Adopt the Duck / TAAF Harness as the Core Agent Engine:**
   - Port the core Duck agent abstractions (`segmentation.py`, `noop_repeat_guard.py`, `retained_functions.py`, `frame_diff`) into our `src/` modular structure.
2. **Local Hybrid Development & Testing:**
   - Maintain dual-engine support:
     - **Local CPU / Apple Silicon (`mps`):** Lightweight local mock LLM / local small model / heuristic search for immediate offline debugging against the 25 public games (`src/evaluate.py`).
     - **Kaggle GPU Deployment:** SGLang / vLLM serving Qwen 3.8 Flash-Next with AutoRound W4A16 + MTP speculative decoding using Franzen's packaging architecture.
3. **High-ROI Innovations to Add On Top of Franzen's 27.89% Baseline:**
   - **MCTS / Best-First Planning in Python REPL:** Allow the model to simulate short rollouts and evaluate candidate action branches before committing moves to the environment.
   - **Coordinate Action Search Specialist (`ACTION6`):** Dedicated sub-module for mouse-driven click games (detecting clickable centroids from component boundaries).
   - **Dynamic Action Budget Guard:** Dynamically adjust the level action budget based on `baseline_actions` (which forum topic #687655 confirmed is visible in `environment_info.baseline_actions` during evaluation!).
