# Top Public Notebooks: arc-prize-2026-arc-agi-3

*Last Updated: 2026-10-29*

## Top Voted & Highest Scoring Public Notebooks

| Title | Author | Votes | Ref / Kernel Slug | Score / Notes |
| :--- | :--- | :--- | :--- | :--- |
| **大阪公立大学 Affectify ARC支部🐙｜31.54 in a Single Sub** | shiiin9 | 75 | `shiiin9/affectify-arc-31-54-in-a-single-sub` | 🏆 **31.54% LB**. Replaces Franzen's scheduler priority with the $D'$ formula ($A \cdot M \cdot C + B \cdot \phi$) and removes `fresh_floor`. |
| **LB score 31.21** | Laimer Botrolenk | 3 | `laimerbotrolenk/lb-score-31-21` | 🚀 **31.21% LB**. "Adaptive Duck": Bounded memory, action batch early stopping, and verified execution. |
| **ARC-AGI-3 Milestone 2 Solution** | Daniel Franzen | 1,164 | `dfranzen/arc-agi-3-milestone-2-solution` | **27.89% LB (M2 Winner)**. Qwen3.8-Flash-Next W4A16, Albucino MTP draft, SGLang Pennyroyal, 93% KV cache hit rate, priority scheduler. Bedrock of all current top solutions. |
| **ARC-AGI-3: 27.80 LB \| 100-Trajectory Audit** | skarin | 55 | `skarin/arc-agi-3-27-80-lb-100-trajectory-audit` | 🔬 **27.80% LB**. Full empirical audit of 100 Franzen runs: 33/100 games completely cleared (100% score) when scheduler gives them sufficient slots. |
| **ARC3 franzen dprime** | red-down (tantan0327) | 80 | `tantan0327/arc3-franzen-dprime` | Franzen M2 with D' priority plugin (`priority_form.py`). |
| **ARC3 D-prime public base** | 奶龙 (dennis6886) | 52 | `dennis6886/arc3-d-prime-public-base` | Clean D' scheduler integration. |
| **Affectify ARC Dfranzen Form D1** | Weitao Guo | 56 | `weitaoguo/affectify-arc-dfranzen-form-d1` | Franzen M2 with D' priority variation. |
| **ARC3 Sample Submission - Random Agent** | inversion | 763 | `inversion/arc3-sample-submission-random-agent` | Official starter benchmark. |
| **ARC3 Sample Submission - Stochastic Goose** | inversion | 750 | `inversion/arc3-sample-submission-stochastic-goose` | Official starter benchmark. |
| **Tufa Labs duck harness [June 30 milestone winner]** | Jeroen Cottaar | 393 | `jeroencottaar/tufa-labs-duck-harness-june-30-milestone-winner` | **M1 Winner**. The original Python REPL tool harness. |
| **LB-9 arc3 duck v12 with Qwen 3.8 27B** | FOYSAL | 297 | `foysalemonshanto/lb-9-arc3-duck-v12-with-qwen-3-8-27b` | Early Qwen 27B harness port. |
| **Duck Qwen3.8 Anim Base** | wuliao_0 | 293 | `wuliao0/duck-qwen3-8-anim-base` | Exposed animation frames and timelines. |
| **【暗黑AGI】duck-harness-fast-eval** | 暗黑AGI | 265 | `boristown/agi-duck-harness-fast-eval` | Accelerated evaluation harness. |
| **taaf-duck-harness-kaggle** | Jeroen Cottaar | 267 | `jeroencottaar/taaf-duck-harness-kaggle` | TAAF foundation. |
| **Ash's ARC-AGI-3 Agent** | ashvin singh | 242 | `ashvinsingh/ash-s-arc-agi-3-agent` | Early custom agent exploration. |
| **Duck Qwen3.8 (Tuned)** | Akagha Chimgozirim | 220 | `chiakazirim/duck-qwen3-8-tuned` | Fine-tuned prompt variations. |
| **Duck Qwen3.8 Flash Next NVFP4 MTP** | chiefkeith | 212 | `keithtyser/duck-qwen3-8-flash-next-nvfp4-mtp` | NVFP4 quantization with MTP head. |
| **taaf-flashnext-sheetu12b-0922** | Scott Le Grand | 197 | `scottlegrand/taaf-flashnext-sheetu12b-0922` | Sheetu 12B experimental run. |
| **FORGE ARC-AGI-3 Agent** | CHRONOS | 167 | `projectforty2/forge-arc-agi-3-agent` | Search-focused heuristic solver. |
| **[0.46] ARC-AGI-3: Persistent Memory BFS ARC Solver** | parthenos | 153 | `nihilisticneuralnet/0-46-arc-agi-3-persistent-memory-bfs-arc-solver` | Persistent memory across moves. |
| **taaf-duck-harness-kaggle-share(Resubmission)** | RS | 152 | `rokaiyasomapti/taaf-duck-harness-kaggle-share-resubmission` | Resubmission baseline. |
| **ARC3 M2 Solution** | Jingshui Fu | 137 | `jingshuifu/arc3-m2-solution` | Franzen M2 variant. |
| **The AGI Boys \| I AM BETTER** | Roman Tamrazov | 303 | `romantamrazov/the-agi-boys-i-am-better` | Single-pass evaluation configuration. |
| **Try merging it—you might get lucky and win gold⭐⭐⭐** | Heliosli | 125 | `heliosli/try-merging-it-you-might-get-lucky-and-win-gold` | Pluggable D' priority integration on Franzen M2 base. |
| **TAAF · Anim — ARC-AGI-3 Solver** | Jakob Brüggen | 120 | `jakobbrggen/taaf-anim-arc-agi-3-solver` | Animation frame handler integration. |
| **ARC-AGI-3 Champion Solution** | Yukai Liu | 44 | `yukailiu/arc-agi-3-champion-solution` | Cache-safe solved-level memory and paper track writeup baseline. |
| **ARC3 SLM plus 55min startup fix** | Weitao Guo | 0 | `weitaoguo/arc3-slm-plus-55min-startup-fix` | **CRITICAL INFRA FIX (Oct 25)**. 55-minute server startup timeout, warmup reset action to prevent Kaggle inactivity cancel, 900s HTTP retry grace. |

