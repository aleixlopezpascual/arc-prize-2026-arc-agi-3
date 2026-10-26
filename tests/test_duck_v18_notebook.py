import json
from pathlib import Path
import pytest


def test_duck_v18_notebook_structure():
    meta_path = Path("submissions/duck_v18/kernel-metadata.json")
    nb_path = Path("submissions/duck_v18/notebook.ipynb")

    assert meta_path.exists(), "kernel-metadata.json must exist"
    assert nb_path.exists(), "notebook.ipynb must exist"

    with open(meta_path) as f:
        meta = json.load(f)
    assert meta["id"] == "aleixlopez/arc-agi-3-duck-v18"
    assert meta.get("enable_gpu") is True
    assert meta.get("machine_shape") == "NvidiaRtxPro6000"

    with open(nb_path) as f:
        nb = json.load(f)
    assert len(nb["cells"]) >= 20

    text = json.dumps(nb)
    # Check infra armor
    assert "55 * 60" in text, "Must contain 55min server startup timeout"
    assert "ARC3_WARMUP_ACTION_GAMES" in text, "Must contain warmup action keepalive flag"
    assert "ARC3_HTTP_RETRY_INITIAL_SECONDS" in text, "Must contain HTTP retry grace period"

    # Check perception & lean core
    assert "candidate_clicks" in text, "Must contain candidate_clicks"
    assert "candidate_goals" in text, "Must contain candidate_goals"
    assert "solved_memory" in text, "Must contain solved_memory"

    # Check lean execution (NO aggressive batch early stopping / stagnation alert from V15)
    assert "stagnation_alert" not in text, "Must NOT contain V15 stagnation alert early stopping"
