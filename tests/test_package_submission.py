import json
from pathlib import Path

from src.package_submission import package_agent_submission


def test_package_submission_creates_valid_notebook(tmp_path: Path):
    output_path = tmp_path / "submission_random.ipynb"
    package_agent_submission(agent_name="random", output_path=output_path)

    assert output_path.exists()
    with open(output_path) as f:
        nb = json.load(f)

    assert "cells" in nb
    assert len(nb["cells"]) == 4
    # Cell 0: pip install wheels
    assert "pip install" in "".join(nb["cells"][0]["source"])
    # Cell 1: agent code inlined
    assert "RandomAgent" in "".join(nb["cells"][1]["source"])
    # Cell 2: gateway rerun logic
    assert "KAGGLE_IS_COMPETITION_RERUN" in "".join(nb["cells"][2]["source"])
    # Cell 3: dummy parquet
    assert "submission.parquet" in "".join(nb["cells"][3]["source"])
