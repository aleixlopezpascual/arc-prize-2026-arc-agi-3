import json
from pathlib import Path

# 1. Update apply_enhancements_v15.py
v15_enh_path = Path("submissions/duck_v15/apply_enhancements_v15.py")
enh_src = v15_enh_path.read_text()

v15_additions = """
# ---------------------------------------------------------------------------
# 6. Repair animation.py: empty animation schema with steps and frames
# ---------------------------------------------------------------------------
anim_file = src_root / "ARC3-Inference/inference/utils/animation.py"
if anim_file.exists():
    anim_text = anim_file.read_text(encoding="utf-8")
    old_empty = '''    empty = {
        "error": (
            "No animation is available: the last executed action returned a single frame."
        )
    }'''
    new_empty = '''    empty = {
        "action": record.get("action_display") if record else None,
        "frames": 0,
        "steps": [],
        "error": (
            "No animation is available: the last executed action returned a single frame."
        ),
    }'''
    if old_empty in anim_text:
        anim_text = anim_text.replace(old_empty, new_empty, 1)
        anim_file.write_text(anim_text, encoding="utf-8")
        print("Successfully repaired animation.py empty schema")

# ---------------------------------------------------------------------------
# 7. Update solver.py: batch action early stoppage on zero gameplay change
# ---------------------------------------------------------------------------
solver_file = src_root / "ARC3-Inference/inference/framework/solver.py"
if solver_file.exists():
    solver_text = solver_file.read_text(encoding="utf-8")
    old_block = '''            if (
                BATCH_NOOP_BLOCK
                and NOOP_GUARD_BORDER_WIDTH > 0
                and batch_size >= 2
                and not payload.get("gameplay_changed", True)
            ):
                stop_reason = "no_op_action"
                break'''
    new_block = '''            if (
                batch_size >= 2
                and (
                    not payload.get("gameplay_changed", True)
                    or not payload.get("board_changed", True)
                )
            ):
                stop_reason = "no_op_action"
                break'''
    if old_block in solver_text:
        solver_text = solver_text.replace(old_block, new_block, 1)
        solver_file.write_text(solver_text, encoding="utf-8")
        print("Successfully patched solver.py batch early stoppage")

# ---------------------------------------------------------------------------
# 8. Update runtime_state.py: add stagnation_alert to FrameView
# ---------------------------------------------------------------------------
rs_file = src_root / "ARC3-Inference/inference/agent/runtime_state.py"
if rs_file.exists():
    rs_text = rs_file.read_text(encoding="utf-8")
    if "stagnation_alert: str | None = None" not in rs_text:
        rs_text = rs_text.replace(
            "level_baseline: int | None = None",
            "level_baseline: int | None = None\\n    stagnation_alert: str | None = None",
            1,
        )
        rs_file.write_text(rs_text, encoding="utf-8")
        print("Successfully updated runtime_state.py with stagnation_alert")
"""

if "Repair animation.py" not in enh_src:
  enh_src += v15_additions
  v15_enh_path.write_text(enh_src)
  print("Updated submissions/duck_v15/apply_enhancements_v15.py")

# 2. Assemble notebook.ipynb from duck_v12 (our pristine, record baseline)
v12_nb = json.loads(Path("submissions/duck_v12/notebook.ipynb").read_text())

# Cell 0: title Duck V15
v12_nb["cells"][0]["source"] = [
    l.replace("Duck V12", "Duck V15") for l in v12_nb["cells"][0]["source"]
]

# Cell 3: write apply_enhancements_v15.py
v15_script = v15_enh_path.read_text()
v12_nb["cells"][3]["source"] = [
    "%%writefile /kaggle/apply_enhancements_v15.py\n"
] + [l + "\n" for l in v15_script.splitlines()[:-1]] + [
    v15_script.splitlines()[-1]
]

# Cell 5: execute apply_enhancements_v15.py
v12_nb["cells"][5]["source"] = [
    l.replace("apply_enhancements_v12.py", "apply_enhancements_v15.py")
    for l in v12_nb["cells"][5]["source"]
]

Path("submissions/duck_v15/notebook.ipynb").write_text(
    json.dumps(v12_nb, indent=1)
)
print("Successfully generated submissions/duck_v15/notebook.ipynb")
