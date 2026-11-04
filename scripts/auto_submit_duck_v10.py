import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

competition = "arc-prize-2026-arc-agi-3"
v10_kernel = "aleixlopez/arc-agi-3-duck-v10"
v10_dir = "/Users/aleix.lopez/arc-prize-2026-arc-agi-3/submissions/duck_v10"
output_file = "submission.parquet"
message = "Duck V10 (Level Baseline Awareness + Calibrated Fable 30k + Temp 0.6 + Unconstrained)"

print(
    f"[{datetime.now(timezone.utc).strftime('%X')} UTC] Auto-Submit Daemon for Duck V10 staged & started.",
    flush=True,
)

v10_pushed = True

for attempt in range(480):  # Run for up to 24 hours
    now_utc = datetime.now(timezone.utc)
    ts = now_utc.strftime("%Y-%m-%d %H:%M:%S")

    # 1. Try pushing Duck V10 if not yet pushed
    if not v10_pushed:
        push_res = subprocess.run(
            ["kaggle", "kernels", "push", "-p", v10_dir],
            capture_output=True,
            text=True,
        )
        combined_push = (push_res.stdout + " " + push_res.stderr).strip()

        if "successfully pushed" in combined_push or "Your kernel has been pushed" in combined_push:
            print(f"[{ts} UTC] 🚀 Duck V10 successfully pushed to Kaggle GPU!", flush=True)
            v10_pushed = True
        elif "Maximum batch GPU session count" in combined_push:
            if attempt % 5 == 0:
                print(f"[{ts} UTC] Waiting for Kaggle batch GPU slot to open...", flush=True)
            time.sleep(120)
            continue
        else:
            print(f"[{ts} UTC] Push attempt returned: {combined_push}", flush=True)
            if "already exists" in combined_push or "Kernel" in combined_push:
                v10_pushed = True
            else:
                time.sleep(60)
                continue

    # 2. Check kernel status
    k_res = subprocess.run(
        ["kaggle", "kernels", "status", v10_kernel],
        capture_output=True,
        text=True,
    )
    k_status = k_res.stdout.strip()
    print(f"[{ts} UTC] {v10_kernel} status: {k_status}", flush=True)

    if "COMPLETE" in k_status:
        print(f"\n[{ts} UTC] 🏆 Kernel {v10_kernel} COMPLETE! Fetching demo summary...", flush=True)
        subprocess.run(["mkdir", "-p", "/tmp/v10_output"])
        subprocess.run(["kaggle", "kernels", "output", v10_kernel, "-p", "/tmp/v10_output"], capture_output=True, text=True)
        summary_file = Path("/tmp/v10_output/summary.txt")
        if summary_file.exists():
            print("=" * 60, flush=True)
            print(summary_file.read_text(), flush=True)
            print("=" * 60, flush=True)

        # Submit to competition
        sub_cmd = [
            "kaggle",
            "competitions",
            "submit",
            "-c",
            competition,
            "-k",
            v10_kernel,
            "-f",
            output_file,
            "-v",
            "1",
            "-m",
            message,
        ]
        sub_res = subprocess.run(sub_cmd, capture_output=True, text=True)
        combined = (sub_res.stdout + " " + sub_res.stderr).strip()

        if "0 submissions remaining today" in combined or "Submission not allowed" in combined or "daily Submission allowance" in combined or "400 Client Error" in combined:
            print(f"[{ts} UTC] V10 complete, waiting for daily quota reset at 00:00 UTC...", flush=True)
            time.sleep(300)
            continue
        elif "Successfully submitted" in combined or sub_res.returncode == 0:
            print(
                f"\n🎉 [{ts} UTC] Successfully submitted Duck V10 to competition!",
                flush=True,
            )
            print(combined, flush=True)
            sys.exit(0)
        else:
            print(f"[{ts} UTC] Submission attempt response: {combined}", flush=True)

    elif "ERROR" in k_status:
        print(f"[{ts} UTC] ❌ Kernel finished with failure status: {k_status}", flush=True)
        sys.exit(1)

    time.sleep(120)  # Check every 2 minutes
