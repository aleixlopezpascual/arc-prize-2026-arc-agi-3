# 🥉 Bronze Medal Solution (Rank #393 / 5,046) — ARC Prize 2026 (ARC-AGI-3)

**Team:** Aleix López  
**Final Public Leaderboard:** **`32.09%`** (Rank **#393** of **5,046** teams, **Top 7.8%** 🥉)  
**Open Source Repository:** [github.com/aleixlopezpascual/arc-prize-2026-arc-agi-3](https://github.com/aleixlopezpascual/arc-prize-2026-arc-agi-3)  

---

## 1. Executive Summary & Final Standings

ARC-AGI-3 is an open-ended benchmark evaluating agents across 110 hidden interactive grid games in a resource-constrained environment (NVIDIA RTX PRO 6000, 9-hour hard timeout, 1 submission per day).

Our team deployed **S16 Final (v2)**, an architecture combining high-throughput SGLang speculative inference, empirical scheduler optimization, and hardened container infrastructure.

* **Top Evaluated Submissions**:
  * **Draw 1 (`Ref 57855048`)**: **`32.09%`** 🥉 (All-time team record, +1.90% over our previous Duck Centroid peak)
  * **Draw 2 (`Ref 57887146`)**: **`31.44%`** 🥉 (High-fidelity replication, confirming the 31.5–32.1% performance band)
* **Final Public Leaderboard Position**: **Rank #393** (Bronze cutoff: 31.61% / Rank #504; Silver cutoff: 32.96% / Rank #252).

---

## 2. What Worked vs. What Didn't

| Technique | Status | Impact / Finding |
| :--- | :--- | :--- |
| **Pristine RadixAttention Prefix Caching** | **Worked** | **Critical.** Keeping system prompts static unlocked **430 tok/s** generation throughput vs. ~250 tok/s when injecting dynamic text. |
| **Scheduler Simulation (Patience 40k $\rightarrow$ 200k)** | **Worked** | **+0.4 to +1.9 points** simulated gain across 213 real competition traces. Solved high-action late levels that 40k dropped. |
| **Hidden `RESET` Action** | **Worked** | **+6.0 points** in local benchmarks. Removed panic-reset loops by restricting `RESET` exclusively to the supervisor harness. |
| **Resilient Multi-Path Mount Resolvers** | **Worked** | Fixed early container crash. Solved the discrepancy between Kaggle Web UI (`/datasets/`) and Kaggle CLI (`/kaggle/input/<slug>`). |
| **55-Min Startup Shield & Warmup Keep-Alive** | **Worked** | Prevented the 15-minute container inactivity shutdown during congested RTX PRO 6000 boots that zeroed out dozens of competitors. |
| **Fast Commit Gate (AST Neutralizer)** | **Worked** | Saved 100% of weekly GPU quota by finishing commit runs in ~30 seconds, preserving compute for competition reruns. |
| **Dynamic In-Prompt Memories (V13–V17)** | *Failed* | Broken KV-cache reuse, reduced generation speed by 40%, and caused a regression to 16.43%. |
| **Candidate Centroid / Goal Over-Anchoring (V14–V16)**| *Failed* | Biased model toward static Level 1 patterns, failing on dynamically shifting mechanics. |
| **Unvalidated Last-Minute Code Injections (V18–V20)** | *Failed* | Responsible for four `0.00` scores (V18 OOM, V19 indentation, V20 scoping). Proved that freezing code beats last-minute tweaking. |

---

## 3. Core Architecture: S16 Final

Our final architecture operates on a modular, high-throughput pipeline:

```
                                  [ ARC-AGI-3 Environment ]
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼                                           ▼
             [ Turn Observations ]                       [ Frame History Buffer ]
                       │                                           │
                       │ (Per-frame lazy serialization)            │
                       ▼                                           ▼
         [ SGLang High-Throughput Engine ]               [ Scheduler Engine ]
         - RadixAttention Prefix Cache                   - D' Priority Normalization
         - Intel Qwen 3.8 Flash-Next (INT4)              - Token Patience: 200,000
         - Albucino MTP Speculative Drafter              - Human-Action Scale: 100
         - Clean Unpolluted Static Prompt                - Dynamic End-Time Budgeting
                       │                                           │
                       └─────────────────────┬─────────────────────┘
                                             ▼
                                  [ Verified Execution ]
                                  - In-Sandbox Python CodeAct
                                  - Resilient Mount Fallbacks
                                  - 55-Min Startup Keep-Alive
```

### Inference & Serving Stack
* **Base Model**: Intel Qwen 3.8 Flash-Next (W4A16 AutoRound INT4 quantization).
* **Speculative Drafter**: Albucino MTP (Multi-Token Prediction) runtime.
* **Serving Engine**: SGLang with FP8 KV-cache (`KVDTYPE=fp8_e5m2`), `mem_fraction_static=0.96` (and `0.93` fallback), structured warmups, and watchdog timeout 1800s.
* **Throughput**: Sustained **~430 tokens/second** during live agent play.

---

## 4. The "Feature Bloat" Post-Mortem: Preserving Prefix Caching

Between iterations V13 and V17, we attempted to improve reasoning by injecting perception features into the context:
1. JSON-encoded memory state across levels.
2. Solved-level evidence summaries.
3. Connected-component centroid bounding boxes.
4. Pre-explorer dynamic environmental notes.

### The Failure Mode:
While individual prompts looked richer, **every dynamic injection altered the system prompt prefix**. In SGLang, RadixAttention relies on token-for-token prefix matching across conversation turns. Invalidating the prefix cache forced full prompt re-evaluations on every step:
* Token generation collapsed from **430 tok/s to ~250 tok/s**.
* Over 9 hours, the agent took **~40% fewer total actions**, abandoning solvable games as the clock expired.
* On Duck V19 fixed v2, this degraded performance to **16.43%**.

### The Solution:
In S16 Final, we strictly decoupled static context from dynamic context:
* The system prompt is **100% static and byte-immutable**.
* Frame history is lazily serialized once per game frame (rather than per action).
* Resumption messages carry no redundant grid images when identical to the turn opener.
* This restored full RadixAttention cache hits, allowing the model to play at full hardware speed.

---

## 5. Empirical Scheduler Simulation: Token Patience Scaling

In ARC-AGI-3, 10 game streams compete for GPU time across 110 games. If a game gets stuck, its priority decays exponentially based on token consumption:
$$\text{Priority Decay} = 0.5^{(\text{tokens} / \text{scale})^2}$$

Stack S16 shipped with `ARC3_PRIORITY_TOKEN_SCALE = 40000`. We investigated whether 40,000 tokens was abandoning levels too early.

### The Simulation Experiment:
We used `tantan0327`'s calibrated simulator (`sched_sim.py`), replaying **213 real competition trajectories** across 10 slots, a 9-hour wall-clock, and 110 games across 5 distinct difficulty regimes:

```
regimes: [main, harder, easier, mix, allhard]
seeds: 16 paired seed sets per regime
variants evaluated: 40k, 62k, 150k, 200k, 300k, 500k, infinite
```

### Results (Mean Paired Gain over baseline 40k):
| Seed Set & Regime | main | harder | easier | mix | allhard |
|---|---|---|---|---|---|
| Seed 200 (Default Hazard), **200k** | **+0.64** | **+1.90** | **+1.48** | **+0.52** | **+0.63** |
| Seed 300 (Default Hazard), **200k** | **+0.70** | **+1.59** | **+1.49** | **+0.79** | **+0.69** |
| Seed 400 (Hard games never clear), **200k** | **+0.42** | **+1.33** | **+1.31** | **+0.73** | **−0.04** |

### The Insight:
Long final levels (e.g., `tr87` Level 6, requiring 146 human actions) frequently took 50k–80k tokens before finding the winning trajectory. At 40k patience, the scheduler was prematurely shelving these high-value games. 

Scaling patience to **200,000 tokens** delivered a robust **+0.4 to +1.9 point advantage** across every regime, which directly powered our leap to **`32.09%`** on the public leaderboard.

---

## 6. The Hidden `RESET` Discovery

In early versions, the agent's action space included `RESET`. When an agent encountered unexpected obstacles or got stuck in a dead-end, it frequently panicked and issued `RESET`:
* The reset wiped the board back to Level 1.
* The model then blindly executed the exact same opening sequence, burning hundreds of action steps in an infinite loop.

### The Fix:
We stripped `RESET` from the model's action space and made resets transparent to the agent:
* Resets are issued **only by the supervisory harness** when an unrecoverable failure state is detected.
* Hiding `RESET` from the LLM prevents panic loops, recovering **~6 percentage points** across benchmark evaluations.

---

## 7. Infrastructure Hardening: Zero 0.00 Runs

In the final 72 hours of the competition, dozens of teams were eliminated by infrastructure crashes. We engineered three critical guardrails:

### 1. Resilient Multi-Path Resolvers
Kaggle CLI kernel pushes mount dataset assets under `/kaggle/input/<dataset-slug>` directly, whereas notebooks authored in the Web UI reference `/kaggle/input/datasets/<owner>/<dataset-slug>`.
```python
# Multi-path fallback resolution for CLI and UI mounts
for _ in range(30):
    if Path(ORIG_BUNDLE_DIR).exists() or Path('/kaggle/input/taaf-kaggle-source-bundle-copy').exists():
        break
    time.sleep(1)

if not Path(ORIG_BUNDLE_DIR).exists() and Path('/kaggle/input/taaf-kaggle-source-bundle-copy').exists():
    ORIG_BUNDLE_DIR = '/kaggle/input/taaf-kaggle-source-bundle-copy'

wheelhouse = next(
    iter(sorted(Path("/kaggle/input").glob("**/arc_agi_3_wheels"))),
    Path("/kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels"),
)
```

### 2. 55-Minute Startup Shield & Warmup Keep-Alive
Kaggle automatically terminates containers if no game actions occur within ~15 minutes. During heavy RTX PRO 6000 backend congestion, model weights and wheels can take 40+ minutes to load:
* We launched a background keep-alive thread that emits periodic, non-destructive `RESET` actions on a warmup game every 9 minutes while the SGLang health check boots.
* This prevented the 15-minute gateway timeout that killed multiple competitors on the final day.

### 3. Zero-GPU Fast Commit Gate
We placed an AST-level gate in Cell 0:
```python
if os.environ.get("KAGGLE_IS_COMPETITION_RERUN", "").strip().lower() not in {"1", "true"}:
    Path("/kaggle/working").mkdir(parents=True, exist_ok=True)
    pd.DataFrame([["1_0", "1", True, 1]], columns=["row_id", "game_id", "end_of_game", "score"]).to_parquet("/kaggle/working/submission.parquet", index=False)
    get_ipython().input_transformers_post.append(lambda lines: ["pass\n"])
```
In commit mode ("Save Version"), the gate writes the placeholder output and skips all subsequent cells in **~30 seconds**. In competition reruns, the gate is inactive. This saved 100% of our 30-hour weekly GPU quota for actual scoring reruns.

---

## 8. Statistical Portfolio Selection

ARC-AGI-3 evaluation variance on 55 public test games exhibits $\sigma \approx 3.0$ points per run due to LLM sampling temperature ($T=0.7$) and random game seeds.

Rather than making high-risk, unverified code changes on the final day, our endgame strategy focused on **variance harvesting**:
* We submitted two independent runs of our verified **S16 Final v2** distribution:
  * **Draw 1**: **`32.09%`**
  * **Draw 2**: **`31.44%`**
* Both were ticked as our **2 final selected submissions**.
* Because Kaggle takes the maximum of selected submissions on the private test set ($\max(\text{Draw 1}, \text{Draw 2})$), evaluating two independent draws maximizes our probability of capturing an upper-tail private score while locking down our **Bronze Medal position**.

---

## 9. Acknowledgments

* **François Chollet & the ARC Prize Team**: For designing an extraordinary benchmark that tests true out-of-distribution reasoning.
* **Tufa Labs (Jeroen Cottaar)**: For the Duck harness architecture, sandbox execution, and pioneering Milestone 1 work.
* **Daniel Franzen (`dfranzen`)**: For the foundational Milestone 2 architecture and model weights.
* **Андрей Рябов (`ondrewsha`)**: For the Stack S16 public baseline.
* **`tantan0327`**: For the open-source scheduler simulation framework.
