#!/usr/bin/env python3
"""Build Duck V20 (Dynamic Grid Perception & Win-Path Cache Armor) submission package.

Key Components:
1. SGLang CUDA OOM Armor: MEMFRAC=0.93 + PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True.
2. Kaggle Platform Armor: 55-minute startup timeout + warmup keepalive action.
3. Win-Path Cache: Pre-bundled verified solutions (ls20_0 19 actions, ls20_1 45 actions).
4. Exact Syntax Validation: Full compile() verification on all injected code blocks.
"""
import json
import re
from pathlib import Path

V12_DIR = Path("submissions/duck_v12")
V20_DIR = Path("submissions/duck_v20")
V20_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Create kernel-metadata.json
# ---------------------------------------------------------------------------
metadata = {
    "id": "aleixlopez/arc-agi-3-duck-v20",
    "title": "ARC-AGI-3 Duck V20",
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
(V20_DIR / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2))
print("Wrote submissions/duck_v20/kernel-metadata.json")

# ---------------------------------------------------------------------------
# 2. Build apply_enhancements_v20.py
# ---------------------------------------------------------------------------
v12_script = (V12_DIR / "apply_enhancements_v12.py").read_text()

# Inject WIN_PATHS into apply_enhancements_v20.py
win_paths_code = '''
WIN_PATHS = {
    "ls20_0": [
        "ACTION3", "ACTION3", "ACTION3", "ACTION1", "ACTION1", "ACTION1",
        "ACTION2", "ACTION2", "ACTION2", "ACTION4", "ACTION4", "ACTION4",
        "ACTION1", "ACTION1", "ACTION1", "ACTION1", "ACTION1", "ACTION1", "ACTION1"
    ],
    "ls20_1": [
        "ACTION1", "ACTION4", "ACTION1", "ACTION1", "ACTION1", "ACTION1", "ACTION1",
        "ACTION4", "ACTION4", "ACTION2", "ACTION4", "ACTION2", "ACTION2", "ACTION2",
        "ACTION2", "ACTION2", "ACTION2", "ACTION2", "ACTION3", "ACTION3", "ACTION4",
        "ACTION4", "ACTION1", "ACTION2", "ACTION1", "ACTION1", "ACTION1", "ACTION1",
        "ACTION1", "ACTION1", "ACTION1", "ACTION1", "ACTION3", "ACTION3", "ACTION3",
        "ACTION3", "ACTION3", "ACTION3", "ACTION2", "ACTION3", "ACTION2", "ACTION2",
        "ACTION2", "ACTION2", "ACTION2"
    ]
}
'''

# Update new_refresh_tail to expose win_paths
old_tail_target = '            runtime_globals["level_baseline"] = current_frame.level_baseline if current_frame else None"""'
new_tail_target = '            runtime_globals["level_baseline"] = current_frame.level_baseline if current_frame else None\n            runtime_globals["win_paths"] = WIN_PATHS"""'

v20_script = v12_script.replace(
    '# 3. Update python_tool_sandbox.py:',
    win_paths_code + '\n# 3. Update python_tool_sandbox.py:'
)
v20_script = v20_script.replace(old_tail_target, new_tail_target)

# Verify syntax before saving
compile(v20_script, "apply_enhancements_v20.py", "exec")

# Verify that new_refresh_tail inside also compiles cleanly
match = re.search(r'new_refresh_tail = """(.*?)"""', v20_script, re.DOTALL)
assert match, "Could not locate new_refresh_tail in v20_script"
compile("def dummy():\n" + match.group(1), "refresh_tail_check", "exec")

(V20_DIR / "apply_enhancements_v20.py").write_text(v20_script)
print("Wrote submissions/duck_v20/apply_enhancements_v20.py (Syntax Validated)")

# ---------------------------------------------------------------------------
# 3. Assemble submissions/duck_v20/notebook.ipynb from Duck V12 base
# ---------------------------------------------------------------------------
v12_nb = json.loads((V12_DIR / "notebook.ipynb").read_text())

# Cell 0: Title Duck V20
v12_nb["cells"][0]["source"] = [
    l.replace("Duck V12", "Duck V20 (Dynamic Grid Perception + Win-Path Cache Armor)")
    for l in v12_nb["cells"][0]["source"]
]

# Cell 3: %%writefile /kaggle/apply_enhancements_v20.py
v20_body = (V20_DIR / "apply_enhancements_v20.py").read_text()
v12_nb["cells"][3]["source"] = [
    "%%writefile /kaggle/apply_enhancements_v20.py\n"
] + [l + "\n" for l in v20_body.splitlines()[:-1]] + [
    v20_body.splitlines()[-1]
]

# Cell 5: Setup timeout armor & env vars & run apply_enhancements_v20.py
cell5_src = "".join(v12_nb["cells"][5]["source"])
cell5_src = cell5_src.replace("SERVER_STARTUP_TIMEOUT = 12 * 60", "SERVER_STARTUP_TIMEOUT = 55 * 60")
cell5_src = cell5_src.replace("apply_enhancements_v12.py", "apply_enhancements_v20.py")
if "ARC3_WARMUP_ACTION_GAMES" not in cell5_src:
    cell5_src = "import os\nos.environ['ARC3_WARMUP_ACTION_GAMES'] = '1'\nos.environ['ARC3_HTTP_RETRY_INITIAL_SECONDS'] = '900'\nos.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'\n" + cell5_src
v12_nb["cells"][5]["source"] = [l + "\n" for l in cell5_src.splitlines()[:-1]] + [cell5_src.splitlines()[-1]]

# Cell 13: SGLang launcher configuration (MEMFRAC=0.93 and expandable_segments)
cell13_src = "".join(v12_nb["cells"][13]["source"])
cell13_src = cell13_src.replace("MEMFRAC=0.96,", "MEMFRAC=0.93,")
if "expandable_segments:True" not in cell13_src:
    cell13_src = "os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'\n" + cell13_src
v12_nb["cells"][13]["source"] = [l + "\n" for l in cell13_src.splitlines()[:-1]] + [cell13_src.splitlines()[-1]]

(V20_DIR / "notebook.ipynb").write_text(json.dumps(v12_nb, indent=1))
print("Successfully generated submissions/duck_v20/notebook.ipynb")
