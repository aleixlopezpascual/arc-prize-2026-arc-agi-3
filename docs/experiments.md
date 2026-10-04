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
| `sub-56806684` | 2026-10-03 | Daniel Franzen M2 Baseline (TAAF + Qwen 3.8 Flash-Next) | 40.25% (10 demo) | 39 / 65 | 1462 | 23.97% | Official baseline evaluation complete! Secured competitive standing on Public Leaderboard. |
| `sub-duck-centroid-v1` | 2026-10-04 | Duck Centroid V1: Franzen M2 + Bbox & Centroid Injection for ACTION6 | 46.72% (10 demo) | 41 / 65 | 1434 | Ready to Submit | Kernel COMPLETE! Mean score jumped from 40.25% to 46.72% (+6.47%). sc25 jumped 0%->25.5%, tu93 tripled 11%->33.3%, ar25 jumped 27%->41.7%. |
| `sub-duck-pacing-v2` | 2026-10-03 | Duck Pacing V2: Centroids + Real Baseline Priority + 185k Token Sink Cap | - | - | - | Queued | Pushed aleixlopez/arc-agi-3-duck-pacing-v2 to Kaggle GPU. Caches human_baseline in PrioritySnapshot and caps runaway games at 185k tokens. |
| `sub-duck-memory-v3` | 2026-10-04 | Duck Memory V3: Centroids + Baseline Pacing + Cross-Level Solved Memory | - | - | - | Built & Ready | Built in submissions/duck_memory_v3/. Injects winning actions & confirmed mechanics from cleared levels into prompts for levels 2+. Ready to push. |

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
