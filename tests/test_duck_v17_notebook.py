import json
from pathlib import Path
import pytest


def test_duck_v17_notebook_structure():
    meta_path = Path("submissions/duck_v17/kernel-metadata.json")
    nb_path = Path("submissions/duck_v17/notebook.ipynb")

    assert meta_path.exists(), "kernel-metadata.json must exist"
    assert nb_path.exists(), "notebook.ipynb must exist"

    with open(meta_path) as f:
        meta = json.load(f)
    assert meta["id"] == "aleixlopez/arc-agi-3-duck-v17"
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

    # Check adaptive primitives
    assert "solve_toggle" in text, "Must contain exact XOR solve_toggle"
    assert "bounded_search" in text, "Must contain bounded_search"
    assert "normalize_notes" in text, "Must contain normalize_notes"
    assert "follow_plan" in text, "Must contain follow_plan"

    # Check Duck V12/V15 core configuration
    assert "LOCAL_ANALYZER_TEMPERATURE': '0.6'" in text or "0.6" in text
    assert "ARC3_FABLE_LAYER" in text
    assert "ARC3_NOOP_REPEAT_GUARD" in text
