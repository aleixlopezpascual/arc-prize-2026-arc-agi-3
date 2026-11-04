#!/usr/bin/env python3
"""Autonomous background daemon to monitor and submit Duck V19 to Kaggle.

Usage:
    python3 scripts/auto_submit_duck_v19.py [--dry-run]
"""
import argparse
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

COMPETITION = "arc-prize-2026-arc-agi-3"
V19_KERNEL = "aleixlopez/arc-agi-3-duck-v19"
V19_DIR = str(Path(__file__).resolve().parent.parent / "submissions" / "duck_v19")
OUTPUT_FILE = "submission.parquet"
MESSAGE = "Duck V19 (Defragmented Lean Armor + MEMFRAC=0.93 + Expandable Segments)"
UV_PYTHON = sys.executable


def parse_args():
    parser = argparse.ArgumentParser(description="Auto-submit Duck V19")
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution without submitting")
    return parser.parse_args()


def submit_via_api(kernel_slug: str, dry_run: bool = False) -> bool:
    if dry_run:
        print(f"[DRY-RUN] Would submit {kernel_slug} output {OUTPUT_FILE} to {COMPETITION}")
        return True

    submit_script = f"""
from kaggle.api.kaggle_api_extended import KaggleApi
api = KaggleApi()
api.authenticate()
try:
    res = api.competition_submit_code(
        file_name='{OUTPUT_FILE}',
        message='{MESSAGE}',
        competition='{COMPETITION}',
        kernel='{kernel_slug}',
        kernel_version=1
    )
    print('SUCCESS:', res)
except Exception as e:
    print('ERROR:', e)
"""
    proc = subprocess.run([UV_PYTHON], input=submit_script, text=True, capture_output=True)
    out = (proc.stdout + " " + proc.stderr).strip()
    if "SUCCESS:" in out:
        print("Successfully submitted:", out)
        return True
    else:
        print("Submission attempt failed:", out)
        return False


def main():
    args = parse_args()
    print(f"[{datetime.now(timezone.utc).strftime('%X')} UTC] Auto-Submit Daemon for Duck V19 started.", flush=True)

    v19_pushed = False

    for attempt in range(480):  # up to 16 hours
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        # 1. Push kernel
        if not v19_pushed:
            if args.dry_run:
                print(f"[{ts} UTC] [DRY-RUN] Push simulated for {V19_DIR}")
                v19_pushed = True
            else:
                push_res = subprocess.run(["kaggle", "kernels", "push", "-p", V19_DIR], capture_output=True, text=True)
                combined = (push_res.stdout + " " + push_res.stderr).strip()
                if "successfully pushed" in combined or "Your kernel has been pushed" in combined or "already exists" in combined:
                    print(f"[{ts} UTC] 🚀 Duck V19 successfully pushed to Kaggle GPU!", flush=True)
                    v19_pushed = True
                elif "Maximum batch GPU session count" in combined:
                    if attempt % 5 == 0:
                        print(f"[{ts} UTC] Waiting for Kaggle batch GPU slot to open...", flush=True)
                    time.sleep(120)
                    continue
                else:
                    print(f"[{ts} UTC] Push returned: {combined}", flush=True)
                    time.sleep(60)
                    continue

        if args.dry_run:
            print(f"[{ts} UTC] [DRY-RUN] Status check passed. Exiting dry-run.")
            sys.exit(0)

        # 2. Check kernel status
        k_res = subprocess.run(["kaggle", "kernels", "status", V19_KERNEL], capture_output=True, text=True)
        k_status = k_res.stdout.strip()
        print(f"[{ts} UTC] {V19_KERNEL} status: {k_status}", flush=True)

        if "COMPLETE" in k_status:
            print(f"\n[{ts} UTC] 🏆 Kernel {V19_KERNEL} COMPLETE! Submitting to competition...", flush=True)
            success = submit_via_api(V19_KERNEL, dry_run=args.dry_run)
            if success:
                print(f"🎉 [{ts} UTC] Duck V19 submission complete!")
                sys.exit(0)
            else:
                print(f"[{ts} UTC] Retrying submission in 300 seconds...", flush=True)
                time.sleep(300)
        elif "ERROR" in k_status:
            print(f"[{ts} UTC] ❌ Kernel finished with failure status: {k_status}", flush=True)
            sys.exit(1)

        time.sleep(120)


if __name__ == "__main__":
    main()
