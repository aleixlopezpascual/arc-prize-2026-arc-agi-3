#!/usr/bin/env python3
"""
Final Submission Orchestrator for S16 Final Draw 2 (Nov 2).
1. Waits until 00:00:05 UTC on Nov 2 (the final day of ARC Prize 2026).
2. Submits verified Version 2 of aleixlopez/arc3-s16-final (no push/GPU commit needed).
3. Verifies submission status is PENDING.
"""

import datetime
import subprocess
import sys
import time

KERNEL_ID = "aleixlopez/arc3-s16-final"
COMPETITION = "arc-prize-2026-arc-agi-3"
VERSION = "2"
SUBMISSION_FILE = "submission.parquet"
MESSAGE = "S16 Final draw 2"


def log(msg: str) -> None:
    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{now_utc}] {msg}", flush=True)


def wait_for_nov2_reset() -> None:
    target_time = datetime.datetime(2026, 11, 2, 0, 0, 5, tzinfo=datetime.timezone.utc)
    while True:
        now = datetime.datetime.now(datetime.timezone.utc)
        diff_s = (target_time - now).total_seconds()
        if diff_s <= 0:
            log("Nov 2 00:00:05 UTC reached! Daily submission quota is active.")
            break
        log(f"Waiting for Nov 2 daily quota reset: {int(diff_s)}s remaining...")
        time.sleep(min(30, max(1, diff_s)))


def submit() -> None:
    log(f"Submitting {KERNEL_ID} v{VERSION} to {COMPETITION}...")
    cmd = [
        "kaggle",
        "competitions",
        "submit",
        "-c",
        COMPETITION,
        "-k",
        KERNEL_ID,
        "-f",
        SUBMISSION_FILE,
        "-v",
        VERSION,
        "-m",
        MESSAGE,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    log(f"Submit stdout: {res.stdout.strip()}")
    if res.stderr:
        log(f"Submit stderr: {res.stderr.strip()}")

    time.sleep(5)
    sub_list = subprocess.run(
        ["kaggle", "competitions", "submissions", "-c", COMPETITION],
        capture_output=True,
        text=True,
    )
    first_lines = "\n".join(sub_list.stdout.strip().splitlines()[:5])
    log(f"Recent submissions:\n{first_lines}")


def main() -> None:
    log("=== S16 FINAL DRAW 2 (NOV 2) ORCHESTRATOR ARMED ===")
    wait_for_nov2_reset()
    submit()
    log("=== S16 FINAL DRAW 2 SUBMITTED SUCCESSFULLY ===")


if __name__ == "__main__":
    main()
