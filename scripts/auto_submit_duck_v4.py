import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

competition = "arc-prize-2026-arc-agi-3"
v4_kernel = "aleixlopez/arc-agi-3-duck-v4"
output_file = "submission.parquet"
message = "Duck V4 (Centroids + candidate_clicks/object_at/is_border + Zero-Prompt-Drift Solved Memory)"

print(
    f"[{datetime.now(timezone.utc).strftime('%X')} UTC] Auto-Submit Daemon for Duck V4 started.",
    flush=True,
)

for _ in range(240):  # Run for up to 20 hours
    now_utc = datetime.now(timezone.utc)
    ts = now_utc.strftime("%Y-%m-%d %H:%M:%S")

    # Check kernel status
    k_res = subprocess.run(
        ["kaggle", "kernels", "status", v4_kernel],
        capture_output=True,
        text=True,
    )
    k_status = k_res.stdout.strip()
    print(f"[{ts} UTC] {v4_kernel} status: {k_status}", flush=True)

    if "COMPLETE" in k_status:
        print(f"\n[{ts} UTC] 🏆 Kernel {v4_kernel} COMPLETE! Fetching demo summary...", flush=True)
        subprocess.run(["mkdir", "-p", "/tmp/v4_output"])
        subprocess.run(["kaggle", "kernels", "output", v4_kernel, "-p", "/tmp/v4_output"], capture_output=True, text=True)
        summary_file = Path("/tmp/v4_output/summary.txt")
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
            v4_kernel,
            "-f",
            output_file,
            "-m",
            message,
        ]
        sub_res = subprocess.run(sub_cmd, capture_output=True, text=True)
        combined = (sub_res.stdout + " " + sub_res.stderr).strip()

        if "0 submissions remaining today" in combined:
            print(f"[{ts} UTC] V4 complete, waiting for daily quota reset at 00:00 UTC...", flush=True)
        elif "Successfully submitted" in combined or sub_res.returncode == 0:
            print(
                f"\n🎉 [{ts} UTC] Successfully submitted Duck V4 to competition!",
                flush=True,
            )
            print(combined, flush=True)
            sys.exit(0)
        else:
            print(f"[{ts} UTC] Submission attempt response: {combined}", flush=True)

    elif "ERROR" in k_status or "CANCELLED" in k_status:
        print(f"[{ts} UTC] ❌ Kernel finished with failure status: {k_status}", flush=True)
        sys.exit(1)

    time.sleep(300)  # Check every 5 minutes
