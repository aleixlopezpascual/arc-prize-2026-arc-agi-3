import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

competition = "arc-prize-2026-arc-agi-3"
v4_kernel = "aleixlopez/arc-agi-3-duck-v4"
output_file = "submission.parquet"
message = "Duck V4 (+10.09% Demo Gain, 56.81% Benchmark, 48/65 levels)"

print(
    f"[{datetime.now(timezone.utc).strftime('%X')} UTC] Midnight Auto-Submit Daemon for Duck V4 started.",
    flush=True,
)

for _ in range(240):  # Run for up to 20 hours
    now_utc = datetime.now(timezone.utc)
    ts = now_utc.strftime("%Y-%m-%d %H:%M:%S")

    # Submit Version 4 to competition
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
        "-v",
        "4",
        "-m",
        message,
    ]
    sub_res = subprocess.run(sub_cmd, capture_output=True, text=True)
    combined = (sub_res.stdout + " " + sub_res.stderr).strip()

    if "Successfully submitted" in combined or sub_res.returncode == 0:
        print(
            f"\n🎉 [{ts} UTC] Successfully submitted Duck V4 to competition!",
            flush=True,
        )
        print(combined, flush=True)
        sys.exit(0)
    elif "0 submissions remaining today" in combined:
        print(f"[{ts} UTC] 0 submissions remaining today. Waiting for midnight UTC reset...", flush=True)
    else:
        print(f"[{ts} UTC] Submission attempt response: {combined}", flush=True)

    time.sleep(60)  # Check every 60 seconds around midnight
