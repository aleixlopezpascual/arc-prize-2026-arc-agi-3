import subprocess
import sys
import time
from datetime import datetime, timezone

competition = "arc-prize-2026-arc-agi-3"
centroid_kernel = "aleixlopez/arc-agi-3-duck-centroid-v1"
v2_dir = "/Users/aleix.lopez/arc-prize-2026-arc-agi-3/submissions/duck_pacing_v2"

print(
    f"[{datetime.now(timezone.utc).strftime('%X')} UTC] Midnight Auto-Submit Daemon started.",
    flush=True,
)

v1_submitted = False
v2_pushed = False

for _ in range(240):  # Run for up to 20 hours
    now_utc = datetime.now(timezone.utc)
    ts = now_utc.strftime("%Y-%m-%d %H:%M:%S")

    # 1. Try pushing duck_pacing_v2 if not already pushed
    if not v2_pushed:
        res = subprocess.run(
            ["kaggle", "kernels", "push", "-p", v2_dir],
            capture_output=True,
            text=True,
        )
        if "successfully pushed" in res.stdout:
            print(
                f"[{ts} UTC] 🚀 Duck Pacing V2 pushed successfully to Kaggle GPU!",
                flush=True,
            )
            v2_pushed = True
        else:
            err = res.stdout.strip() or res.stderr.strip()
            if "Maximum batch GPU session count" not in err:
                print(f"[{ts} UTC] Pushing V2 status: {err}", flush=True)

    # 2. Try submitting duck_centroid_v1
    if not v1_submitted:
        sub_cmd = [
            "kaggle",
            "competitions",
            "submit",
            "-c",
            competition,
            "-k",
            centroid_kernel,
            "-f",
            "submission.parquet",
            "-v",
            "1",
            "-m",
            "Duck Centroid V1 (+6.47% Demo Gain)",
        ]
        sub_res = subprocess.run(sub_cmd, capture_output=True, text=True)
        combined = (sub_res.stdout + " " + sub_res.stderr).strip()

        if "0 submissions remaining today" in combined:
            # Still waiting for daily quota reset
            pass
        elif "Successfully submitted" in combined or sub_res.returncode == 0:
            print(
                f"\n🎉 [{ts} UTC] Successfully submitted Duck Centroid V1 to competition!",
                flush=True,
            )
            print(combined, flush=True)
            v1_submitted = True
        else:
            print(f"[{ts} UTC] Submission attempt response: {combined}", flush=True)

    if v1_submitted and v2_pushed:
        print(
            f"\n[{ts} UTC] All automated tasks complete! Daemon exiting.",
            flush=True,
        )
        sys.exit(0)

    # Sleep 3 minutes between checks
    time.sleep(180)
