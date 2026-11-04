#!/usr/bin/env python3
"""Autonomous background daemon to monitor and submit Duck V21 (The Fusion Kernel) to Kaggle.

Usage:
    python3 scripts/auto_submit_duck_v21.py [--dry-run]
"""
import argparse
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

COMPETITION = "arc-prize-2026-arc-agi-3"
V21_KERNEL = "aleixlopez/arc-agi-3-duck-v21"
V21_DIR = str(Path(__file__).resolve().parent.parent / "submissions" / "duck_v21")
OUTPUT_FILE = "submission.parquet"
MESSAGE = "Duck V21 (The Fusion Kernel: D-Prime Priority Scheduler + 4-Level Win-Path Cache + Lean Armor)"
UV_PYTHON = sys.executable


def parse_args():
    parser = argparse.ArgumentParser(description="Auto-submit Duck V21")
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution without submitting")
    return parser.parse_args()


def submit_via_api(kernel_slug: str, dry_run: bool = False) -> bool:
    if dry_run:
        print(f"[DRY-RUN] Would submit {kernel_slug} output {OUTPUT_FILE} to {COMPETITION}")
        return True

    safe_message = MESSAGE.replace("'", "")
    submit_script = f"""
from kaggle.api.kaggle_api_extended import KaggleApi
api = KaggleApi()
api.authenticate()
try:
    res = api.competition_submit_code(
        file_name='{OUTPUT_FILE}',
        message='{safe_message}',
        competition='{COMPETITION}',
        kernel='{kernel_slug}',
        kernel_version=None
    )
    print('SUCCESS:', res)
except Exception as e:
    print('ERROR:', e)
"""
    proc = subprocess.run([UV_PYTHON], input=submit_script, text=True, capture_output=True)
    out = (proc.stdout + proc.stderr).strip()
    if "SUCCESS" in out:
        print(f"🎉 Competition submission successful: {out}")
        return True
    else:
        print(f"Submission attempt failed: {out}")
        return False


def get_status(kernel_slug: str) -> str:
    res = subprocess.run(
        ["kaggle", "kernels", "status", kernel_slug],
        capture_output=True,
        text=True
    )
    return res.stdout.strip()


def push_kernel(kernel_dir: str):
    print(f"Pushing kernel from {kernel_dir}...")
    subprocess.run(["kaggle", "kernels", "push", "-p", kernel_dir], check=True)


def main():
    args = parse_args()

    # Step 1: Push kernel if not already running/complete
    current_status = get_status(V21_KERNEL)
    print(f"Current status of {V21_KERNEL}: {current_status}")

    if "not found" in current_status.lower() or "error" in current_status.lower() or not current_status:
        push_kernel(V21_DIR)
        time.sleep(10)

    # Step 2: Loop until COMPLETE, then submit
    while True:
        status_str = get_status(V21_KERNEL)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"[{now}] {V21_KERNEL} status: {status_str}")

        if "COMPLETE" in status_str:
            print(f"\n[{now}] 🏆 Kernel {V21_KERNEL} COMPLETE! Submitting to competition...")
            success = submit_via_api(V21_KERNEL, dry_run=args.dry_run)
            if success:
                print(f"[{now}] ✅ Submitted successfully!")
                break
            else:
                print(f"[{now}] Retrying submission in 300 seconds...")
                time.sleep(300)
        elif "CANCELLED" in status_str or "FAILED" in status_str:
            print(f"[{now}] ❌ Kernel execution failed: {status_str}")
            sys.exit(1)
        else:
            time.sleep(60)


if __name__ == "__main__":
    main()
