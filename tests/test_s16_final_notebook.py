import json
from pathlib import Path


def test_s16_final_notebook_structure():
    meta_path = Path("submissions/s16_final/kernel-metadata.json")
    nb_path = Path("submissions/s16_final/notebook.ipynb")

    assert meta_path.exists(), "kernel-metadata.json must exist"
    assert nb_path.exists(), "notebook.ipynb must exist"

    with open(meta_path) as f:
        meta = json.load(f)
    assert meta["id"] == "aleixlopez/arc3-s16-final"
    assert meta.get("enable_gpu") is True
    assert meta.get("machine_shape") == "NvidiaRtxPro6000"

    with open(nb_path) as f:
        nb = json.load(f)
    assert len(nb["cells"]) >= 25

    all_sources = "\n".join("".join(c.get("source", [])) for c in nb["cells"])

    # Check scheduler tuning
    assert '"ARC3_PRIORITY_TOKEN_SCALE": "200000"' in all_sources, "Must set ARC3_PRIORITY_TOKEN_SCALE=200000"

    # Check resilient mount resolvers
    assert "Resilient mount resolvers" in all_sources, "Must include resilient mount resolvers"
    assert "**/arc_agi_3_wheels" in all_sources, "Must dynamically find arc_agi_3_wheels"
    assert "SERVER_STARTUP_TIMEOUT = 55 * 60" in all_sources, "Must set 55 minute startup timeout"

    # Check commit gate cell 0
    cell0 = nb["cells"][0]
    assert cell0["cell_type"] == "code"
    src0 = "".join(cell0["source"])
    assert "KAGGLE_IS_COMPETITION_RERUN" in src0, "Cell 0 must check KAGGLE_IS_COMPETITION_RERUN"
    assert "submission.parquet" in src0, "Cell 0 must write placeholder submission.parquet"
    assert "input_transformers_post" in src0, "Cell 0 must neutralize later cells in commit run"
