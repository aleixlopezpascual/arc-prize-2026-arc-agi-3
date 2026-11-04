import json
from pathlib import Path


def test_duck_v4_notebook_validity():
    nb_path = Path("submissions/duck_v4/notebook.ipynb")
    meta_path = Path("submissions/duck_v4/kernel-metadata.json")

    assert nb_path.exists(), "submissions/duck_v4/notebook.ipynb must exist"
    assert meta_path.exists(), "submissions/duck_v4/kernel-metadata.json must exist"

    meta = json.loads(meta_path.read_text())
    assert meta["id"] == "aleixlopez/arc-agi-3-duck-v4"
    assert meta["enable_gpu"] is True
    assert "dfranzen/pennyroyal-v253" in meta["dataset_sources"]
    assert "dfranzen/taaf-kaggle-source-bundle-copy" in meta["dataset_sources"]
    assert len(meta["model_sources"]) == 2

    nb = json.load(open(nb_path))
    assert len(nb["cells"]) >= 20
    cell3_src = "".join(nb["cells"][3]["source"])
    assert "apply_enhancements_v4.py" in cell3_src
    assert "candidate_clicks" in cell3_src
    assert "object_at" in cell3_src
    assert "is_border" in cell3_src
    assert "solved_memory" in cell3_src
