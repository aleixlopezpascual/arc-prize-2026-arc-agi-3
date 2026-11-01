#!/usr/bin/env python3
"""Build the endgame submission packages: a public notebook verbatim plus one gate cell at the top.

- Competition rerun (KAGGLE_IS_COMPETITION_RERUN set): the gate does nothing, so every published
  cell runs as is (with resilient path resolvers and tuned scheduler).
- Commit run ("Save Version"): the gate writes the placeholder submission.parquet that these
  notebooks themselves write after an offline run, then turns every later cell into `pass`. The
  commit finishes in seconds instead of spending GPU quota on model loading and demo games.

Variants (select with a flag; no flag builds S16 Final):
- (default)     S16 Final: Stack S16 (ondrewsha/arc-agi-3-stack-s16), token patience 40k -> 200k.
- --memfrac93   S16 Final with MEMFRAC 0.96 -> 0.93, the fallback for an SGLang OOM (what zeroed
                our Duck V18). Same kernel id, so pushing it becomes the next version.
- --affectify   Affectify D' (shiiin9/affectify-arc-31-54-in-a-single-sub, 31.54 LB), the backup if
                S16 Final scores between 0 and 27.
"""

import json
import sys
from pathlib import Path

INSPECTIONS = Path("notebooks/public_baselines/inspections")
S16_METADATA = INSPECTIONS / "stack-s16/kernel-metadata.json"

# Token patience 40k -> 200k in S16's SCH cell
PATIENCE_200K = ('"ARC3_PRIORITY_TOKEN_SCALE": "40000"', '"ARC3_PRIORITY_TOKEN_SCALE": "200000"')

# Server startup timeout 12 -> 55 min
STARTUP_TIMEOUT_55M = ("SERVER_STARTUP_TIMEOUT = 12 * 60", "SERVER_STARTUP_TIMEOUT = 55 * 60")

# Resilient mount resolvers for datasets and models attached via Kaggle CLI
MOUNT_RESOLVER_OLD = """\
ORIG_BUNDLE_DIR   = '/kaggle/input/datasets/dfranzen/taaf-kaggle-source-bundle-copy'
SERVED_MODEL_NAME = 'flashnext'
"""

MOUNT_RESOLVER_NEW = """\
ORIG_BUNDLE_DIR   = '/kaggle/input/datasets/dfranzen/taaf-kaggle-source-bundle-copy'
SERVED_MODEL_NAME = 'flashnext'

# Resilient mount resolvers
for _ in range(30):
    if Path(ORIG_BUNDLE_DIR).exists() or Path('/kaggle/input/taaf-kaggle-source-bundle-copy').exists():
        break
    time.sleep(1)

if not Path(ORIG_BUNDLE_DIR).exists() and Path('/kaggle/input/taaf-kaggle-source-bundle-copy').exists():
    ORIG_BUNDLE_DIR = '/kaggle/input/taaf-kaggle-source-bundle-copy'

for p in ['/kaggle/input/datasets/dfranzen/pennyroyal-v253', '/kaggle/input/pennyroyal-v253']:
    if Path(p).exists():
        WHEELHOUSE_DIR = p
        break

for p in [
    '/kaggle/input/models/dfranzen/intel-qwen3.8-flash-next-w4a16-autoround/transformers/default/1',
    '/kaggle/input/intel-qwen3.8-flash-next-w4a16-autoround/transformers/default/1',
    '/kaggle/input/intel-qwen3.8-flash-next-w4a16-autoround/Transformers/default/1',
    '/kaggle/input/models/dfranzen/intel-qwen3.8-flash-next-w4a16-autoround/Transformers/default/1',
]:
    if Path(p).exists():
        MODEL_DIR = p
        break

for p in [
    '/kaggle/input/models/dfranzen/albucino-qwen3-8-flash-next-drafter/transformers/default/1',
    '/kaggle/input/albucino-qwen3-8-flash-next-drafter/transformers/default/1',
    '/kaggle/input/albucino-qwen3-8-flash-next-drafter/Transformers/default/1',
    '/kaggle/input/models/dfranzen/albucino-qwen3-8-flash-next-drafter/Transformers/default/1',
]:
    if Path(p).exists():
        DRAFT_MODEL_DIR = p
        break
"""

WHEELS_INSTALL_OLD = """\
        "--find-links",
        "/kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels",
        "arc-agi",\
"""

WHEELS_INSTALL_NEW = """\
        "--find-links",
        str(next(iter(sorted(Path("/kaggle/input").glob("**/arc_agi_3_wheels"))), Path("/kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels"))),
        "arc-agi",\
"""

ENV_FILES_OLD = 'competition_env_files = str(Path("/kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels").parent / "environment_files")'
ENV_FILES_NEW = 'competition_env_files = str(next(iter(sorted(Path("/kaggle/input").glob("**/arc_agi_3_wheels"))), Path("/kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels")).parent / "environment_files")'

S16_SHARED_EDITS = [
    PATIENCE_200K,
    STARTUP_TIMEOUT_55M,
    (MOUNT_RESOLVER_OLD, MOUNT_RESOLVER_NEW),
    (WHEELS_INSTALL_OLD, WHEELS_INSTALL_NEW),
    (ENV_FILES_OLD, ENV_FILES_NEW),
]

VARIANTS = {
    "s16": {
        "notebook": INSPECTIONS / "stack-s16/arc-agi-3-stack-s16.ipynb",
        "out_dir": Path("submissions/s16_final"),
        "id": "aleixlopez/arc3-s16-final",
        "title": "ARC3 S16 Final",
        "label": "Stack S16",
        "edits": S16_SHARED_EDITS,
    },
    "memfrac93": {
        "notebook": INSPECTIONS / "stack-s16/arc-agi-3-stack-s16.ipynb",
        "out_dir": Path("submissions/s16_final_mf93"),
        "id": "aleixlopez/arc3-s16-final",
        "title": "ARC3 S16 Final",
        "label": "Stack S16",
        "edits": S16_SHARED_EDITS + [("MEMFRAC=0.96,", "MEMFRAC=0.93,")],
    },
    "affectify": {
        "notebook": INSPECTIONS / "shiiin9/affectify-arc-31-54-in-a-single-sub.ipynb",
        "out_dir": Path("submissions/affectify_backup"),
        "id": "aleixlopez/arc3-affectify-backup",
        "title": "ARC3 Affectify Backup",
        "label": "Affectify D'",
        "edits": [
            ("SERVER_STARTUP_TIMEOUT = 12 * 60\n", "SERVER_STARTUP_TIMEOUT = 55 * 60\n"),
            (MOUNT_RESOLVER_OLD, MOUNT_RESOLVER_NEW),
            (WHEELS_INSTALL_OLD, WHEELS_INSTALL_NEW),
            (ENV_FILES_OLD, ENV_FILES_NEW),
        ],
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
        hits = [c for c in nb["cells"] if old in "".join(c["source"])]
        assert len(hits) == 1, f"expected exactly one hit for edit:\n{old!r}\nFound: {len(hits)}"
        hits[0]["source"] = "".join(hits[0]["source"]).replace(old, new)
    (out_dir / "notebook.ipynb").write_text(json.dumps(nb, indent=1))

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
