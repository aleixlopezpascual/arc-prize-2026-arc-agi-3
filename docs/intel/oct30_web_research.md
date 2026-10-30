# Oct 30 Web and Kaggle Research: Is There Anything We Are Missing?

*Date: 2026-10-30. Sources: Kaggle API (notebook rankings and downloads), web search (GitHub, the arc.markbarney.net mirror, X).*

## Bottom line

There is no public technique with measured evidence above the noise. The top teams have not published anything; one team says it will release after the deadline, and Yi-Chia Chen (Fields Model) has said he will not open-source his work. **Decision: S16 Final is unchanged.** The endgame plan in `docs/ENDGAME_RUNBOOK.md` stands.

## Leaderboard (Oct 30, 4,984 teams)

| Rank | Team | Score |
|---|---|---|
| 1 | Fields Model | 75.56 |
| 2 | Tufa Labs | 70.02 |
| 3 | "faster machine is all you need" (new, no write-up) | 58.59 |
| 4 | Turducken | 56.02 |
| 8 | NVARC3 | 49.54 |

Estimated medal lines: gold ≈ 38.2 (rank 19), silver ≈ 32.3, bronze ≈ 31.0.

## Top public notebooks are plain Franzen M2

Kaggle's "best score" sort, with each notebook diffed against `submissions/franzen_m2_baseline/`. Local copies are in `notebooks/public_baselines/inspections/oct30_top/`.

| Rank | Notebook | Change vs Franzen M2 |
|---|---|---|
| #1 | `romantamrazov/the-agi-boys-i-am-better` | none (byte-identical) |
| #2 | `dfranzen/arc-agi-3-milestone-2-solution` | offline-demo settings only |
| #3 | `vickyfym/arc-agi-3-lalalia-final` | 55-min start-up limit + solved-level memory |
| #4 | `yongjiehishi/arc3-duck-lab-t06` | input-path finder + D'. Its author reports **8 draws: 22.06–31.05** |
| #5 | `evgendvorkin/arc-3-2026` | none (byte-identical) |
| #13 / #16 | Stack S9 / Stack S16 | large harness patches |

The public scoreboard rewards luck and the number of copies run, not ideas.

## Noise (documented)

- Plain Franzen M2 across forum runs: mean 25.77, SD 3.93.
- D' vs plain M2, 4 runs each: 27.10 vs 26.52, a tie.
- Two runs of identical code differed by −1.72 ± 4.74, with an average swing of 14 points per game.

## Candidate changes vs S16 Final

| Candidate | Evidence | S16 Final |
|---|---|---|
| Longer gateway wait (a ~33.7 run fell to 8.61 in a >10-min outage; fix waits 1,800 s) | documented, no A/B | already in: `_wait_for_gateway` 3,600 s |
| Keep-alive during model load (611–1,472 s measured) | documented | already in (the KA cell) |
| `ARC3_MEMORY_SECTIONS` off (unused in all 27 public notebooks ≥ 30) | documented | already off |
| Fallback when `KAGGLE_IS_COMPETITION_RERUN` is unreadable: treat a reachable `http://gateway:8001/` as a scored run (ppx16: 2× 0.00, cause unconfirmed) | weak | not in. Skipped: all 15+ of our runs read the flag fine |
| Drop solved-level memory (5 runs average 25.2 vs D'-only 27.9) | confounded, within noise | kept |
| `ARC3_NOOP_REPEAT_GUARD=1` (+3.3 ± 5.4 in practice; one LB run 23.57; su15/wa30 nearly stopped acting) | noisy | not adopted |
| Keep helper functions across timeouts (+2.8 ± 5.7), `ARC3_STRATEGY_AUDIT=1` (+1.9 ± 6.3), death-repeat guard (no score) | noise | not adopted |
| Serving: MEMFRAC > 0.96, 12–14 streams and temperature changes are all negative; MTP 5 steps is only +4% over 3 (vLLM, off-stack) | documented negatives | Franzen settings kept |

Other negatives:
- Win-path replay: a second `make` is refused and the scorecard never closes, giving 0.00.
- A ppx16 D' variant produced no output online and scored 0.00.
- ThinkingCap model: 62.24 vs 74.47.

## Sources

- https://raw.githubusercontent.com/da-fr/arc-agi-3-solution/main/WRITEUP.md
- https://github.com/mayankraj4728/ARC-AGI-3-2026
- https://github.com/ppx16/arc-agi-3-ledger/issues/1
- https://github.com/guoyi12311125-netizen/arc3-repeat-controlled-eval
- https://github.com/charleneleong-ai/tgaer/pull/61
- https://arc.markbarney.net/arc-leaderboards
- https://github.com/lastloop-ai/vllm-blackwell-guide
