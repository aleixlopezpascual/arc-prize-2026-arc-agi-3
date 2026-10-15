import json
from pathlib import Path

def test_duck_v10_notebook_validity():
    nb_path = Path("submissions/duck_v10/notebook.ipynb")
    meta_path = Path("submissions/duck_v10/kernel-metadata.json")

    assert nb_path.exists(), "submissions/duck_v10/notebook.ipynb must exist"
    assert meta_path.exists(), "submissions/duck_v10/kernel-metadata.json must exist"

    meta = json.loads(meta_path.read_text())
    assert meta["id"] == "aleixlopez/arc-agi-3-duck-v10"
    assert meta["title"] == "ARC-AGI-3 Duck V10"
    assert meta["enable_gpu"] is True

    nb = json.load(open(nb_path))
    assert len(nb["cells"]) >= 20

    cell3_src = "".join(nb["cells"][3]["source"])
    assert "apply_enhancements_v10.py" in cell3_src
    assert "candidate_clicks" in cell3_src
    assert "bfs_path" in cell3_src
    assert "FABLE_CORE_SRC" in cell3_src
    assert "level_baseline" in cell3_src

    cell5_src = "".join(nb["cells"][5]["source"])
    assert "apply_enhancements_v10.py" in cell5_src
    assert "ARC3_FABLE_LAYER" in cell5_src
    assert "ARC3_FABLE_EVENTS_AFTER_TOKENS" in cell5_src
    assert "30000" in cell5_src
    assert "LOCAL_ANALYZER_TEMPERATURE" in cell5_src
    assert "0.6" in cell5_src

    cell17_src = "".join(nb["cells"][17]["source"])
    assert "bm.solver.max_generated_tokens_per_game = 185000" not in cell17_src
    assert "ours_form_priority" not in cell17_src
    assert "install_d" not in cell17_src
