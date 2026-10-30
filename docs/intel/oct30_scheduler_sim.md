# Oct 30: S16 Token Patience 40k → 200k (Scheduler Simulation)

## Question

Stack S16 tunes Franzen's slot-priority formula with:
- `ARC3_PRIORITY_HUMAN_ACTIONS = 100` (was 25)
- `ARC3_PRIORITY_TOKEN_SCALE = 40000` (was 62000)

The token scale is the "patience" term: a level's priority halves after this many tokens without a clear (`0.5 ** ((t / scale) ** 2)`). Is 40k the right patience?

## Instrument

tantan0327's CPU simulator `scripts/sched_sim.py` (github.com/tantan0327/arc-agi-3-agent, MIT-0, snapshot 2cd59c3):
- It replays 213 real Franzen M2 trajectories, with 10 slots, a 9-hour wall clock and 110 hidden games.
- Its `base` policy is Franzen's contest configuration, which is S16's formula with human 25 / scale 62k.
- The author calibrated it to the leaderboard (base ≈ 28, D' ≈ 30). Per their 60-minute traces, an all-knowing scheduler is worth only about +4 over base.

**Script:** `scripts/sched_sim_s16_patience.py <clone> <seed0> <hard-hazard-scale>`.
- 5 regimes from the author's calibrated search (difficulty 1.15): main, harder, easier, mix, allhard.
- 16 paired seeds per run. The table below reports the gain over S16 as shipped.

## Results (mean paired gain vs S16 (100, 40k); 16 seeds each)

| Seed set / hard-game hazard | main | harder | easier | mix | allhard |
|---|---|---|---|---|---|
| 100 / 1.0, **200k** | ≈+0.6 | ≈+1.7 | ≈+1.0 | ≈+0.7 | ≈+0.7 |
| 200 / 1.0, **200k** | +0.64 | +1.90 | +1.48 | +0.52 | +0.63 |
| 300 / 1.0, **200k** | +0.70 | +1.59 | +1.49 | +0.79 | +0.69 |
| 400 / **0.0** (hard games never clear), **200k** | +0.42 | +1.33 | +1.31 | +0.73 | −0.04 |
| 400 / 0.3, **200k** | +0.70 | +1.40 | +1.50 | +0.68 | +0.22 |

Seed set 100 was run before 200k was added, so its row interpolates the 150k and 300k results.

**Reference points:**
- Franzen base (25, 62k) is −0.6 to −2.5 vs S16 everywhere, which agrees with S16's author.
- S16 (100, 62k) is worse than (100, 40k).
- D' is about the same as 150k–300k.
- Longer patience (300k, 500k, never decaying) is about the same as 200k, but slightly worse when hard games never clear.

## Decision

S16 Final (and its MEMFRAC 0.93 fallback) ships with `ARC3_PRIORITY_TOKEN_SCALE = 200000`. This is a one-value edit in S16's own SCH cell, which the harness reads when picking the next game.

- **Expected gain:** about +1 point, against run-to-run noise of SD ≈ 3–4.
- **Supporting real-world evidence:** D' gains on the leaderboard come from patience; a hard 110k token cutoff measured −9 points on the forum; 60-minute traces show slow games clearing after 30–80k tokens per level.
- **Caveat:** the hidden-game population in the simulator is modelled from the 25 public games.
