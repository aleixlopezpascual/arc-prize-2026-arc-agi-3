#!/usr/bin/env python3
"""Build the endgame submission packages: a public notebook verbatim plus one gate cell at the top.

- Competition rerun (KAGGLE_IS_COMPETITION_RERUN set): the gate does nothing, so every published
  cell runs as is (apart from the variant's listed edits).
- Commit run ("Save Version"): the gate writes the placeholder submission.parquet that these
  notebooks themselves write after an offline run, then turns every later cell into `pass`. The
  commit finishes in seconds instead of spending GPU quota on model loading and demo games.

Variants (select with a flag; no flag builds S16 Final):
- (default)     S16 Final: Stack S16 (ondrewsha/arc-agi-3-stack-s16), token patience 40k -> 200k.
- --memfrac93   S16 Final with MEMFRAC 0.96 -> 0.93, the fallback for an SGLang OOM (what zeroed
                our Duck V18). Same kernel id, so pushing it becomes the next version.
- --affectify   Affectify D' (shiiin9/affectify-arc-31-54-in-a-single-sub, 31.54 LB), the backup if
                S16 Final scores between 0 and 27. One edit: the server start-up limit 12 -> 55 min,
                since the 12-minute limit zeroed runs on slow machines (forum 753007).
"""

import json
import sys
from pathlib import Path

INSPECTIONS = Path("notebooks/public_baselines/inspections")
S16_METADATA = INSPECTIONS / "stack-s16/kernel-metadata.json"

# Token patience 40k -> 200k in S16's SCH cell: on tantan0327's calibrated scheduler simulator
# (213 real Franzen traces, 5 regimes x 5 seed sets of 16) this gains +0.4..+1.9 over S16's 40k and
# is neutral (-0.04) only when hard games can never clear. See docs/intel/oct30_scheduler_sim.md.
PATIENCE_200K = ('"ARC3_PRIORITY_TOKEN_SCALE": "40000"', '"ARC3_PRIORITY_TOKEN_SCALE": "200000"')

VARIANTS = {
    "s16": {
        "notebook": INSPECTIONS / "stack-s16/arc-agi-3-stack-s16.ipynb",
        "out_dir": Path("submissions/s16_final"),
        "id": "aleixlopez/arc3-s16-final",
        "title": "ARC3 S16 Final",
        "label": "Stack S16",
        "edits": [PATIENCE_200K],
    },
    "memfrac93": {
        "notebook": INSPECTIONS / "stack-s16/arc-agi-3-stack-s16.ipynb",
        "out_dir": Path("submissions/s16_final_mf93"),
        "id": "aleixlopez/arc3-s16-final",
        "title": "ARC3 S16 Final",
        "label": "Stack S16",
        "edits": [PATIENCE_200K, ("MEMFRAC=0.96,", "MEMFRAC=0.93,")],
    },
    "affectify": {
        "notebook": INSPECTIONS / "shiiin9/affectify-arc-31-54-in-a-single-sub.ipynb",
        "out_dir": Path("submissions/affectify_backup"),
        "id": "aleixlopez/arc3-affectify-backup",
        "title": "ARC3 Affectify Backup",
        "label": "Affectify D'",
        "edits": [("SERVER_STARTUP_TIMEOUT = 12 * 60\n", "SERVER_STARTUP_TIMEOUT = 55 * 60\n")],
    },
}

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
    print("[GATE] competition rerun: running LABEL unchanged")
"""


def build(variant: str = "s16") -> None:
    spec = VARIANTS[variant]
    out_dir = spec["out_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    nb = json.loads(spec["notebook"].read_text())
    gate_cell = {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": GATE_SOURCE.replace("LABEL", spec["label"]).splitlines(keepends=True),
    }
    nb["cells"].insert(0, gate_cell)
    for old, new in spec["edits"]:
        # Kaggle stores each cell's source as one string, not a list of lines.
        hits = [c for c in nb["cells"] if old in "".join(c["source"])]
        assert len(hits) == 1, f"expected exactly one {old!r}"
        hits[0]["source"] = "".join(hits[0]["source"]).replace(old, new)
    (out_dir / "notebook.ipynb").write_text(json.dumps(nb, indent=1))

    # All variants load the same dfranzen datasets, models and machine as Stack S16.
    metadata = json.loads(S16_METADATA.read_text())
    metadata.pop("id_no", None)
    metadata.update(
        {
            "id": spec["id"],
            "title": spec["title"],
            "code_file": "notebook.ipynb",
            "is_private": True,
        }
    )
    (out_dir / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Wrote {out_dir}/notebook.ipynb ({len(nb['cells'])} cells) and kernel-metadata.json")


if __name__ == "__main__":
    flags = [arg.removeprefix("--") for arg in sys.argv[1:]]
    build(flags[0] if flags else "s16")
