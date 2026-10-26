#!/usr/bin/env python3
"""Build Duck V18 (Lean Armor) submission package.

Combines:
1. Duck V12 peak engine (58.42% demo record benchmark, 29.46% LB)
2. 55-minute Kaggle startup shield + warmup keepalive + 900s HTTP retry grace (from V17)
3. Zero premature batch early stopping (uninterrupted multi-step execution)
4. Concise prompt for maximum SGLang KV cache reuse (>93%)
5. Candidate goals & candidate clicks perception primitives
"""
import json
import shutil
from pathlib import Path

V12_DIR = Path("submissions/duck_v12")
V17_DIR = Path("submissions/duck_v17")
V18_DIR = Path("submissions/duck_v18")
V18_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Create kernel-metadata.json
# ---------------------------------------------------------------------------
metadata = {
    "id": "aleixlopez/arc-agi-3-duck-v18",
    "title": "ARC-AGI-3 Duck V18",
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
(V18_DIR / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2))
print("Wrote submissions/duck_v18/kernel-metadata.json")

# ---------------------------------------------------------------------------
# 2. Build apply_enhancements_v18.py based on Duck V12
# ---------------------------------------------------------------------------
v12_script = (V12_DIR / "apply_enhancements_v12.py").read_text()

# Inject candidate_goals helper alongside candidate_clicks in python_tool_sandbox.py
candidate_goals_func = '''
    def candidate_goals(exclude_border=True, max_candidates=8):
        nodes = runtime_globals.get("candidate_clicks")(min_size=1, exclude_border=exclude_border)
        if not nodes:
            return []
        scores = []
        for n in nodes:
            c = n.get("color")
            p = n.get("pixels", 0)
            score = 0.0
            if p == 1:
                score += 35.0
            elif p <= 4:
                score += 20.0
            if c not in (0, 4):  # not background/floor
                score += 15.0
            n_copy = dict(n)
            n_copy["goal_score"] = score
            scores.append(n_copy)
        scores.sort(key=lambda x: x["goal_score"], reverse=True)
        return scores[:max_candidates]
'''

v18_script = v12_script
if "def candidate_goals" not in v18_script:
    # Add candidate_goals into python_tool_sandbox.py
    v18_script = v18_script.replace(
        '            runtime_globals["candidate_clicks"] = candidate_clicks\n',
        candidate_goals_func + '\n            runtime_globals["candidate_clicks"] = candidate_clicks\n            runtime_globals["candidate_goals"] = candidate_goals\n'
    )
    # Add to prompts.py
    v18_script = v18_script.replace(
        '    "- `candidate_clicks(color=None, min_size=1, max_size=None, exclude_border=True)` returns candidate click targets with their `centroid` [row, col], `bbox`, and `color`.\\n"\n',
        '    "- `candidate_clicks(color=None, min_size=1, max_size=None, exclude_border=True)` returns candidate click targets with their `centroid` [row, col], `bbox`, and `color`.\\n"\n'
        '    "- `candidate_goals(exclude_border=True, max_candidates=8)` returns candidate destination targets, sockets, and landmarks with their `centroid` [row, col] and `goal_score`.\\n"\n'
    )

(V18_DIR / "apply_enhancements_v18.py").write_text(v18_script)
print("Wrote submissions/duck_v18/apply_enhancements_v18.py")

# ---------------------------------------------------------------------------
# 3. Assemble submissions/duck_v18/notebook.ipynb from Duck V12 base with V17 armor
# ---------------------------------------------------------------------------
v12_nb = json.loads((V12_DIR / "notebook.ipynb").read_text())

# Cell 0: Title Duck V18
v12_nb["cells"][0]["source"] = [
    l.replace("Duck V12", "Duck V18 (Lean Armor + 55min Startup Shield + V12 Core + Unrestricted Execution)")
    for l in v12_nb["cells"][0]["source"]
]

# Cell 3: %%writefile /kaggle/apply_enhancements_v18.py
v18_body = (V18_DIR / "apply_enhancements_v18.py").read_text()
v12_nb["cells"][3]["source"] = [
    "%%writefile /kaggle/apply_enhancements_v18.py\n"
] + [l + "\n" for l in v18_body.splitlines()[:-1]] + [
    v18_body.splitlines()[-1]
]

# Cell 5: Setup timeout armor (55 * 60) & run apply_enhancements_v18.py
cell5_src = "".join(v12_nb["cells"][5]["source"])
cell5_src = cell5_src.replace("SERVER_STARTUP_TIMEOUT = 12 * 60", "SERVER_STARTUP_TIMEOUT = 55 * 60")
cell5_src = cell5_src.replace("apply_enhancements_v12.py", "apply_enhancements_v18.py")

# Ensure environment flags for armor are set in cell 5
if "ARC3_WARMUP_ACTION_GAMES" not in cell5_src:
    cell5_src = "import os\nos.environ['ARC3_WARMUP_ACTION_GAMES'] = '1'\nos.environ['ARC3_HTTP_RETRY_INITIAL_SECONDS'] = '900'\n" + cell5_src

v12_nb["cells"][5]["source"] = [l + "\n" for l in cell5_src.splitlines()[:-1]] + [cell5_src.splitlines()[-1]]

(V18_DIR / "notebook.ipynb").write_text(json.dumps(v12_nb, indent=1))
print("Successfully generated submissions/duck_v18/notebook.ipynb")
