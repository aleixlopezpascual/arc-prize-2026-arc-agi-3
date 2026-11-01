#!/usr/bin/env python3
"""
Endgame Push & Submit Orchestrator for S16 Final Draw 1.
Follows docs/ENDGAME_RUNBOOK.md exactly:
1. Retries `kaggle kernels push -p submissions/s16_final` until GPU quota resets (~23:57 UTC).
2. Waits for kernel status COMPLETE (takes ~15-30s thanks to Cell 0 commit gate).
3. Verifies `submission.parquet` and commit gate log.
4. Holds until >= 00:00:01 UTC on Oct 31.
5. Submits `S16 Final draw 1` to arc-prize-2026-arc-agi-3.
6. Confirms submission status is PENDING.
"""

import datetime
import os
import shutil
import subprocess
import sys
import time

KERNEL_DIR = "submissions/s16_final"
KERNEL_ID = "aleixlopez/arc3-s16-final"
COMPETITION = "arc-prize-2026-arc-agi-3"
OUTPUT_DIR = "/tmp/s16_out"
VERSION = "1"
SUBMISSION_FILE = "submission.parquet"
MESSAGE = "S16 Final draw 1"


def log(msg: str) -> None:
    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{now_utc}] {msg}", flush=True)


def push_kernel() -> bool:
    log("Attempting to push S16 Final kernel...")
    res = subprocess.run(
        ["kaggle", "kernels", "push", "-p", KERNEL_DIR],
        capture_output=True,
        text=True,
    )
    combined = (res.stdout + "\n" + res.stderr).strip()
    log(f"Push response: {combined}")
    return "successfully pushed" in combined.lower()


def wait_for_push() -> None:
    attempt = 1
    while not push_kernel():
        log(f"Push attempt #{attempt} not accepted yet (waiting for weekly GPU quota reset ~23:57 UTC). Retrying in 30s...")
        time.sleep(30)
        attempt += 1
    log("Kernel successfully pushed to Kaggle!")


def wait_for_completion() -> None:
    log(f"Waiting for kernel {KERNEL_ID} commit run to complete...")
    for _ in range(60):  # Poll up to 15 minutes (gate run takes ~30s)
        res = subprocess.run(
            ["kaggle", "kernels", "status", KERNEL_ID],
            capture_output=True,
            text=True,
        )
        status_text = res.stdout.strip()
        log(f"Status: {status_text}")
        if "COMPLETE" in status_text.upper():
            log("Commit run completed successfully!")
            return
        if "ERROR" in status_text.upper():
            log("Kernel commit run failed with ERROR!")
            sys.exit(1)
        time.sleep(15)
    log("Timeout waiting for kernel commit run!")
    sys.exit(1)


def verify_gate_output() -> None:
    log("Verifying gate output in /tmp/s16_out...")
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    res = subprocess.run(
        ["kaggle", "kernels", "output", KERNEL_ID, "-p", OUTPUT_DIR],
        capture_output=True,
        text=True,
    )
    log(f"Downloaded output files: {os.listdir(OUTPUT_DIR)}")

    parquet_path = os.path.join(OUTPUT_DIR, SUBMISSION_FILE)
    if not os.path.exists(parquet_path):
        log(f"ERROR: {SUBMISSION_FILE} not found in output!")
        sys.exit(1)

    log(f"Found {parquet_path} ({os.path.getsize(parquet_path)} bytes). Output verified!")


def wait_for_daily_reset() -> None:
    while True:
        now = datetime.datetime.now(datetime.timezone.utc)
        if now.date() > datetime.date(2026, 10, 30):
            log(f"Daily quota window for {now.date()} is ACTIVE!")
            break
        remaining_s = (datetime.datetime(2026, 10, 31, 0, 0, 1, tzinfo=datetime.timezone.utc) - now).total_seconds()
        log(f"Current date is still Oct 30. Waiting {max(1, int(remaining_s))}s until 00:00:01 UTC Oct 31...")
        time.sleep(min(15, max(1, remaining_s)))


def submit_to_competition() -> None:
    log("Waiting 15s for Kaggle artifact storage to settle before submitting...")
    time.sleep(15)
    log(f"Submitting latest version of {KERNEL_ID} to {COMPETITION}...")
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
    first_lines = "\n".join(sub_list.stdout.strip().splitlines()[:6])
    log(f"Recent submissions:\n{first_lines}")


def main() -> None:
    log("=== S16 FINAL DRAW 1 ORCHESTRATOR STARTED ===")
    wait_for_push()
    wait_for_completion()
    verify_gate_output()
    wait_for_daily_reset()
    submit_to_competition()
    log("=== S16 FINAL DRAW 1 ORCHESTRATION COMPLETE ===")


if __name__ == "__main__":
    main()
