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
