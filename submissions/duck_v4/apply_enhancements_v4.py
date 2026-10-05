import sys
from pathlib import Path

src_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")

# ---------------------------------------------------------------------------
# 1. Update segmentation.py: bbox, centroid, and is_border
# ---------------------------------------------------------------------------
seg_file = src_root / "ARC3-Inference/inference/utils/segmentation.py"
seg_text = seg_file.read_text(encoding="utf-8")

if '"is_border": is_border' not in seg_text:
    v4_nodes_append = """        cells = comp["cells"]
        min_r = min(r for r, _ in cells)
        max_r = max(r for r, _ in cells)
        min_c = min(c for _, c in cells)
        max_c = max(c for _, c in cells)
        r_c = round(sum(r for r, _ in cells) / len(cells))
        c_c = round(sum(c for _, c in cells) / len(cells))
        H, W = len(layer), len(layer[0]) if layer else 0
        is_border = bool(
            H > 0 and W > 0 and (
                (min_r == 0 and max_r == 0 and len(cells) >= W * 0.75) or
                (min_r == H - 1 and max_r == H - 1 and len(cells) >= W * 0.75) or
                (min_c == 0 and max_c == 0 and len(cells) >= H * 0.75) or
                (min_c == W - 1 and max_c == W - 1 and len(cells) >= H * 0.75)
            )
        )
        nodes.append(
            {
                "id": cid,
                "color": color,
                "hash": signature[0],
                "rotation": signature[1],
                "rotational_symmetry": signature[2],
                "pose_hash": signature[3],
                "shape_hash": signature[4],
                "pixels": len(comp["cells"]),
                "bbox": [min_r, min_c, max_r, max_c],
                "centroid": [r_c, c_c],
                "is_border": is_border,
                "boundary": [[r, c] for r, c in boundary],
                "children": children[cid],
            }
        )"""

    old_seg_centroid = """        cells = comp["cells"]
        min_r = min(r for r, _ in cells)
        max_r = max(r for r, _ in cells)
        min_c = min(c for _, c in cells)
        max_c = max(c for _, c in cells)
        r_c = round(sum(r for r, _ in cells) / len(cells))
        c_c = round(sum(c for _, c in cells) / len(cells))
        nodes.append(
            {
                "id": cid,
                "color": color,
                "hash": signature[0],
                "rotation": signature[1],
                "rotational_symmetry": signature[2],
                "pose_hash": signature[3],
                "shape_hash": signature[4],
                "pixels": len(comp["cells"]),
                "bbox": [min_r, min_c, max_r, max_c],
                "centroid": [r_c, c_c],
                "boundary": [[r, c] for r, c in boundary],
                "children": children[cid],
            }
        )"""

    old_seg_pristine = """        nodes.append(
            {
                "id": cid,
                "color": color,
                "hash": signature[0],
                "rotation": signature[1],
                "rotational_symmetry": signature[2],
                "pose_hash": signature[3],
                "shape_hash": signature[4],
                "pixels": len(comp["cells"]),
                "boundary": [[r, c] for r, c in boundary],
                "children": children[cid],
            }
        )"""

    if old_seg_centroid in seg_text:
        seg_text = seg_text.replace(old_seg_centroid, v4_nodes_append, 1)
    elif old_seg_pristine in seg_text:
        seg_text = seg_text.replace(old_seg_pristine, v4_nodes_append, 1)
    else:
        raise ValueError("Failed to match nodes.append target in segmentation.py")

    seg_file.write_text(seg_text, encoding="utf-8")
    print("Successfully injected bbox, centroid, and is_border into segmentation.py")
else:
    print("segmentation.py already has is_border")

# ---------------------------------------------------------------------------
# 2. Update prompts.py: Document candidate_clicks, object_at, solved_memory
# ---------------------------------------------------------------------------
prompt_file = src_root / "ARC3-Inference/inference/agent/prompts.py"
prompt_text = prompt_file.read_text(encoding="utf-8")

