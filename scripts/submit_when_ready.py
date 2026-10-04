import subprocess
import sys
import time

kernel = "aleixlopez/arc-agi-3-franzen-m2-baseline"
competition = "arc-prize-2026-arc-agi-3"
version = "2"
output_file = "submission.parquet"
message = "Daniel Franzen M2 Baseline 27.89%"

print(f"Monitoring {kernel} for completion...", flush=True)

for _ in range(60):  # Poll up to 20 minutes
    res = subprocess.run(
        ["kaggle", "kernels", "status", kernel],
        capture_output=True,
        text=True,
    )
    out = res.stdout.strip()
    print(f"[{time.strftime('%X')}] Status: {out}", flush=True)

    if "COMPLETE" in out:
        print("\n✅ Kernel finished! Submitting to competition...", flush=True)
        submit_cmd = [
            "kaggle",
            "competitions",
            "submit",
            "-c",
            competition,
            "-k",
            kernel,
            "-f",
            output_file,
            "-v",
            version,
            "-m",
            message,
        ]
        sub_res = subprocess.run(submit_cmd, capture_output=True, text=True)
        print("Submission output:", flush=True)
        print(sub_res.stdout, flush=True)
        if sub_res.stderr:
            print("Errors:", sub_res.stderr, flush=True)
        sys.exit(0)
    elif "ERROR" in out:
        print("\n❌ Kernel encountered an ERROR.", flush=True)
        sys.exit(1)

    time.sleep(20)
