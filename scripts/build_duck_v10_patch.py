"""Generator script for submissions/duck_v10/apply_enhancements_v10.py."""
from pathlib import Path

v9_src = Path("submissions/duck_v9/apply_enhancements_v9.py").read_text(encoding="utf-8")

# 1. Update FrameView in python_tool_sandbox.py
old_frame = '''        fv.solved_memory = list(payload.get("solved_memory") or [])
        return fv'''

new_frame = '''        fv.solved_memory = list(payload.get("solved_memory") or [])
        fv.level_baseline = payload.get("level_baseline")
        return fv'''

assert old_frame in v9_src, "Failed to find old_frame in v9_src"
v10_src = v9_src.replace(old_frame, new_frame, 1)

# 2. In python_tool_sandbox.py _refresh_state
old_refresh = 'runtime_globals["solved_memory"] = list(state_payload.get("solved_memory") or [])'
new_refresh = '''runtime_globals["solved_memory"] = list(state_payload.get("solved_memory") or [])
            runtime_globals["level_baseline"] = current_frame.level_baseline if current_frame else None'''

assert old_refresh in v10_src, "Failed to find old_refresh in v10_src"
v10_src = v10_src.replace(old_refresh, new_refresh, 1)

# 3. In prompts.py
old_prompt_add = '    "- `current_frame.solved_memory` (also available as `solved_memory`) is a list of summaries from completed levels in this game: `[{\'level\': ..., \'actions_taken\': ..., \'winning_actions\': [...]}, ...]`. Core object mechanics and action patterns from earlier levels often carry forward.\\\\n"'
new_prompt_add = '''    "- `current_frame.solved_memory` (also available as `solved_memory`) is a list of summaries from completed levels in this game: `[{\'level\': ..., \'actions_taken\': ..., \'winning_actions\': [...]}, ...]`. Core object mechanics and action patterns from earlier levels often carry forward.\\\\n"
    "- `current_frame.level_baseline` (also available as `level_baseline`): human reference action count for this level (when available).\\\\n"'''

assert old_prompt_add in v10_src, "Failed to find old_prompt_add in v10_src"
v10_src = v10_src.replace(old_prompt_add, new_prompt_add, 1)

# 4. In tool_agent.py
old_agent_state = '''            if current_frame_payload is not None:
                current_frame_payload["solved_memory"] = list(getattr(self, "_cleared_level_memories", []))'''

new_agent_state = '''            if current_frame_payload is not None:
                current_frame_payload["solved_memory"] = list(getattr(self, "_cleared_level_memories", []))
                current_frame_payload["level_baseline"] = getattr(self, "_current_level_baseline", None)'''

assert old_agent_state in v10_src, "Failed to find old_agent_state in v10_src"
v10_src = v10_src.replace(old_agent_state, new_agent_state, 1)

Path("submissions/duck_v10/apply_enhancements_v10.py").write_text(v10_src, encoding="utf-8")
print("Successfully generated submissions/duck_v10/apply_enhancements_v10.py")
