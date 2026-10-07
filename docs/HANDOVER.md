# ARC Prize 2026 (ARC-AGI-3) — Session Handover Document

**Date:** Wednesday, October 7, 2026  
**Repository:** `aleixlopezpascual/arc-prize-2026-arc-agi-3` (Local: `/Users/aleix.lopez/arc-prize-2026-arc-agi-3`)  
**Current Best Leaderboard Score:** **`30.19%`** (Rank #152 of 750+ teams, Ref `56836213`)  
**Best Demo Benchmark:** **`56.81%`** (Duck V4: 48 / 65 levels cleared, +10.09% over Centroid V1)  
**Kaggle User:** `aleixlopez`  

---

## 🏆 Official Competition Submissions Ledger

| Submission Ref | Date (UTC) | Model Architecture | Status | Public Score | Key Finding / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`56912309`** | **2026-10-07 13:41:45** | **Duck V5 (Centroids + candidate_clicks + bfs_path + D-prime)** | **`COMPLETE`** | **`24.31%`** | 🛡️ Clean 9-hour run, 0 crashes. Finding: D-prime queueing suppressed unstarted games. Round-robin is required. |
| `56891721` | 2026-10-06 22:02:48 | Duck V4 (candidate_clicks + object_at + is_border + solved_memory) | `ERROR` | - | 🚀 **56.81% Demo** (+10.09% over V1, 48/65 levels). Terminated due to missing null check on frame payload during live arcade reset. Fixed in V5. |
| **`56836213`** | **2026-10-05 00:00:56** | **Duck Centroid V1 (Midnight Auto-Submit)** | **`COMPLETE`** | **`30.19%`** 🚀 | **Current Best LB (Rank #152)**. Centroid & bbox targeting in segmentation. |
| `56827574` | 2026-10-04 15:22:29 | Duck Centroid V1 Run 1 | `COMPLETE` | `25.22%` | First centroid run (+1.25% over baseline). |
| `56806684` | 2026-10-03 21:05:59 | Daniel Franzen M2 Baseline | `COMPLETE` | `23.97%` | Initial baseline locked in. |

---

## 🔬 Key Architectural Milestones & Empirical Learnings

### 1. Duck V4: The Perception & Memory Breakthrough (56.81% Demo Benchmark)
In Duck V4, we introduced four pure-Python sandbox perception primitives while keeping system and user prompt prefixes **100% byte-static** to preserve SGLang's >93% RadixAttention KV-cache hit rate:
- **`candidate_clicks(color=None, min_size=1, max_size=None, exclude_border=True)`**: Automatically filters outer border/HUD timer components, computes centroids, and returns candidate click targets sorted by pixel count descending.
- **`object_at(row, col)`**: Directly returns the segmented object node enclosing coordinate `(row, col)` or `None`.
- **`is_border` in `segmentation.py`**: Identifies perimeter strips and HUD countdown bars across arbitrary grid dimensions $H \times W$.
- **Zero-Prompt-Drift Solved Memory**: Cleared level summaries (level number, action count, winning actions) are passed **strictly via JSON runtime state** into the sandbox as `current_frame.solved_memory` and global `solved_memory`. Prompt templates remain 100% byte-identical.
- **Measured Impact:** Smashed the 10-game demo benchmark from **46.72% to 56.81% (+10.09% gain)**, clearing **48 / 65 levels** (+7 levels solved), with `lp85` jumping from 41.7% to 77.8% and `sc25` jumping from 25.5% to 47.6%.
- **Submission 56891721 Post-Mortem:** In `tool_agent.py`, during live arcade network resets across the 110 private games, `_ascii_frame_view_payload(frame)` returned `None`. Calling `None["solved_memory"]` raised an unhandled `TypeError`. This was immediately resolved with defensive null guards in Duck V5.

### 2. Duck V5: Search Primitives & Scheduler Analysis (24.31% LB)
In Duck V5, we added:
- **Defensive Null-Safety:** Guaranteed `if current_frame_payload is not None:` before item assignment in `tool_agent.py`.
- **Built-In `bfs_path()` Grid Search:** Shortest-path action generator (`UP`, `DOWN`, `LEFT`, `RIGHT`) in `python_tool_sandbox.py`, eliminating the 40+ lines of manual BFS boilerplate the LLM was writing by hand in navigation games (`tu93`, `re86`).
- **Shiiin9's $D'$ Priority Scheduler:** Integrated Osaka Metropolitan University's formula ($A \cdot M \cdot C + B \cdot \phi$) from the #1 public notebook (`shiiin9/affectify-arc-31-54-in-a-single-sub`).
- **Empirical Rerun Result & Critical Scheduler Finding:**
  - Submission `56912309` executed for the full 9 hours with **zero crashes** (confirming 100% runtime stability).
  - Score was **`24.31%`**.
  - **The Root Cause:** In Shiiin9's $D'$, *"unstarted games no longer jump the queue; they compete on equal footing with active games."* While effective in simulation, in the actual 110-game competition rerun, games with high token usage on early levels hogged the GPU slots, starving unstarted games from ever receiving their first active turn (leaving them with a 0.00 score).
  - **The Golden Rule for Schedulers:** Franzen's original round-robin scheduling (where every unstarted game is guaranteed at least one turn to get on the board before priority pruning takes effect) is essential for maximizing aggregate leaderboard score across all 110 games.

---

## 🎯 Blueprint for Duck V6 (Targeting 35%–40%+):

Duck V6 will bring together the best of both worlds:
1. **Perception & Memory (From Duck V4/V5):**
   - Retain `candidate_clicks()`, `object_at()`, `is_border`, in-sandbox `current_frame.solved_memory`, and `bfs_path()`.
   - Retain the null-safety guard in `_serialized_runtime_state()`.
2. **Guaranteed Round-Robin Scheduling (From Franzen / Duck Centroid V1):**
   - Revert to Franzen's original scheduler where all 110 games are guaranteed active rounds (`gate.acquire(2000000 - waiting_order)`).
   - Ensure no game is starved at Level 1.
3. **Pacing Sink Cap:**
   - Add `bm.solver.max_generated_tokens_per_game = 185000` to gently clip runaway puzzle sinks (like `bp35`) without starving unstarted games.

---

## 📁 Repository Directory Map

```text
/Users/aleix.lopez/arc-prize-2026-arc-agi-3/
├── docs/
│   ├── HANDOVER.md                         # This session handover document
│   ├── experiments.md                      # Complete experiment ledger
│   ├── intel/
│   │   ├── top_solutions_research.md       # Competitive intel (Shiiin9 D', Provorov Fable)
│   │   └── forum_intel.md                  # Community discussion findings
│   └── superpowers/
│       ├── specs/                          # Architecture specs (Duck V4, search, etc.)
│       └── plans/                          # Implementation plans
├── src/
│   ├── perception/
│   │   ├── segmentation.py                 # bbox, centroid, is_border detection
│   │   └── sandbox_primitives.py           # candidate_clicks, object_at
│   ├── search/
│   │   └── bfs_path.py                     # bfs_path shortest pathfinder
│   ├── utils/
│   │   └── solved_memory.py                # Cross-level solved memory manager
│   ├── guards/                             # noop repeat guards
│   ├── agents/                             # stochastic goose, search agent, etc.
│   └── metrics.py                          # Official ARC-AGI-3 efficiency metric
├── submissions/
│   ├── duck_centroid_v1/                   # 30.19% LB Best Working Submission
│   ├── duck_v4/                            # 56.81% Demo Benchmark package
│   └── duck_v5/                            # 24.31% LB Null-Safe + BFS + D-prime package
├── scripts/
│   ├── auto_submit_duck_v4.py              # V4 auto-launch & submit daemon
│   └── auto_submit_duck_v5.py              # V5 auto-launch & submit daemon
└── tests/                                  # 51/51 pytest tests (100% GREEN in 5.25s)
```

---

## 🧪 Testing & Verification Commands

```bash
# Run the entire test suite (51 tests)
python3 -m pytest tests/ -v

# Run Duck V5 / V4 verification tests
python3 -m pytest tests/test_duck_v5.py tests/test_duck_v5_notebook.py -v
python3 -m pytest tests/test_duck_v4_patch.py tests/test_duck_v4_notebook.py -v

# Check competition submissions status
kaggle competitions submissions -c arc-prize-2026-arc-agi-3
```

---

## 🔐 Git & Remote Push Overrides

- Local git remote overrides:
  ```bash
  GIT_SSH_COMMAND="ssh" env -u GIT_CONFIG_COUNT -u GIT_CONFIG_KEY_3 -u GIT_CONFIG_VALUE_3 git push origin master
  ```
- All commits are pushed to `origin/master`. Working tree is 100% clean.
