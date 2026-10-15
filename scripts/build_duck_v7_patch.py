"""Generator script for submissions/duck_v7/apply_enhancements_v7.py."""
from pathlib import Path
import json

fable_core_src = Path("src/perception/fable_core.py").read_text(encoding="utf-8")
v6_src = Path("submissions/duck_v6/apply_enhancements_v6.py").read_text(encoding="utf-8")

# Extract Fable methods from Cell 42
nb = json.load(open("notebooks/public_baselines/fable-astra/fable-astra-play-arc-3-handbook-harness.ipynb"))
c42_lines = "".join(nb["cells"][42]["source"])

start_methods = c42_lines.find("METHODS = r'''") + len("METHODS = r'''")
end_methods = c42_lines.find("'''\n\nEDITS = [", start_methods)
fable_methods = c42_lines[start_methods:end_methods]

section_0 = f'''# ---------------------------------------------------------------------------
# 0. Write fable_layer_core.py
# ---------------------------------------------------------------------------
fable_core_file = src_root / "ARC3-Inference/inference/agent/fable_layer_core.py"
FABLE_CORE_SRC = {repr(fable_core_src)}
fable_core_file.write_text(FABLE_CORE_SRC, encoding="utf-8")
print("Successfully wrote fable_layer_core.py")

'''

# Insert section 0 right before Section 1
idx_sec1 = v6_src.find("# --------------------------------------------------------------------------- \n# 1. Update segmentation.py")
if idx_sec1 == -1:
    idx_sec1 = v6_src.find("# 1. Update segmentation.py")
    idx_sec1 = v6_src.rfind("# ---------------------------------------------------------------------------", 0, idx_sec1)

v7_src = v6_src[:idx_sec1] + section_0 + v6_src[idx_sec1:]

# Now append Fable layer injection to tool_agent.py at the end of the script
fable_tool_agent_injection = f'''
# 5. Inject Fable layer hooks into tool_agent.py
FABLE_METHODS = {repr(fable_methods)}

FABLE_EDITS = [
    (
        "    def _build_user_prompt(\\n        self,\\n        action_num: int,\\n",
        FABLE_METHODS + "    def _build_user_prompt(\\n        self,\\n        action_num: int,\\n",
    ),
    (
        "                f\\"Valid actions right now: {{_format_valid_action_line(valid_actions)}}.\\",\\n            ]\\n        )\\n",
        "                f\\"Valid actions right now: {{_format_valid_action_line(valid_actions)}}.\\",\\n            ]\\n        )\\n"
        "        lines.extend(self._fl_opener_lines(current_frame, history_entries))\\n",
    ),
    (
        "            self._actions_at_level_start = _priority_action_count(summary)\\n"
        "            self._tokens_at_level_start = self._session_generated_tokens\\n",
        "            self._actions_at_level_start = _priority_action_count(summary)\\n"
        "            self._tokens_at_level_start = self._session_generated_tokens\\n"
        "            self._fl_forget_pin()\\n",
    ),
    (
        "        preserve_history = True\\n        resuming_after_yield = bool(getattr(self, \\\"_resume_after_yield\\\", False))\\n",
        "        self._fl_maybe_pin(current_frame, history_entries)\\n"
        "        preserve_history = True\\n        resuming_after_yield = bool(getattr(self, \\\"_resume_after_yield\\\", False))\\n",
    ),
    (
        "        if len(history) != len(messages) - 1:\\n"
        "            self._note_history_evicted()\\n"
        "        return [system_message, *history]\\n",
        "        if len(history) != len(messages) - 1:\\n"
        "            self._note_history_evicted()\\n"
        "        history = self._fl_restore_pinned(history)\\n"
        "        return [system_message, *history]\\n",
    ),
]

if "ARC3_FABLE_LAYER" not in agent_text:
    for old, new in FABLE_EDITS:
        assert agent_text.count(old) == 1, f"Failed to match anchor: {{old[:50]}}"
        agent_text = agent_text.replace(old, new, 1)
    agent_file.write_text(agent_text, encoding="utf-8")
    print("Successfully injected Fable layer into tool_agent.py")
else:
    print("tool_agent.py already has Fable layer")
'''

v7_src = v7_src + fable_tool_agent_injection

Path("submissions/duck_v7/apply_enhancements_v7.py").write_text(v7_src, encoding="utf-8")
print("Successfully generated submissions/duck_v7/apply_enhancements_v7.py")