if "candidate_clicks" not in prompt_text:
    old_fields_centroid = """`pixels` (cell count), `bbox` ([min_row, min_col, max_row, max_col]), `centroid` (geometric center [row, col] for targeting clicks), `boundary`"""
    old_fields_pristine = """`pixels` (cell count), `boundary`"""
    new_fields = """`pixels` (cell count), `bbox` ([min_row, min_col, max_row, max_col]), `centroid` (geometric center [row, col] for targeting clicks), `is_border` (True if outer boundary/HUD bar), `boundary`"""

    if old_fields_centroid in prompt_text:
        prompt_text = prompt_text.replace(old_fields_centroid, new_fields, 1)
    elif old_fields_pristine in prompt_text:
        prompt_text = prompt_text.replace(old_fields_pristine, new_fields, 1)

    old_addendum_anchor = '    "- `frame_diff(before=None, after=None)` compares two frames. Omitted arguments default to `previous_frame` and `current_frame`, respectively.\\n"'
    new_addendum_block = '''    "- `candidate_clicks(color=None, min_size=1, max_size=None, exclude_border=True)` returns candidate click targets with their `centroid` [row, col], `bbox`, and `color`.\\n"
    "- `object_at(row, col)` returns the segmented object node covering cell `(row, col)`, or `None`.\\n"
    "- `current_frame.solved_memory` (also available as `solved_memory`) is a list of summaries from completed levels in this game: `[{'level': ..., 'actions_taken': ..., 'winning_actions': [...]}, ...]`. Core object mechanics and action patterns from earlier levels often carry forward.\\n"
    "- `frame_diff(before=None, after=None)` compares two frames. Omitted arguments default to `previous_frame` and `current_frame`, respectively.\\n"'''

    assert old_addendum_anchor in prompt_text, "Failed to find frame_diff anchor in prompts.py"
    prompt_text = prompt_text.replace(old_addendum_anchor, new_addendum_block, 1)

    prompt_file.write_text(prompt_text, encoding="utf-8")
    print("Successfully documented candidate_clicks, object_at, and solved_memory in prompts.py")
else:
    print("prompts.py already documented candidate_clicks")

# ---------------------------------------------------------------------------
# 3. Update python_tool_sandbox.py: inject candidate_clicks, object_at, solved_memory
# ---------------------------------------------------------------------------
sandbox_file = src_root / "ARC3-Inference/inference/agent/python_tool_sandbox.py"
sandbox_text = sandbox_file.read_text(encoding="utf-8")

if "def candidate_clicks" not in sandbox_text:
    old_frame_from_payload = """    def _frame_from_payload(payload):
        if not isinstance(payload, dict):
            return None
        return FrameView(
            ascii=str(payload.get("ascii", "")),
            step=int(payload.get("step", 0)),
            level=int(payload.get("level", 0)),
            shape=payload.get("shape", [0, 0]),
            grid=payload.get("grid", []),
        )"""

    new_frame_from_payload = """    def candidate_clicks(color=None, min_size=1, max_size=None, exclude_border=True, frame=None):
        target = frame if frame is not None else runtime_globals.get("current_frame")
        if target is None:
            return []
        seg = getattr(target, "segmentation", None)
        if not seg or not isinstance(seg, dict):
            return []
        nodes = seg.get("nodes") or []
        res = []
        for n in nodes:
            if not isinstance(n, dict):
                continue
            if exclude_border and n.get("is_border", False):
                continue
            if color is not None and n.get("color") != color:
                continue
            px = int(n.get("pixels", 0))
            if px < min_size:
                continue
            if max_size is not None and px > max_size:
                continue
            c = n.get("centroid")
            b = n.get("bbox")
            res.append({
                "id": n.get("id"),
                "color": n.get("color"),
                "centroid": list(c) if c else None,
                "bbox": list(b) if b else None,
                "pixels": px,
            })
        res.sort(key=lambda item: item["pixels"], reverse=True)
        return res

    def object_at(row, col, frame=None):
        target = frame if frame is not None else runtime_globals.get("current_frame")
        if target is None:
            return None
        seg = getattr(target, "segmentation", None)
        if not seg or not isinstance(seg, dict):
            return None
        nodes = seg.get("nodes") or []
        for n in nodes:
            if not isinstance(n, dict):
                continue
            bbox = n.get("bbox")
            if not bbox or len(bbox) != 4:
                continue
            min_r, min_c, max_r, max_c = bbox
            if min_r <= row <= max_r and min_c <= col <= max_c:
                return dict(n)
        return None

    def _frame_from_payload(payload):
        if not isinstance(payload, dict):
            return None
        fv = FrameView(
            ascii=str(payload.get("ascii", "")),
            step=int(payload.get("step", 0)),
            level=int(payload.get("level", 0)),
            shape=payload.get("shape", [0, 0]),
            grid=payload.get("grid", []),
        )
        fv.solved_memory = list(payload.get("solved_memory") or [])
        return fv"""

    assert old_frame_from_payload in sandbox_text, "Failed to find _frame_from_payload in python_tool_sandbox.py"
    sandbox_text = sandbox_text.replace(old_frame_from_payload, new_frame_from_payload, 1)

    old_refresh_tail = """            runtime_globals["valid_actions"] = [str(item) for item in state_payload.get("valid_actions", [])]
            runtime_globals["death_ledger"] = state_payload.get("death_ledger") or {"attempts": []}
            runtime_globals["last_action_call_result"] = action_result"""

    new_refresh_tail = """            runtime_globals["valid_actions"] = [str(item) for item in state_payload.get("valid_actions", [])]
            runtime_globals["death_ledger"] = state_payload.get("death_ledger") or {"attempts": []}
            runtime_globals["last_action_call_result"] = action_result
            runtime_globals["candidate_clicks"] = candidate_clicks
            runtime_globals["object_at"] = object_at
            runtime_globals["solved_memory"] = list(state_payload.get("solved_memory") or [])"""

    assert old_refresh_tail in sandbox_text, "Failed to find _refresh_state tail in python_tool_sandbox.py"
    sandbox_text = sandbox_text.replace(old_refresh_tail, new_refresh_tail, 1)

    sandbox_file.write_text(sandbox_text, encoding="utf-8")
    print("Successfully injected candidate_clicks, object_at, and solved_memory into python_tool_sandbox.py")
