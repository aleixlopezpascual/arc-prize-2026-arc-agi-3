#!/usr/bin/env python3
"""Build Duck V19 (Defragmented Lean Armor) submission package.

Fixes SGLang CUDA OOM:
1. Lowers static KV cache fraction from 0.96 to 0.93 (MEMFRAC=0.93).
   Gives 6.7 GB of dynamic VRAM headroom (up from 3.8 GB) to guarantee
   TileLang/Triton JIT compilation and activations never crash.
2. Enables PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True in the environment.
3. Retains 55-minute startup shield, warmup keepalive, and 900s HTTP retry grace.
4. Retains Duck V12 lean engine and candidate_clicks / candidate_goals.
"""
import json
import shutil
from pathlib import Path

V18_DIR = Path("submissions/duck_v18")
V19_DIR = Path("submissions/duck_v19")
V19_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Create kernel-metadata.json
# ---------------------------------------------------------------------------
metadata = {
    "id": "aleixlopez/arc-agi-3-duck-v19",
    "title": "ARC-AGI-3 Duck V19",
    "code_file": "notebook.ipynb",
    "language": "python",
    "kernel_type": "notebook",
    "is_private": True,
    "enable_gpu": True,
    "enable_tpu": False,
    "enable_internet": False,
    "keywords": ["gpu"],
    "dataset_sources": [
        "dfranzen/pennyroyal-v253",
        "dfranzen/taaf-kaggle-source-bundle-copy"
    ],
    "kernel_sources": [],
    "competition_sources": [
        "arc-prize-2026-arc-agi-3"
    ],
    "model_sources": [
        "dfranzen/albucino-qwen3-8-flash-next-drafter/Transformers/default/1",
        "dfranzen/intel-qwen3.8-flash-next-w4a16-autoround/Transformers/default/1"
    ],
    "docker_image": "gcr.io/kaggle-private-byod/python@sha256:57e612b484cf3df5026ee4dcc3cb176974b22b2bc0937fb1e16132a8be4cb13c",
    "machine_shape": "NvidiaRtxPro6000"
}
(V19_DIR / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2))
print("Wrote submissions/duck_v19/kernel-metadata.json")

# ---------------------------------------------------------------------------
# 2. Build apply_enhancements_v19.py based on Duck V18
# ---------------------------------------------------------------------------
v18_script = (V18_DIR / "apply_enhancements_v18.py").read_text()
(V19_DIR / "apply_enhancements_v19.py").write_text(v18_script)
print("Wrote submissions/duck_v19/apply_enhancements_v19.py")

# ---------------------------------------------------------------------------
# 3. Assemble submissions/duck_v19/notebook.ipynb
# ---------------------------------------------------------------------------
v18_nb = json.loads((V18_DIR / "notebook.ipynb").read_text())

# Cell 0: Title Duck V19
v18_nb["cells"][0]["source"] = [
    l.replace("Duck V18", "Duck V19 (Defragmented Lean Armor + MEMFRAC=0.93 + Expandable Segments)")
    for l in v18_nb["cells"][0]["source"]
]

# Cell 3: %%writefile /kaggle/apply_enhancements_v19.py
v19_body = (V19_DIR / "apply_enhancements_v19.py").read_text()
v18_nb["cells"][3]["source"] = [
    "%%writefile /kaggle/apply_enhancements_v19.py\n"
] + [l + "\n" for l in v19_body.splitlines()[:-1]] + [
    v19_body.splitlines()[-1]
]

# Cell 5: Setup timeout armor & env vars & run apply_enhancements_v19.py
cell5_src = "".join(v18_nb["cells"][5]["source"])
cell5_src = cell5_src.replace("apply_enhancements_v18.py", "apply_enhancements_v19.py")
if "expandable_segments:True" not in cell5_src:
    cell5_src = "import os\nos.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'\n" + cell5_src
v18_nb["cells"][5]["source"] = [l + "\n" for l in cell5_src.splitlines()[:-1]] + [cell5_src.splitlines()[-1]]

# Cell 13: SGLang launcher configuration (MEMFRAC=0.93 and expandable_segments)
cell13_src = "".join(v18_nb["cells"][13]["source"])
cell13_src = cell13_src.replace("MEMFRAC=0.96,", "MEMFRAC=0.93,")
if "expandable_segments:True" not in cell13_src:
    cell13_src = "os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'\n" + cell13_src
v18_nb["cells"][13]["source"] = [l + "\n" for l in cell13_src.splitlines()[:-1]] + [cell13_src.splitlines()[-1]]

(V19_DIR / "notebook.ipynb").write_text(json.dumps(v18_nb, indent=1))
print("Successfully generated submissions/duck_v19/notebook.ipynb")
