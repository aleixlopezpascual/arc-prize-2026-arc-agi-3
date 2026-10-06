# Experiment Ledger: ARC Prize 2026 - ARC-AGI-3

Tracking all agent iterations, local validation scores, efficiency benchmarks, and leaderboard submissions.

---

## Evaluation Benchmark Setup
- **Metric:** Weighted efficiency-squared completion score ($0.0\%$ – $100.0\%$).
- **Local Validation Set:** 25 public ARC-AGI-3 environments (`input/environment_files/`).
- **Leaderboard Scope:** 110 unseen private games (55 public test, 55 private test).

---

## Experiments Table

| Exp ID | Date | Agent Strategy / Description | Local Macro Score (%) | Levels Cleared | Total Actions | Public LB | Notes & Next Steps |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `exp-00-scaffold` | 2026-10-01 | Baseline metric engine & test suite verification | - | - | - | - | 100% test pass on metric calculation. Scaffold complete. |
| `eval-random` | 2026-10-01 | RandomAgent baseline on smoke games (ls20, ar25, dc22) | 0.00% | 0 | 349 | - | Random exploration lower bound verified. |
| `eval-stochastic_goose` | 2026-10-01 | StochasticGoose (Tufa Labs CNN) on smoke games (ls20, ar25, dc22) | 0.00% | 0 | 407 | - | Offline forward pass & state encoding verified. |
| `eval-stochastic_goose-2026-10-02` | 2026-10-02 | stochastic_goose on all 25 public games | 0.00% | 0 | 5142 | - | Benchmark baseline for untrained CNN agent. |
| `sub-56806684` | 2026-10-03 | Daniel Franzen M2 Baseline (TAAF + Qwen 3.8 Flash-Next) | 40.25% (10 demo) | 39 / 65 | 1462 | 23.97% | Initial baseline locked in. |
| `sub-56827574` | 2026-10-04 | Duck Centroid V1 Run 1 | 46.72% (10 demo) | 41 / 65 | 1434 | 25.22% | Injected bbox and centroids for ACTION6 clicks. First leaderboard improvement (+1.25%). |
| `sub-56836213` | 2026-10-05 | Duck Centroid V1 Run 2 (Midnight Auto-Submit) | 46.72% (10 demo) | 41 / 65 | 1434 | **30.19%** | 🚀 BROKE 30%! Rank #152 on the Global Leaderboard. +6.22% jump over baseline! |
| `sub-duck-pacing-v2` | 2026-10-03 | Duck Pacing V2: Centroids + Real Baseline Priority + 185k Token Sink Cap | - | - | - | Staged | Caches human_baseline in PrioritySnapshot and caps runaway games at 185k tokens. |
| `sub-duck-memory-v3` | 2026-10-05 | Duck Memory V3 (Centroids + Pacing + Solved Memory) | 26.11% (10 demo) | 30 / 65 | 860 | - | Kernel complete. Finding: dynamic prompt prefix text hurt SGLang prefix-cache reuse rate. Preserving static prefix is critical. |
| `sub-56891721` | 2026-10-06 | Duck V4 (candidate_clicks, object_at, is_border, in-sandbox solved_memory) | **56.81%** (10 demo) | **48 / 65** | 1580 | PENDING | 🚀 +10.09% Demo Benchmark jump over V1 (46.72% -> 56.81%). 48/65 levels cleared (+7 levels). Zero crashes, 562.9 tok/s, submitted & executing on 110 private competition games! |

---

## Per-Game Tracking on 25 Public Games

| Game ID | Baseline Actions (Sum) | Best Agent Score | Best Levels Cleared | Notes / Mechanics |
| :--- | :--- | :--- | :--- | :--- |
| `ar25` | - | - | - | Public game |
| `bp35` | - | - | - | Public game |
| `cd82` | - | - | - | Public game |
| `cn04` | - | - | - | Public game |
| `dc22` | - | - | - | Public game |
| `ft09` | - | - | - | Public game |
| `g50t` | - | - | - | Public game |
| `ka59` | - | - | - | Public game |
| `lf52` | - | - | - | Public game |
| `lp85` | - | - | - | Public game |
| `ls20` | - | - | - | Public game |
| `m0r0` | - | - | - | Public game |
| `r11l` | - | - | - | Public game |
| `re86` | - | - | - | Public game |
| `s5i5` | - | - | - | Public game |
| `sb26` | - | - | - | Public game |
| `sc25` | - | - | - | Public game |
| `sk48` | - | - | - | Public game |
| `sp80` | - | - | - | Public game |
| `su15` | - | - | - | Public game |
| `tn36` | - | - | - | Public game |
| `tr87` | - | - | - | Public game |
| `tu93` | - | - | - | Public game |
| `vc33` | - | - | - | Public game |
| `wa30` | - | - | - | Public game |
| `eval-stochastic_goose-2026-10-02` | 2026-10-02 | stochastic_goose on ar25,bp35,cd82,cn04,dc22,ft09,g50t,ka59,lf52,lp85,ls20,m0r0,r11l,re86,s5i5,sb26,sc25,sk48,sp80,su15,tn36,tr87,tu93,vc33,wa30 | 0.00% | 0 | 5142 | - | Offline evaluation runner pass. |
| `eval-perception_search-2026-10-03` | 2026-10-03 | perception_search on ls20,ar25,dc22 | 0.00% | 0 | 407 | - | Offline evaluation runner pass. |
