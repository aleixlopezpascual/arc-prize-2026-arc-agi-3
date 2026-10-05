import subprocess
import sys
import time
from datetime import datetime, timezone

competition = "arc-prize-2026-arc-agi-3"
v3_kernel = "aleixlopez/arc-agi-3-duck-memory-v3"
output_file = "submission.parquet"
message = "Duck Memory V3 (Centroids + Baseline Priority + Solved Level Memory)"

print(
    f"[{datetime.now(timezone.utc).strftime('%X')} UTC] Auto-Submit Daemon for Duck Memory V3 started.",
    flush=True,
)

for _ in range(240):  # Run for up to 20 hours
    now_utc = datetime.now(timezone.utc)
    ts = now_utc.strftime("%Y-%m-%d %H:%M:%S")

    # Check kernel status
    k_res = subprocess.run(
        ["kaggle", "kernels", "status", v3_kernel],
        capture_output=True,
        text=True,
    )
    k_status = k_res.stdout.strip()
    print(f"[{ts} UTC] {v3_kernel} status: {k_status}", flush=True)

    if "COMPLETE" in k_status:
        # Submit to competition
        sub_cmd = [
            "kaggle",
            "competitions",
            "submit",
            "-c",
            competition,
            "-k",
            v3_kernel,
            "-f",
            output_file,
            "-v",
            "1",
            "-m",
            message,
        ]
        sub_res = subprocess.run(sub_cmd, capture_output=True, text=True)
        combined = (sub_res.stdout + " " + sub_res.stderr).strip()

        if "0 submissions remaining today" in combined:
            print(f"[{ts} UTC] V3 complete, waiting for daily quota reset...", flush=True)
        elif "Successfully submitted" in combined or sub_res.returncode == 0:
            print(
                f"\n🎉 [{ts} UTC] Successfully submitted Duck Memory V3 to competition!",
                flush=True,
            )
            print(combined, flush=True)
            sys.exit(0)
        else:
            print(f"[{ts} UTC] Submission attempt response: {combined}", flush=True)

    elif "ERROR" in k_status:
        print(f"\n❌ [{ts} UTC] Kernel {v3_kernel} encountered an error.", flush=True)
        sys.exit(1)

    # Sleep 3 minutes between checks
    time.sleep(180)
