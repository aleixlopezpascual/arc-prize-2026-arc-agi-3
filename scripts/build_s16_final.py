#!/usr/bin/env python3
"""Build the S16 Final submission package.

Public Stack S16 (ondrewsha/arc-agi-3-stack-s16) verbatim, plus one gate cell at the top:
- Competition rerun (KAGGLE_IS_COMPETITION_RERUN set): the gate does nothing, so every S16
  cell runs exactly as published.
- Commit run ("Save Version"): the gate writes the placeholder submission.parquet that S16
  itself writes after an offline run, then turns every later cell into `pass`. The commit
  finishes in seconds instead of spending GPU quota on model loading and demo games.
"""

import json
import sys
from pathlib import Path

S16_NOTEBOOK = Path("notebooks/public_baselines/inspections/stack-s16/arc-agi-3-stack-s16.ipynb")
S16_METADATA = Path("notebooks/public_baselines/inspections/stack-s16/kernel-metadata.json")
OUT_DIR = Path("submissions/s16_final")
# Fallback for an SGLang OOM at S16's MEMFRAC=0.96 (what zeroed our Duck V18): same kernel id, one value changed.
MF93_DIR = Path("submissions/s16_final_mf93")

GATE_SOURCE = """\
# S16 Final gate: a commit run skips the whole notebook; a competition rerun is untouched.
import os

if os.environ.get("KAGGLE_IS_COMPETITION_RERUN", "").strip().lower() not in {"1", "true"}:
    from pathlib import Path

    import pandas as pd

    Path("/kaggle/working").mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [["1_0", "1", True, 1]],
        columns=["row_id", "game_id", "end_of_game", "score"],
    ).to_parquet("/kaggle/working/submission.parquet", index=False)
    get_ipython().input_transformers_post.append(lambda lines: ["pass\\n"])
    print("[GATE] commit run: placeholder submission.parquet written, remaining cells skipped")
else:
    print("[GATE] competition rerun: running Stack S16 unchanged")
"""


def build(memfrac93: bool = False) -> None:
    out_dir = MF93_DIR if memfrac93 else OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    nb = json.loads(S16_NOTEBOOK.read_text())
    gate_cell = {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": GATE_SOURCE.splitlines(keepends=True),
    }
    nb["cells"].insert(0, gate_cell)
    if memfrac93:
        # Kaggle stores each cell's source as one string, not a list of lines.
        hits = [c for c in nb["cells"] if "MEMFRAC=0.96," in "".join(c["source"])]
        assert len(hits) == 1, "expected exactly one MEMFRAC=0.96 setting"
        hits[0]["source"] = "".join(hits[0]["source"]).replace("MEMFRAC=0.96,", "MEMFRAC=0.93,")
    (out_dir / "notebook.ipynb").write_text(json.dumps(nb, indent=1))

    metadata = json.loads(S16_METADATA.read_text())
    for key in ("id_no",):
        metadata.pop(key, None)
    metadata.update(
        {
            "id": "aleixlopez/arc3-s16-final",
            "title": "ARC3 S16 Final",
            "code_file": "notebook.ipynb",
            "is_private": True,
        }
    )
    (out_dir / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Wrote {out_dir}/notebook.ipynb ({len(nb['cells'])} cells) and kernel-metadata.json")


if __name__ == "__main__":
    build(memfrac93="--memfrac93" in sys.argv)
