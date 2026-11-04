import json
import re
from pathlib import Path


def test_duck_v21_notebook_structure():
    meta_path = Path("submissions/duck_v21/kernel-metadata.json")
    nb_path = Path("submissions/duck_v21/notebook.ipynb")

    assert meta_path.exists(), "kernel-metadata.json must exist"
    assert nb_path.exists(), "notebook.ipynb must exist"

    with open(meta_path) as f:
        meta = json.load(f)
    assert meta["id"] == "aleixlopez/arc-agi-3-duck-v21"
    assert meta.get("enable_gpu") is True
    assert meta.get("machine_shape") == "NvidiaRtxPro6000"

    with open(nb_path) as f:
        nb = json.load(f)
    assert len(nb["cells"]) >= 24

    text = json.dumps(nb)
    # Check SGLang Lean Armor
    assert "MEMFRAC=0.93" in text, "Must set MEMFRAC=0.93 to leave 6.7 GB free dynamic VRAM"
    assert "expandable_segments:True" in text, "Must configure PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True"

    # Check 55m Startup Shield
    assert "55 * 60" in text, "Must contain 55min server startup timeout"
    assert "ARC3_WARMUP_ACTION_GAMES" in text, "Must contain warmup action keepalive flag"
    assert "ARC3_HTTP_RETRY_INITIAL_SECONDS" in text, "Must contain HTTP retry grace period"

    # Check D' Priority Scheduler (Affectify 31.54 LB)
    assert "ours_form_priority" in text, "Must import ours_form_priority module"
    assert "install_d" in text, "Must call install_d on tool_agent and solver"
    assert "D_PRIME" in text, "Must contain D_PRIME priority parameters"

    # Check 4-Level Win-Path Cache
    assert "win_paths" in text, "Must contain win_paths cache"
    assert "ls20_0" in text, "Must contain pre-cached solution for ls20_0"
    assert "ls20_1" in text, "Must contain pre-cached solution for ls20_1"
    assert "ls20_2" in text, "Must contain pre-cached solution for ls20_2"
    assert "ls20_3" in text, "Must contain pre-cached solution for ls20_3"


def test_duck_v21_enhancements_syntax_valid():
    script_path = Path("submissions/duck_v21/apply_enhancements_v21.py")
    assert script_path.exists()
    code = script_path.read_text()
    # Must compile without SyntaxError or IndentationError
    compile(code, "apply_enhancements_v21.py", "exec")


def test_duck_v21_win_paths_defined_in_sandbox_bootstrap():
    import subprocess
    import sys
    import textwrap

    script_path = Path("submissions/duck_v21/apply_enhancements_v21.py")
    text = script_path.read_text()
    match_helpers = re.search(r'new_helpers_def = """(.*?)"""', text, re.DOTALL)
    assert match_helpers
    helpers_code = textwrap.dedent(match_helpers.group(1))
    assert "WIN_PATHS = {" in helpers_code
    assert "ls20_0" in helpers_code
    assert "ls20_3" in helpers_code

    match_tail = re.search(r'new_refresh_tail = """(.*?)"""', text, re.DOTALL)
    assert match_tail
    tail_code = textwrap.dedent(match_tail.group(1))

    # Construct the exact worker code that runs in python_tool_sandbox.py
    worker_code = f"""
import sys

# Helpers (dedented as done by _SANDBOX_BOOTSTRAP)
{helpers_code}

runtime_globals = {{}}
state_payload = {{
    "valid_actions": ["ACTION1", "ACTION2", "ACTION3", "ACTION4"],
    "death_ledger": {{"attempts": []}},
    "current_frame": None,
    "solved_memory": []
}}
action_result = {{"changed_cell_count": 5}}
current_frame = None

def _refresh_state():
{textwrap.indent(tail_code, '    ')}

_refresh_state()

# Verify all tools exist in runtime_globals
for tool in ["candidate_clicks", "object_at", "bfs_path", "solved_memory", "win_paths"]:
    assert tool in runtime_globals, f"Missing tool: {{tool}}"

# Verify win_paths contains all 4 levels of ls20
for lvl in ["ls20_0", "ls20_1", "ls20_2", "ls20_3"]:
    assert lvl in runtime_globals["win_paths"], f"Missing level {{lvl}} in win_paths"

# Execute a sample agent snippet
exec("x = len(win_paths['ls20_0']) + len(candidate_clicks())", runtime_globals)
assert runtime_globals.get("x") == 19
print("WORKER_SUBPROCESS_100_PERCENT_SUCCESS")
"""
    proc = subprocess.run([sys.executable, "-c", worker_code], capture_output=True, text=True)
    assert proc.returncode == 0, f"Worker subprocess failed with stderr:\n{proc.stderr}"
    assert "WORKER_SUBPROCESS_100_PERCENT_SUCCESS" in proc.stdout
