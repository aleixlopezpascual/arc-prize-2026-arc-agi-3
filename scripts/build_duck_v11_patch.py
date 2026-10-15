"""Generator script for submissions/duck_v11/apply_enhancements_v11.py."""
from pathlib import Path

v10 = Path("submissions/duck_v10/apply_enhancements_v10.py").read_text(encoding="utf-8")
old_l = '"- `current_frame.level_baseline` (also available as `level_baseline`): human reference action count for this level (when available).\\\\n"'
new_l = '"- `current_frame.level_baseline` (also available as `level_baseline`): human reference action count for this level (when available). Plan direct, efficient routes to conserve actions and maximize efficiency.\\\\n"'

assert old_l in v10, "old_l not found in v10"
v11 = v10.replace(old_l, new_l, 1)
Path("submissions/duck_v11/apply_enhancements_v11.py").write_text(v11, encoding="utf-8")
print("Successfully generated submissions/duck_v11/apply_enhancements_v11.py")
