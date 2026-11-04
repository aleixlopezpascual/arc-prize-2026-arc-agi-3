import json
from pathlib import Path


def test_duck_v19_notebook_structure():
    meta_path = Path("submissions/duck_v19/kernel-metadata.json")
    nb_path = Path("submissions/duck_v19/notebook.ipynb")

    assert meta_path.exists(), "kernel-metadata.json must exist"
    assert nb_path.exists(), "notebook.ipynb must exist"

    with open(meta_path) as f:
        meta = json.load(f)
    assert meta["id"] == "aleixlopez/arc-agi-3-duck-v19"
    assert meta.get("enable_gpu") is True
    assert meta.get("machine_shape") == "NvidiaRtxPro6000"

    with open(nb_path) as f:
        nb = json.load(f)
    assert len(nb["cells"]) >= 20

    text = json.dumps(nb)
    # Check memory defragmentation and safe headroom
    assert "MEMFRAC=0.93" in text, "Must set MEMFRAC=0.93 to leave 6.7 GB free dynamic VRAM"
    assert "expandable_segments:True" in text, "Must configure PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True"

    # Check infra armor
    assert "55 * 60" in text, "Must contain 55min server startup timeout"
    assert "ARC3_WARMUP_ACTION_GAMES" in text, "Must contain warmup action keepalive flag"
    assert "ARC3_HTTP_RETRY_INITIAL_SECONDS" in text, "Must contain HTTP retry grace period"

    # Check perception & lean core (Duck V12 peak engine)
    assert "candidate_clicks" in text, "Must contain candidate_clicks"
    assert "object_at" in text, "Must contain object_at"
    assert "bfs_path" in text, "Must contain bfs_path"
    assert "solved_memory" in text, "Must contain solved_memory"
    assert "stagnation_alert" not in text, "Must NOT contain V15 stagnation alert early stopping"


def test_duck_v19_enhancements_syntax_valid():
    script_path = Path("submissions/duck_v19/apply_enhancements_v19.py")
    assert script_path.exists()
    code = script_path.read_text()
    # Must compile without SyntaxError or IndentationError
    compile(code, "apply_enhancements_v19.py", "exec")