else:
    print("python_tool_sandbox.py already has candidate_clicks")

# ---------------------------------------------------------------------------
# 4. Update tool_agent.py: record level clears and forward into runtime state
# ---------------------------------------------------------------------------
agent_file = src_root / "ARC3-Inference/inference/agent/tool_agent.py"
agent_text = agent_file.read_text(encoding="utf-8")

# Clean up any legacy prompt injection if present
if "Knowledge from cleared levels:" in agent_text:
    old_prompt_mutation = """        if getattr(self, "_cleared_level_memories", None):
            lines.append("Knowledge from cleared levels:")
            for m in self._cleared_level_memories[-3:]:
                acts = ", ".join(m["actions"]) if m.get("actions") else "verified action sequence"
                lines.append(f"- Level {m['level']} cleared! Winning actions: [{acts}]. Core object mechanics carry forward.")"""
    if old_prompt_mutation in agent_text:
        agent_text = agent_text.replace(old_prompt_mutation, "")
        print("Cleaned up legacy prompt injection from tool_agent.py")

if "_cleared_level_memories" not in agent_text:
    old_init = """        self._session_generated_tokens = 0
        self._session_wallclock_seconds = 0.0"""

    new_init = """        self._session_generated_tokens = 0
        self._session_wallclock_seconds = 0.0
        self._cleared_level_memories = []"""

    assert old_init in agent_text, "Failed to find session init in tool_agent.py"
    agent_text = agent_text.replace(old_init, new_init, 1)

    old_ensure = """        if self._state_path != state_path:
            self._state_path = state_path
            self._ensure_prompt_cache()
            self._history_messages = []"""

    new_ensure = """        if self._state_path != state_path:
            self._state_path = state_path
            self._ensure_prompt_cache()
            self._history_messages = []
            self._cleared_level_memories = []"""

    assert old_ensure in agent_text, "Failed to find _ensure_session in tool_agent.py"
    agent_text = agent_text.replace(old_ensure, new_ensure, 1)

    old_update_knowledge = """        if step_executed:
            self._last_step_summary = self._summarize_step_sequence(action_results)
            self._update_summarized_knowledge_from_step_summary()"""

    new_update_knowledge = """        if step_executed:
            self._last_step_summary = self._summarize_step_sequence(action_results)
            self._update_summarized_knowledge_from_step_summary()
            if getattr(self, "_cleared_level_memories", None) is not None and self._last_step_summary and self._last_step_summary.get("level_transition"):
                cleared_lvl = max(1, int(self._last_step_summary.get("level") or 2) - 1)
                acts = self._last_step_summary.get("executed_actions") or []
                self._cleared_level_memories.append({
                    "level": cleared_lvl,
                    "actions_taken": int(self._last_step_summary.get("executed_count", len(acts))),
                    "winning_actions": [str(a) for a in acts[-5:]] if acts else [],
                })"""

    assert old_update_knowledge in agent_text, "Failed to find _update_summarized_knowledge in tool_agent.py"
    agent_text = agent_text.replace(old_update_knowledge, new_update_knowledge, 1)

    old_state_return = """            return {
                "current_frame": current_frame_payload,
                "history": _serialized_history(refreshed_history),
                "valid_actions": sanitized_actions,
                "death_ledger": dict(
                    self._death_ledger_payload()
                    if hasattr(self, "_death_ledger_payload")
                    else {}
                ),
                "last_action_call_result": (
                    dict(persisted_action_result)
                    if isinstance(persisted_action_result, dict)
                    else {}
                ),
            }"""

    new_state_return = """            current_frame_payload["solved_memory"] = list(getattr(self, "_cleared_level_memories", []))
            return {
                "current_frame": current_frame_payload,
                "history": _serialized_history(refreshed_history),
                "valid_actions": sanitized_actions,
                "death_ledger": dict(
                    self._death_ledger_payload()
                    if hasattr(self, "_death_ledger_payload")
                    else {}
                ),
                "last_action_call_result": (
                    dict(persisted_action_result)
                    if isinstance(persisted_action_result, dict)
                    else {}
                ),
                "solved_memory": list(getattr(self, "_cleared_level_memories", [])),
            }"""

    assert old_state_return in agent_text, "Failed to find _serialized_runtime_state return in tool_agent.py"
    agent_text = agent_text.replace(old_state_return, new_state_return, 1)

    agent_file.write_text(agent_text, encoding="utf-8")
    print("Successfully injected solved level tracking into tool_agent.py")
else:
    print("tool_agent.py already tracks _cleared_level_memories")
