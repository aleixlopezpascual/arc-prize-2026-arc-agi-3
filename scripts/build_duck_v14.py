import json
from pathlib import Path

pre_explorer_code = Path("src/perception/pre_explorer.py").read_text()
manual_injector_code = Path("src/perception/manual_injector.py").read_text()

# 1. Update apply_enhancements_v14.py
v14_enh_path = Path("submissions/duck_v14/apply_enhancements_v14.py")
enh_src = v14_enh_path.read_text()

append_code = f"""
# ---------------------------------------------------------------------------
# 6. Write pre_explorer.py and manual_injector.py
# ---------------------------------------------------------------------------
PRE_EXPLORER_SRC = {repr(pre_explorer_code)}
MANUAL_INJECTOR_SRC = {repr(manual_injector_code)}

for out_dir in [src_root, Path('/kaggle'), Path('.')]:
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / 'pre_explorer.py').write_text(PRE_EXPLORER_SRC, encoding='utf-8')
        (out_dir / 'manual_injector.py').write_text(MANUAL_INJECTOR_SRC, encoding='utf-8')
    except Exception:
        pass
print('Successfully wrote pre_explorer.py and manual_injector.py')
"""

if "Write pre_explorer.py" not in enh_src:
    enh_src += append_code
    v14_enh_path.write_text(enh_src)
    print("Updated submissions/duck_v14/apply_enhancements_v14.py")

# 2. Update notebook.ipynb
v13_nb = json.loads(Path("submissions/duck_v13/notebook.ipynb").read_text())

# Cell 0: title
v13_nb["cells"][0]["source"] = [
    l.replace("Duck V13", "Duck V14") for l in v13_nb["cells"][0]["source"]
]

# Cell 3: apply_enhancements_v14.py
v14_script = v14_enh_path.read_text()
v13_nb["cells"][3]["source"] = [
    "%%writefile /kaggle/apply_enhancements_v14.py\n"
] + [l + "\n" for l in v14_script.splitlines()[:-1]] + [
    v14_script.splitlines()[-1]
]

# Cell 5: execution
v13_nb["cells"][5]["source"] = [
    l.replace("apply_enhancements_v13.py", "apply_enhancements_v14.py")
    for l in v13_nb["cells"][5]["source"]
]

# Cell 21: add Pre-Exploration before await bm.run
cell21_src = "".join(v13_nb["cells"][21]["source"])
pre_explore_hook = """
# --- Duck V14 Phase A: Fast CPU Pre-Exploration ---
import os, time
import pre_explorer
import manual_injector

_v14_manuals = {}
if os.getenv("ENABLE_PRE_EXPLORATION", "1") == "1":
    try:
        from arcengine import GameAction as _V14_GameAction
        _v14_ids = [g.env_name for g in bm.games]
        def _v14_make(gid):
            match = next((g for g in bm.games if g.env_name == gid), None)
            if match and hasattr(match, "_arcade"):
                return match._arcade.make(gid)
            return None

        _v14_budget = float(os.getenv("PRE_EXPLORATION_SECONDS_PER_GAME", "45"))
        print(f"[Duck-V14-PhaseA] Starting CPU pre-exploration on {len(_v14_ids)} games...", flush=True)
        _t0 = time.monotonic()
        _v14_manuals = pre_explorer.run_pre_exploration(
            _v14_ids,
            _v14_make,
            _V14_GameAction,
            seconds_per_game=_v14_budget,
            seed=0,
            max_chars=int(os.getenv("MANUAL_MAX_CHARS", "2500")),
        )
        print(f"[Duck-V14-PhaseA] Completed in {time.monotonic() - _t0:.1f}s: {len(_v14_manuals)}/{len(_v14_ids)} manuals generated.", flush=True)
    except Exception as exc:
        print(f"[Duck-V14-PhaseA] Warning: pre-exploration degraded to pristine: {exc}", flush=True)
        _v14_manuals = {}

# --- Duck V14 Phase B: System Prompt Manual Injection ---
if _v14_manuals:
    manual_injector.install(_v14_manuals)

"""

run_call = "await bm.run(soft_end_time=soft_end, runtime_environment=target, minimal_diagnostics=TRUE_SUBMISSION)"
assert run_call in cell21_src, "await bm.run not in cell 21"
cell21_src = cell21_src.replace(run_call, pre_explore_hook + "\n" + run_call, 1)
v13_nb["cells"][21]["source"] = [
    l + "\n" for l in cell21_src.splitlines()[:-1]
] + [cell21_src.splitlines()[-1]]

Path("submissions/duck_v14/notebook.ipynb").write_text(
    json.dumps(v13_nb, indent=1)
)
print("Successfully generated submissions/duck_v14/notebook.ipynb")
