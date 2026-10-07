import json
from pathlib import Path

def test_duck_v5_notebook_validity():
    nb_path = Path("submissions/duck_v5/notebook.ipynb")
    meta_path = Path("submissions/duck_v5/kernel-metadata.json")

    assert nb_path.exists(), "submissions/duck_v5/notebook.ipynb must exist"
    assert meta_path.exists(), "submissions/duck_v5/kernel-metadata.json must exist"

    meta = json.loads(meta_path.read_text())
    assert meta["id"] == "aleixlopez/arc-agi-3-duck-v5"
    assert meta["enable_gpu"] is True

    nb = json.load(open(nb_path))
    assert len(nb["cells"]) >= 20
    cell3_src = "".join(nb["cells"][3]["source"])
    assert "apply_enhancements_v5.py" in cell3_src
    assert "candidate_clicks" in cell3_src
    assert "object_at" in cell3_src
    assert "is_border" in cell3_src
    assert "bfs_path" in cell3_src
    assert "if current_frame_payload is not None:" in cell3_src

    cell17_src = "".join(nb["cells"][17]["source"])
    assert "ours_form_priority" in cell17_src
    assert "install_d" in cell17_src
