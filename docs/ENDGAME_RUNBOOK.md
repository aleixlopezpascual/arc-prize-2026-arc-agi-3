# ARC-AGI-3 Endgame Runbook (Oct 30 – Nov 2, 2026)

Self-contained: follow this if the Claude session that set it up is gone.

## Facts

- **Final deadline: 2026-11-02 23:59 UTC.** This deadline covers both submissions and final selections.
- **One submission per UTC day.** The daily counter resets at 00:00 UTC.
- **Field:** 4,983 teams. Bronze = top 10% (about rank 498), silver = top 5% (about rank 249), gold ≈ top 20 (38.22 on Oct 25).
- **Our standing:** rank #809 on Oct 30. Best public score is 30.19 (`56836213`, Centroid V1).
- **Why we use S16:** our Duck kernels average about 26 on the leaderboard. Public **Stack S16** (`ondrewsha/arc-agi-3-stack-s16`) is the strongest Franzen-M2 variant and scores about 31.6.
- **Why repeat runs:** runs of identical code vary a lot. The unmodified Franzen M2 notebook scored both 23.97 and 35.35. Final rank uses the better private score of our 2 selected submissions, so every slot goes to repeat runs of S16 Final.
- **GPU quota:** the weekly quota (30 h) was exhausted on Oct 30 and resets at about **23:57 UTC on Oct 30**. Pushing a kernel needs quota. Submitting an already-run kernel version does not.

## The kernel: S16 Final

- **Files:** `submissions/s16_final/`, built by `python3 scripts/build_s16_final.py`. It is all S16 cells plus a gate cell 0, with **one edit**: token patience `ARC3_PRIORITY_TOKEN_SCALE` 40000 → 200000. The scheduler simulation gives +0.4 to +1.9; see `docs/intel/oct30_scheduler_sim.md`.
  - **Commit run** (Save Version / `kaggle kernels push`): the gate writes a placeholder `submission.parquet` and turns every later cell into `pass`. The run finishes in seconds of GPU.
  - **Competition rerun:** the gate does nothing, and S16 runs exactly as published.
- **Kaggle id:** `aleixlopez/arc3-s16-final`. Version 1 is the first push.
- **Backup notebook:** `submissions/affectify_backup/`, built by `python3 scripts/build_s16_final.py --affectify`. Kaggle id `aleixlopez/arc3-affectify-backup`.
  - It is Affectify D' (`shiiin9/affectify-arc-31-54-in-a-single-sub`), which scored 31.54 on the exact published notebook. It is a different scheduler from S16.
  - It has the same gate. The only edit is the server start-up limit, `12 * 60` -> `55 * 60`.
  - Push it only under the decision rule below.
- **Fallback:** `submissions/s16_final_mf93/`, built by `python3 scripts/build_s16_final.py --memfrac93`. It has the same kernel id. The only change is `MEMFRAC 0.96 -> 0.93`. Push it **only** if an S16 Final run scores 0.00 and its log shows an SGLang CUDA out-of-memory error. It becomes the next version, so submit that version number.

## Schedule

| UTC day | Submission | Status |
|---|---|---|
| Oct 30 | Duck V19 v2 (`57802714`) | Completed, scored **16.43%** |
| Oct 31 | S16 Final v1, run 1 | Pushed v1; Ref **`57843859`** submitted, currently **PENDING** |
| Nov 1 | S16 Final, run 2 | Manual, any time that day, once run 1 has a sane score |
| Nov 2 | S16 Final, run 3 | Manual, **right after 00:00 UTC** so the ~9 h run finishes before 23:59 |
| Nov 2, before 23:59 | Tick the final 2 selections | Manual, on the Kaggle Submissions page |

## Commands

Run from the repo root (or the worktree `.claude/worktrees/competition-medal-strategy-c33307`).

**Oct 31: push and submit run 1** (only if the auto-loop isn't running or has died; it is safe to rerun):
```bash
until kaggle kernels push -p submissions/s16_final 2>&1 | tee /dev/stderr | grep -qi "successfully pushed"; do echo "retry in 60s"; sleep 60; done && until kaggle kernels status aleixlopez/arc3-s16-final 2>&1 | grep -qiE "complete|error"; do sleep 30; done && rm -rf /tmp/s16_out && kaggle kernels output aleixlopez/arc3-s16-final -p /tmp/s16_out && grep -rq "GATE\] commit run" /tmp/s16_out && until [ "$(date -u +%F)" != "2026-10-30" ]; do sleep 60; done && kaggle competitions submit -c arc-prize-2026-arc-agi-3 -k aleixlopez/arc3-s16-final -f submission.parquet -v 1 -m "S16 Final draw 1"
```
If the push already succeeded and only the submit is missing, run just the last part: `kaggle competitions submit ... -v 1 ...`.

**Nov 1 and Nov 2: resubmit the same version.** No push and no GPU needed:
```bash
kaggle competitions submit -c arc-prize-2026-arc-agi-3 -k aleixlopez/arc3-s16-final -f submission.parquet -v 1 -m "S16 Final draw 2"
```
Use `draw 3` on Nov 2.

**Check status and scores:**
```bash
kaggle competitions submissions -c arc-prize-2026-arc-agi-3 | head -8
```

## Decision rules

- **S16 run scores ≥ 27:** resubmit the same version the next day.
- **S16 run scores above 0 but below 27:** switch the remaining days to the Affectify backup. S16's ~31.6 comes from its earlier versions (S8/S9), so a weak first run is a reason to hedge. Push once (seconds of GPU), then submit version 1 on each remaining day:
  ```bash
  kaggle kernels push -p submissions/affectify_backup && until kaggle kernels status aleixlopez/arc3-affectify-backup 2>&1 | grep -qiE "complete|error"; do sleep 30; done && kaggle competitions submit -c arc-prize-2026-arc-agi-3 -k aleixlopez/arc3-affectify-backup -f submission.parquet -v 1 -m "Affectify backup draw 1"
  ```
- **S16 run scores 0.00:** download the log with `kaggle kernels output aleixlopez/arc3-s16-final -p /tmp/s16_out`.
  - If the log shows `CUDA out of memory`: `kaggle kernels push -p submissions/s16_final_mf93`, then submit that new version number the next day.
  - If the log shows any other error: change nothing big. Resubmitting v1 is still the best bet, because a slow machine or start-up timing is the usual cause.
- **Never** spend a slot on Duck V20/V21 or anything with `ls20` replay.
- **Never** use the `scripts/auto_submit_*.py` daemons. They caused lost and wrong submissions (V20 Run 2, V21).
- **Keep GPU quota for this competition.** The ARC-AGI-2 notebooks used up the quota on Oct 29–30.

## Final selection (by Nov 2 23:59 UTC)

1. **Now:** tick Centroid V1 (`56836213`, 30.19) and V12 Run 2 (`57232788`, 29.46) as insurance.
2. **On Nov 2:** swap in the two highest-scoring healthy runs among the S16 Final draws, any Affectify backup draws, and V19 (`57802714`).
   - Keep Centroid V1 only if it still beats them.
   - Don't leave the choice to Kaggle's auto-pick.

## Bookkeeping

After each score arrives, add it to:
- the submissions ledger in `docs/HANDOVER.md`
- `docs/experiments.md` (rows `duck_v19_v2_sub`, `s16_final_build`, then one row per run)
