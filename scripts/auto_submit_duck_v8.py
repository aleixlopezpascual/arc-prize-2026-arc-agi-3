import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

competition = "arc-prize-2026-arc-agi-3"
v8_kernel = "aleixlopez/arc-agi-3-duck-v8"
v8_dir = "/Users/aleix.lopez/arc-prize-2026-arc-agi-3/submissions/duck_v8"
output_file = "submission.parquet"
message = "Duck V8 (Fable Layer Diagnostics + Perception + Search + Unconstrained Priority Scheduling)"

print(
    f"[{datetime.now(timezone.utc).strftime('%X')} UTC] Auto-Submit Daemon for Duck V8 staged & started.",
    flush=True,
)

v8_pushed = True

for attempt in range(480):  # Run for up to 24 hours
    now_utc = datetime.now(timezone.utc)
    ts = now_utc.strftime("%Y-%m-%d %H:%M:%S")

    # 1. Try pushing Duck V8 if not yet pushed
    if not v8_pushed:
        push_res = subprocess.run(
            ["kaggle", "kernels", "push", "-p", v8_dir],
            capture_output=True,
            text=True,
        )
        combined_push = (push_res.stdout + " " + push_res.stderr).strip()

        if "successfully pushed" in combined_push or "Your kernel has been pushed" in combined_push:
            print(f"[{ts} UTC] 🚀 Duck V8 successfully pushed to Kaggle GPU!", flush=True)
            v8_pushed = True
        elif "Maximum batch GPU session count" in combined_push:
            if attempt % 5 == 0:
                print(f"[{ts} UTC] Waiting for Kaggle batch GPU slot to open...", flush=True)
            time.sleep(120)
            continue
        else:
            print(f"[{ts} UTC] Push attempt returned: {combined_push}", flush=True)
            if "already exists" in combined_push or "Kernel" in combined_push:
                v8_pushed = True
            else:
                time.sleep(60)
                continue

    # 2. Check kernel status
    k_res = subprocess.run(
        ["kaggle", "kernels", "status", v8_kernel],
        capture_output=True,
        text=True,
    )
    k_status = k_res.stdout.strip()
    print(f"[{ts} UTC] {v8_kernel} status: {k_status}", flush=True)

    if "COMPLETE" in k_status:
        print(f"\n[{ts} UTC] 🏆 Kernel {v8_kernel} COMPLETE! Fetching demo summary...", flush=True)
        subprocess.run(["mkdir", "-p", "/tmp/v8_output"])
        subprocess.run(["kaggle", "kernels", "output", v8_kernel, "-p", "/tmp/v8_output"], capture_output=True, text=True)
        summary_file = Path("/tmp/v8_output/summary.txt")
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
            v8_kernel,
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
            print(f"[{ts} UTC] V8 complete, waiting for daily quota reset at 00:00 UTC...", flush=True)
            time.sleep(300)
            continue
        elif "Successfully submitted" in combined or sub_res.returncode == 0:
            print(
                f"\n🎉 [{ts} UTC] Successfully submitted Duck V8 to competition!",
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
