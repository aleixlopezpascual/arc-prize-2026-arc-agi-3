# ARC Prize 2026 (ARC-AGI-3) — Bronze Medal Solution 🥉

[![Kaggle Rank](https://img.shields.io/badge/Kaggle%20Rank-%23393%20of%205%2C046%20(Top%207.8%25)-orange?style=flat-square)](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3)
[![Best Score](https://img.shields.io/badge/Best%20Public%20LB-32.09%25-green?style=flat-square)](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3)
[![Status](https://img.shields.io/badge/Status-Submissions%20Locked%20%7C%20Winners%20Dec%204-blue?style=flat-square)](https://arcprize.org)
[![Tests](https://img.shields.io/badge/Tests-Passing%20(100%25)-brightgreen?style=flat-square)](tests/)
[![License](https://img.shields.io/badge/License-Apache--2.0-lightgrey?style=flat-square)](LICENSE)

Official repository for team **Aleix López** in **[ARC Prize 2026 — ARC-AGI-3](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3)**.

* **Final Public Leaderboard Rank**: **`#393`** out of **5,046** teams (**Top 7.8%**, securely inside the **Bronze Medal bracket**).
* **Top Evaluated Submissions**:
  1. **Draw 1 (`Ref 57855048`)**: **`32.09%`** 🥉
  2. **Draw 2 (`Ref 57887146`)**: **`31.44%`** 🥉
* **Competition Status**: Submissions locked on **November 2, 2026 at 23:59 UTC**. Final private test evaluations and official winner announcements occur on **December 4, 2026**.

---

## 🧠 Core Architecture: S16 Final

Our competition-winning kernel, **S16 Final** (`submissions/s16_final/`), builds upon the strongest open architectures in ARC-AGI-3 while resolving critical efficiency, scheduling, and infrastructure bottlenecks.

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

### Key Pillars:

1. **RadixAttention Prefix Caching (High Token Throughput)**:
   * Early experiments (V13–V17) demonstrated that injecting dynamic observation memories, level summaries, and perception notes directly into the system prompt collapsed SGLang's KV-cache reuse, dropping generation speed from **430 tok/s to ~250 tok/s**.
   * S16 Final maintains a pristine, static prompt prefix, unlocking maximum speculative drafting throughput with Albucino MTP.

2. **Empirical Scheduler Simulation (Patience 40k $\rightarrow$ 200k)**:
   * Analysis of 213 real competition traces revealed that the default 40k token patience was prematurely abandoning high-value, solvable levels (e.g. `tr87` Level 6).
   * Offline Monte Carlo scheduler simulation across 5 regimes $\times$ 5 seed sets $\times$ 16 runs proved scaling `ARC3_PRIORITY_TOKEN_SCALE` to **200,000** consistently yielded **+0.4 to +1.9 points** of leaderboard gain.

3. **Infrastructure Hardening (Zero 0.00 Crashes)**:
   * **Resilient Multi-Path Resolvers**: Kaggle CLI kernel pushes mount dataset assets under `/kaggle/input/<slug>` instead of the Web UI's `/kaggle/input/datasets/<owner>/<slug>`. We injected dynamic multi-path fallbacks to eliminate path-not-found exceptions.
   * **55-Minute Startup Shield & Keep-Alive**: Background keepalive threads issue harmless warmup actions to prevent Kaggle's 15-minute inactivity container termination during congested RTX PRO 6000 boot cycles.
   * **Fast Commit Gate**: Cell 0 gate neutralizes execution during commit runs, finishing in seconds and saving 100% of GPU compute for competition reruns.

---

## 📁 Repository Structure

```
.
├── README.md               # Main repository documentation & guide
├── pyproject.toml          # Project configuration, dependencies, and tools
├── docs/                   # Detailed documentation and research ledgers
│   ├── HANDOVER.md         # Official competition submissions ledger & status
│   ├── ENDGAME_RUNBOOK.md  # Endgame schedule, commands, and decision matrix
│   ├── experiments.md      # Full experiment log of all 25 iterations
│   └── intel/              # Technical deep-dives, scheduler simulation & research
│       ├── oct30_scheduler_sim.md
│       ├── oct30_notebooks_intelligence.md
│       └── top_solutions_research.md
├── scripts/                # Utility and submission automation scripts
│   ├── build_s16_final.py  # Builds S16 Final, MEMFRAC 0.93, and Affectify variants
│   ├── submit_s16_run1.py  # Automated submission orchestrator for Draw 1
│   └── submit_s16_run2.py  # Automated submission orchestrator for Draw 2
├── src/                    # Core modular evaluation and agent framework
│   ├── agents/             # Agent implementations (OpenAI, Search, Baselines)
│   ├── experiments/        # Noise-aware A/B testing harness and statistics
│   ├── perception/         # Connected components, segmentation, and centroids
│   ├── evaluate.py         # Local offline evaluation runner
│   └── metrics.py          # ARC-AGI-3 efficiency and scoring formulas
├── submissions/            # Submission notebook packages and kernels
│   ├── s16_final/          # Primary submission kernel (32.09% Public LB)
│   ├── s16_final_mf93/     # MEMFRAC=0.93 fallback variant
│   └── affectify_backup/   # Affectify D' hedge variant
└── tests/                  # Automated pytest suite (unit, regression, notebook checks)
```

---

## 🚀 Quickstart & Reproduction

### 1. Environment Setup

Python 3.10+ is required (Python 3.12 recommended).

```bash
# Clone the repository
git clone https://github.com/aleixlopezpascual/arc-prize-2026-arc-agi-3.git
cd arc-prize-2026-arc-agi-3

# Install dependencies via pip or poetry
pip install -e .
```

### 2. Running Automated Tests

Run the full pytest suite to verify all agent contracts, perception algorithms, scheduler invariants, and notebook build structures:

```bash
pytest -v
```

### 3. Evaluating Agents Offline

Run local offline evaluations on public ARC-AGI-3 environments (`input/environment_files/`):

```bash
# Evaluate Random baseline
python -m src.evaluate --agent random --games ls20,ar25

# Evaluate Stochastic Goose CNN baseline
python -m src.evaluate --agent stochastic_goose --games ls20,ar25
```

### 4. Building Submission Notebooks

To build the submission notebook packages:

```bash
# Build S16 Final (Default: Stack S16 + 200k patience + resilient mounts)
python scripts/build_s16_final.py

# Build MEMFRAC 0.93 fallback variant
python scripts/build_s16_final.py --memfrac93

# Build Affectify D' backup variant
python scripts/build_s16_final.py --affectify
```

Output notebooks and `kernel-metadata.json` will be written to `submissions/s16_final/`.

---

## 📊 Submissions & Experiment Ledger

Our complete progression across the competition:

| Submission Ref | Date (UTC) | Model Architecture | Public Score | Key Finding / Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **`57855048`** | 2026-11-01 | **S16 Final Draw 1 (v2)** | **`32.09%`** 🥉 | **Team Record / Rank #393**. Clean 9h execution across 110 private test games. |
| **`57887146`** | 2026-11-02 | **S16 Final Draw 2 (v2)** | **`31.44%`** 🥉 | High replication. Confirms 31.5–32.1% performance band. |
| `56836213` | 2026-10-05 | Duck Centroid V1 Run 2 | **`30.19%`** | Previous best baseline; centroid targeting in segmentation. |
| `57232788` | 2026-10-15 | Duck V12 Run 2 | **`29.46%`** | Demo benchmark record (`58.42%`); no-op repeat guard. |
| `57138832` | 2026-10-13 | Duck V11 | **`27.77%`** | Refined action-budget guidance; Fable 30k. |
| `57055146` | 2026-10-11 | Duck V9 | **`27.26%`** | Unconstrained priority scheduling. |

*Full experiment and forensic history available in [`docs/HANDOVER.md`](docs/HANDOVER.md) and [`docs/experiments.md`](docs/experiments.md).*

---

## 🏆 Final Selections & Winner Announcement

Both top submissions were submitted and selected for final private leaderboard scoring:
1. **Ref `57855048`** (`32.09%`)
2. **Ref `57887146`** (`31.44%`)

The final private test evaluation takes the higher score of both selections. Final winners and official rankings will be announced by the ARC Prize organizers on **December 4, 2026**.

---

## 🙏 Acknowledgments & Credits

* **François Chollet & the ARC Prize Team**: For creating ARC-AGI and pushing the frontier of artificial general intelligence benchmarks.
* **Tufa Labs (Jeroen Cottaar)**: For the foundational Duck harness, agent sandbox design, and Milestone 1 open-source release.
* **Daniel Franzen (`dfranzen`)**: For the Milestone 2 solution architecture and model weights.
* **Андрей Рябов (`ondrewsha`)**: For the Stack S16 public baseline.
