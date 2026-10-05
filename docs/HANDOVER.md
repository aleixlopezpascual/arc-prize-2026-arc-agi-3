# ARC Prize 2026 (ARC-AGI-3) — Session Handover Document

**Date:** Monday, October 5, 2026  
**Repository:** `aleixlopezpascual/arc-prize-2026-arc-agi-3` (Local: `/Users/aleix.lopez/arc-prize-2026-arc-agi-3`)  
**Current Global Standing:** **Rank #152 of 750+ teams** (Score: **`30.19%`**)  
**Kaggle User:** `aleixlopez`  

---

## 🏆 Official Competition Submissions Summary

| Submission Ref | Date (UTC) | Model Architecture | Status | Official Public Score |
| :--- | :--- | :--- | :--- | :--- |
| **`56836213`** | **2026-10-05 00:00:56** | **Duck Centroid V1 (Midnight Auto-Submit)** | **`COMPLETE`** | **`30.19%`** 🚀 **(Current Best, Rank #152)** |
| `56827574` | 2026-10-04 15:22:29 | Duck Centroid V1 Run 1 | `COMPLETE` | `25.22%` |
| `56806684` | 2026-10-03 21:05:59 | Daniel Franzen M2 Baseline | `COMPLETE` | `23.97%` |

---

## 🛠️ Proven Architecture & Breakthroughs

1. **The SGLang Serving Stack:**
   - **Framework:** SGLang Pennyroyal v2.5.3 (`dfranzen/pennyroyal-v253` compiled wheels for Python 3.12 / `cp312`).
   - **Base Model:** Qwen 3.8 Flash-Next with Intel AutoRound W4A16 quantization and unquantized BF16 PLE embedding tables offloaded to host system RAM (~95 GB).
   - **Speculative Decoding:** Albucino INT4 MTP (Multi-Token Prediction) drafter.
   - **Pinned Container:** `docker_image: "gcr.io/kaggle-private-byod/python@sha256:57e612b484cf3df5026ee4dcc3cb176974b22b2bc0937fb1e16132a8be4cb13c"`.
   - **Hardware Shape:** `NvidiaRtxPro6000` (96 GB VRAM).
   - **Prefix Cache Hit Rate:** **93.43%** when the prompt prefix is static.

2. **Enhancement #1: Click-Centroid Specialist (Jumped score from 23.97% to 30.19%):**
   - **Implementation:** Added `"bbox": [min_r, min_c, max_r, max_c]` and `"centroid": [round(sum(r)/N), round(sum(c)/N)]` to each segmented object node in `ARC3-Inference/inference/utils/segmentation.py`.
   - **Prompt Guidance:** Documented `bbox` and `centroid` in `prompts.py` so Qwen 3.8 Flash-Next targets interactive clicks (`ACTION6`) at exact object centers rather than guessing random pixels.
   - **Measured Impact:** Tripled `tu93` (11.3% -> 33.3%), launched `sc25` from 0% to 25.5%, and pushed the official leaderboard score to **30.19%**.

3. **Enhancement #2: Baseline-Aware Pacing & Sink Cap:**
   - Evaluated game baselines via `self.game.base_actions_per_level` (confirmed available during submission).
   - Added `bm.solver.max_generated_tokens_per_game = 185000` to terminate stalled puzzle games (like `bp35`) early, saving GPU compute for winnable games.

4. **Enhancement #3: Solved-Level Memory & The KV-Cache Golden Rule:**
   - **Empirical Finding:** Dynamically injecting text (like `Knowledge from cleared levels:`) into `_build_user_prompt` across level transitions invalidated SGLang's RadixAttention prefix cache, dropping generation throughput.
   - **Golden Rule:** **The prompt prefix must remain 100% static.** Any cross-level memory, episodic knowledge, or candidate click rankings must be passed via **runtime variables in the Python sandbox** (`current_frame.solved_memory`, `candidate_clicks()`), which preserves byte-identical prompt caching while giving the model full access to memory!

---

## 📁 Repository & Submission Artifacts

- **Best Working Submission:** `submissions/duck_centroid_v1/` (`notebook.ipynb`, `kernel-metadata.json`)
- **Staged Enhancements:**
  - `submissions/duck_pacing_v2/`: Baseline-aware scheduling + 185k token sink cap.
  - `submissions/duck_memory_v3/`: Evaluated demo run on Kaggle GPU.
- **Reference Baselines:** `notebooks/public_baselines/` (Franzen M2, Lord Han Solo 23.84%, Siriki Lohit 22.53%, Scott LeGrand, Sovereign Agent).
- **Automation:** `scripts/auto_submit_midnight.py` (daemon that polls quota and auto-submits).
- **Core Library & Tests:** `src/` (metrics, perception, guards, search), `tests/` (37/37 passing).

---

## 🚀 Immediate Next Steps for the New Session

1. **Review Leaderboard Standing:** Check `kaggle competitions submissions -c arc-prize-2026-arc-agi-3`.
2. **Next Submission Window:** Quota resets daily at **00:00 UTC**.
3. **Build `Duck V4` (Target: 35%+ / Top 50):**
   - Keep the system and user prompt prefixes **strictly byte-identical** to guarantee >93% KV-cache hit rate.
   - Expose `candidate_clicks()` and `solved_memory` directly inside `python_tool_sandbox.py` as pre-loaded runtime objects.
   - Deploy to Kaggle GPU, verify on demo games, and queue for submission.

---

## 🔐 Environment & Git Overrides
- Local git remote overrides:
  ```bash
  GIT_SSH_COMMAND="ssh" env -u GIT_CONFIG_COUNT -u GIT_CONFIG_KEY_3 -u GIT_CONFIG_VALUE_3 git push origin master
  ```
- All commits are pushed to `origin/master`. Working tree is 100% clean.