---

## 🔬 Deep-Dive Analysis of the Leading Public Techniques

### 1. The $D'$ Priority Scheduler (`Affectify 31.54 LB`)

In Daniel Franzen's original scheduler, 10 game slots run concurrently. When context is trimmed, games yield their slot, but:
1. **Unstarted games always jumped the queue** (`priority = 2,000,000 - queue_index`), preempting games on level 6 or 7 that were close to a 100% clear.
2. Stagnant games (spending hundreds of actions on an impossible level) continued eating GPU time equally.

**The $D'$ Formula:**
$$\text{Priority} = A \cdot M \cdot C + B \cdot \phi$$

* **$A$ (Level Depth & Action Efficiency):**
  $$(1 + 0.5(\ell - 1)) \cdot \text{norm}(N) \cdot \left(\frac{300}{300 + a}\right)^{2.5}$$
  Games on higher levels ($\ell$) receive a dramatic boost. Games that take too many actions ($a$) decay aggressively.
* **$M$ (Pace / Token Efficiency):**
  $$\text{clip}\left(\left(\frac{30,000}{p}\right)^{0.4}, 0.25, 4.0\right)$$
  Where $p$ is the mean tokens generated per cleared level so far. Games clearing levels with fewer tokens get up to $4\times$ multiplier!
* **$C$ (Patience / Stagnation Backoff):**
  $$0.1 \cdot \max(0.1, 1 - a / 115) + 0.9 \cdot \max(0.1, 1 - t / T)$$
  Where $T = 225,000 \cdot \text{clip}(p / 30000, 0.5, 2.0)^{0.5}$. Stagnant levels lose patience and yield their slot to active winners.
* **$B$ (Room to Grow):** Bonus of 16, 14, 10, or 0 when $\ge 3$, 2, 1, or 0 levels remain.
* **$\phi$ (Tail Fade):** Ramps from $1 \to 0$ over the final 40% of the 9-hour competition window.
* **Queue Egalitarianism:** Removes `fresh_floor`. Unstarted games compete based on potential rather than jumping ahead.

---

### 2. 100-Trajectory Audit Findings (`skarin 27.80 LB`)

Audit of 100 game runs by the 27B Qwen model revealed:
* **33% of private games are 100% solvable** by Qwen 27B if given sufficient slot time (`tn36`, `tu93`, `lp85`, `r11l`, `ar25`, `sb26`, `cd82`, `ft09`, `tr87`).
* Games fail primarily because the scheduler pulls the plug while the model is actively making progress on later levels.
* Optimizing the scheduler gives a **+3.6% to +5.0% score increase** without modifying the model or prompt.

---

## 📊 Feature Comparison: Duck V20 vs Top Public Notebooks

| Feature | Franzen M2 Original | Affectify 31.54 | Adaptive Duck 31.21 | **Our Duck V20** |
| :--- | :---: | :---: | :---: | :---: |
| **Base Model** | Qwen3.8-Flash-Next W4A16 + MTP | Qwen3.8-Flash-Next W4A16 + MTP | Unverified (notebook not in repo) | Qwen3.8-Flash-Next W4A16 + MTP |
| **SGLang VRAM Headroom** | 5 MB (`MEMFRAC=0.96`) | 5 MB (`MEMFRAC=0.96`) | 5 MB (`MEMFRAC=0.96`) | **6,670 MB (`MEMFRAC=0.93`)** |
| **CUDA OOM Shield** | ❌ Spikes on TileLang | ❌ Spikes on TileLang | ❌ Spikes on TileLang | **✅ `expandable_segments:True`** |
| **55-Min Startup Shield** | ❌ Aborts at 12m | ❌ Aborts at 12m | ✅ 55m Shield | **✅ 55m Shield + Keepalive** |
| **Scheduler Priority** | Default Round-Robin | **✅ $D'$ Priority Formula** | Default Round-Robin | Default Round-Robin |
| **Win-Path Solution Cache** | ❌ None | ❌ None | ❌ None | **✅ Pre-cached 4-Level Wins** |
| **Tile Step-Size Detection**| ❌ 1px default | ❌ 1px default | ❌ 1px default | **✅ Dynamic 5px Sensing** |
| **Public LB Score** | 27.89% | **31.54%** | 31.21% | **30.22% (Practice)** |

---

## 🎯 High-Value Takeaways for Our Next Kernel (Duck V21)

1. **Integrate the $D'$ Scheduler:**
   * Adding the $D'$ priority formula from `Affectify 31.54` to Duck V20 is a zero-risk plug-and-play hook (`install_d(tool_agent, solver)`).
   * It directs GPU compute to games that are actively clearing levels instead of stalling on dead ends.
2. **Combine with Duck V20's Infrastructure Armor:**
   * Affectify 31.54 still uses `MEMFRAC=0.96` and lacks the 55-minute startup shield, making it vulnerable to Kaggle OOMs and cache mounting timeouts.
   * Combining $D'$ scheduling with our **MEMFRAC=0.93 Lean Armor** and **Win-Path Solution Cache** gives the best of all worlds:
     $$\text{Duck V21} = \text{SGLang Lean Armor} + D' \text{ Scheduler} + \text{Win-Path Cache} + \text{Dynamic 5px Perception}$$
     **Targeting: 34%–36%+ Leaderboard Score.**

