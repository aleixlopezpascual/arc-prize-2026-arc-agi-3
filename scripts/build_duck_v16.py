import json
from pathlib import Path

# 1. Update apply_enhancements_v16.py
v16_enh_path = Path("submissions/duck_v16/apply_enhancements_v16.py")
enh_src = v16_enh_path.read_text()

# Update prompts addition in apply_enhancements_v16.py
old_prompt_line = (
    "    \"- `candidate_clicks(color=None, min_size=1, max_size=None,"
    " exclude_border=True)` returns candidate click targets with their"
    " `centroid` [row, col], `bbox`, and `color`.\\n\""
)
new_prompt_line = (
    "    \"- `candidate_clicks(color=None, min_size=1, max_size=None,"
    " exclude_border=True)` returns candidate click targets with their"
    " `centroid` [row, col], `bbox`, and `color`.\\n\"\n    \"-"
    " `candidate_goals(exclude_border=True, max_candidates=8)` returns"
    " candidate destination targets, sockets, and landmarks with their"
    " `centroid` [row, col] and `goal_score`.\\n\""
)

if old_prompt_line in enh_src and new_prompt_line not in enh_src:
  enh_src = enh_src.replace(old_prompt_line, new_prompt_line, 1)

# In Step 3, define candidate_goals and expose in runtime_globals
goals_def = """    def candidate_goals(exclude_border=True, max_candidates=8, frame=None):
        from collections import Counter
        target = frame if frame is not None else runtime_globals.get("current_frame")
        if target is None:
            return []
        seg = getattr(target, "segmentation", None)
        if not seg or not isinstance(seg, dict):
            return []
        nodes = seg.get("nodes") or []
        valid_nodes = []
        color_counts = Counter()
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if exclude_border and node.get("is_border", False):
                continue
            c = node.get("color")
            color_counts[c] += 1
            valid_nodes.append(node)
        if not valid_nodes:
            return []
        scored = []
        for node in valid_nodes:
            c = node.get("color")
            pixels = int(node.get("pixels", 0))
            freq = color_counts[c]
            score = 0.0
            if freq == 1:
                score += 50.0
            elif freq == 2:
                score += 30.0
            elif freq <= 4:
                score += 15.0
            if 1 <= pixels <= 4:
                score += 30.0 - (pixels * 3.0)
            elif pixels <= 9:
                score += 10.0
            centroid = node.get("centroid")
            bbox = node.get("bbox")
            scored.append({
                "id": node.get("id"),
                "color": c,
                "centroid": list(centroid) if centroid else None,
                "bbox": list(bbox) if bbox else None,
                "pixels": pixels,
                "goal_score": round(score, 1),
            })
        scored.sort(key=lambda item: item["goal_score"], reverse=True)
        return scored[:max_candidates]
"""

old_globals_line = 'runtime_globals["candidate_clicks"] = candidate_clicks'
new_globals_line = (
    'runtime_globals["candidate_clicks"] = candidate_clicks\n           '
    ' runtime_globals["candidate_goals"] = candidate_goals'
)

if "def candidate_goals" not in enh_src:
  # Insert candidate_goals def right before candidate_clicks def
  enh_src = enh_src.replace(
      "    def candidate_clicks(", goals_def + "\n    def candidate_clicks(", 1
  )
  enh_src = enh_src.replace(old_globals_line, new_globals_line, 1)

v16_enh_path.write_text(enh_src)
print("Updated submissions/duck_v16/apply_enhancements_v16.py")

# 2. Assemble notebook.ipynb from duck_v15
v15_nb = json.loads(Path("submissions/duck_v15/notebook.ipynb").read_text())

# Cell 0: title Duck V16
v15_nb["cells"][0]["source"] = [
    l.replace("Duck V15", "Duck V16") for l in v15_nb["cells"][0]["source"]
]

# Cell 3: write apply_enhancements_v16.py
v16_script = v16_enh_path.read_text()
v15_nb["cells"][3]["source"] = [
    "%%writefile /kaggle/apply_enhancements_v16.py\n"
] + [l + "\n" for l in v16_script.splitlines()[:-1]] + [
    v16_script.splitlines()[-1]
]

# Cell 5: execute apply_enhancements_v16.py
v15_nb["cells"][5]["source"] = [
    l.replace("apply_enhancements_v15.py", "apply_enhancements_v16.py")
    for l in v15_nb["cells"][5]["source"]
]

Path("submissions/duck_v16/notebook.ipynb").write_text(
    json.dumps(v15_nb, indent=1)
)
print("Successfully generated submissions/duck_v16/notebook.ipynb")
