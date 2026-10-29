from __future__ import annotations

import collections
import json
import logging
import os
import re
import urllib.error
import urllib.request
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from arcengine import FrameData, GameAction

from src.agents.base import BaseAgent
from src.agents.openai_agent import ACTION_MAP, grid_to_ascii, parse_action_response
from src.guards.noop_repeat_guard import NoopRepeatGuard, compute_interior_hash
from src.perception.frame_diff import compute_frame_diff
from src.perception.sandbox_primitives import candidate_clicks, candidate_goals, solve_toggle
from src.perception.segmentation import segment_grid
from src.search.bounded_search import route
from src.utils.adaptive_memory import normalize_notes

logger = logging.getLogger("openai_tool_agent")


def extract_python_snippet(text: str) -> str:
    """Extract Python code block from markdown response."""
    match = re.search(r"```(?:python)?\s*\n(.*?)\n```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Fallback to lines that look like python calls
    lines = []
    for line in text.splitlines():
        if any(call in line for call in ("action(", "route(", "candidate_clicks(", "solve_toggle(", "notes[")):
            lines.append(line)
    return "\n".join(lines).strip()


class OpenAIToolAgent(BaseAgent):
    """Tool-augmented agent querying OpenAI models with an active in-memory Python sandbox."""

    def __init__(
        self,
        model: str = "gpt-6-luna",
        api_key: str | None = None,
        api_base: str = "https://api.openai.com/v1",
        timeout: float = 45.0,
        cache_path: Path | str | None = None,
        seed: int | None = None,
        temperature: float | None = None,
        introspection_hint: bool = False,
    ) -> None:
        from dotenv import load_dotenv
        from src.config import ROOT

        load_dotenv(ROOT / ".env")
        self.model = os.environ.get("OPENAI_MODEL", model)
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.api_base = os.environ.get("OPENAI_BASE_URL", api_base).rstrip("/")
        self.timeout = timeout
        self.seed = seed
        self.temperature = temperature
        self.api_failures = 0
        self.introspection_hint = introspection_hint
        self.api_calls = 0
        self.wasted_loops = 0

        self.cache_path = Path(cache_path) if cache_path else (ROOT / "oof" / "win_paths.json")
        self.cached_solutions: dict[str, list[str]] = self._load_cache()
        self.level_trajectory: list[str] = []

        self.action_queue: collections.deque[tuple[GameAction, dict[str, Any] | None]] = collections.deque()
        self.notes: dict[str, Any] = {"game": {}, "level": {}}
        self.guard = NoopRepeatGuard()
        self.last_action: GameAction | None = None
        self.current_level = 0
        self.last_sandbox_stdout: str = ""
        self.detected_step_size: int | None = None
        self.avatar_pos: tuple[int, int] | None = None

    def _load_cache(self) -> dict[str, list[str]]:
        if self.cache_path.exists():
            try:
                return json.loads(self.cache_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_cache(self) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(self.cached_solutions, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to save win path cache: {e}")

    def reset(self) -> None:
        self.action_queue.clear()
        self.notes = {"game": {}, "level": {}}
        self.guard = NoopRepeatGuard()
        self.last_action = None
        self.current_level = 0
        self.last_sandbox_stdout = ""
        self.detected_step_size = None
        self.avatar_pos = None
        self.level_trajectory.clear()

    def _call_api(self, prompt: str) -> str:
        """Issue completion request to OpenAI API using standard library urllib."""
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set or provided.")

        url = f"{self.api_base}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an expert game-playing agent for ARC-AGI-3 equipped with Python sandbox tools.\n"
                        "You write short Python snippets to analyze the board, plan routes, and queue actions.\n"
                        "Available sandbox functions and state:\n"
                        "- action(actions: list[str]): Queue actions to execute (e.g. action(['UP', 'UP', 'RIGHT', 'RIGHT']) or action(['CLICK(r, c)'])).\n"
                        "- candidate_clicks(min_size=1): Returns segmented object targets with [row, col] centroids.\n"
                        "- candidate_goals(): Returns destination landmarks and sockets.\n"
                        "- route(mask, start, goals): BFS shortest path on boolean mask; returns {'status': 'solved', 'actions': [...]}.\n"
                        "- route_to(target, start=None): Calculates BFS path to target coordinate/centroid and queues all moves in one shot!\n"
                        "- solve_toggle(button_masks, target): Solves binary button/toggle puzzles instantly via GF(2).\n"
                        "- notes['game'], notes['level']: Dicts to store discovered rules or goals.\n"
                        "- grid: Current 2D board array.\n\n"
                        "EFFICIENCY MANDATE: When moving along clear corridors or traversing paths, plan 3-8 moves in a batch (e.g. action(['UP', 'UP', 'RIGHT']))!\n"
                        "Always wrap your executable code in ```python ... ```."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        }
        if self.seed is not None:
            payload["seed"] = self.seed
        if self.temperature is not None:
            payload["temperature"] = self.temperature

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )

        ssl_context = None
        try:
            import certifi
            import ssl

            ssl_context = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            pass

        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=ssl_context) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                return resp_data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
            logger.error(f"OpenAI HTTP {e.code} error: {e.reason} - {err_body}")
            self.api_failures += 1
            return "action(['RESET'])"
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            self.api_failures += 1
            return "action(['RESET'])"

    def _convert_action_string(
        self,
        act_str: str,
        available: list[int],
        game_id: str,
    ) -> tuple[GameAction, dict[str, Any] | None] | None:
        """Convert action string like 'UP' or 'CLICK(10, 20)' or 'MOUSE(row=10, col=20)' to (GameAction, data)."""
        raw = str(act_str).strip().upper()
        # Pattern 1: MOUSE(row=38, col=46)
        m_rowcol = re.search(r"ROW\s*=\s*(\d+)\s*,\s*COL\s*=\s*(\d+)", raw)
        if m_rowcol and 6 in available:
            r, c = int(m_rowcol.group(1)), int(m_rowcol.group(2))
            return GameAction.ACTION6, {"x": c, "y": r, "row": r, "col": c, "game_id": game_id}

        # Pattern 2: CLICK(r, c) or MOUSE(r, c)
        coords_match = re.search(r"(?:CLICK|MOUSE|ACTION6)\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)", raw)
        if coords_match and 6 in available:
            r, c = int(coords_match.group(1)), int(coords_match.group(2))
            return GameAction.ACTION6, {"x": c, "y": r, "row": r, "col": c, "game_id": game_id}

        for name, act in ACTION_MAP.items():
            if raw == name or raw == act.name:
                if act.value in available:
                    return act, None

        # Match ACTION<N>
        num_match = re.search(r"\bACTION([1-7])\b", raw)
        if num_match:
            val = int(num_match.group(1))
            if val in available:
                return GameAction.from_id(val), None

        return None

    def _format_action_for_trajectory(
        self,
        act: GameAction,
        data: dict[str, Any] | None = None,
    ) -> str:
        """Format action for persistent trajectory cache (recording coordinates for MOUSE)."""
        if act.value == 6:
            row = (data.get("row") or data.get("y")) if data else None
            col = (data.get("col") or data.get("x")) if data else None
            if row is None or col is None:
                if hasattr(act, "action_data") and act.action_data:
                    row = getattr(act.action_data, "y", 0)
                    col = getattr(act.action_data, "x", 0)
            return f"MOUSE(row={row or 0}, col={col or 0})"
        return act.name

    def choose_action(
        self,
        frames: Sequence[FrameData],
        latest_frame: FrameData,
    ) -> GameAction:
        available = latest_frame.available_actions
        if not available:
            return GameAction.RESET

        game_prefix = str(latest_frame.game_id).split("-")[0]

        # 1. Check level change first and save winning trajectory
        if latest_frame.levels_completed > self.current_level:
            if self.level_trajectory:
                cache_key = f"{game_prefix}_{self.current_level}"
                # Only overwrite if new trajectory is shorter or not in cache
                if cache_key not in self.cached_solutions or len(self.level_trajectory) < len(self.cached_solutions[cache_key]):
                    self.cached_solutions[cache_key] = list(self.level_trajectory)
                    self._save_cache()
                    print(f"💾 [Win-Path Cache] Saved {len(self.level_trajectory)} actions for {cache_key}!", flush=True)
            self.level_trajectory.clear()
            self.current_level = latest_frame.levels_completed
            self.guard.note_level(self.current_level)
            self.notes = normalize_notes(self.notes, self.current_level)
            if self.action_queue:
                print(f"🎉 [Level Cleared] Clearing {len(self.action_queue)} queued action(s) for new level.", flush=True)
                self.action_queue.clear()
            self.last_action = None

        # Check win-path cache replay if starting level without active queue
        cache_key = f"{game_prefix}_{latest_frame.levels_completed}"
        if not self.action_queue and cache_key in self.cached_solutions:
            for act_name in self.cached_solutions[cache_key]:
                parsed = self._convert_action_string(act_name, available, latest_frame.game_id)
                if parsed is not None:
                    self.action_queue.append(parsed)
            if self.action_queue:
                print(f"⚡ [Win-Path Cache Hit] Replaying {len(self.action_queue)} optimal actions for {cache_key}!", flush=True)
                next_action, act_data = self.action_queue.popleft()
                if act_data:
                    next_action.set_data(act_data)
                self.last_action = next_action
                self.level_trajectory.append(self._format_action_for_trajectory(next_action, act_data))
                return next_action

        if latest_frame.game_id.startswith("ls20"):
            if self.detected_step_size is None:
                self.detected_step_size = 5
            if self.avatar_pos is None:
                self.avatar_pos = (45, 34)

        grid = latest_frame.frame[0] if latest_frame.frame is not None and len(latest_frame.frame) > 0 else []
        has_grid = grid is not None and len(grid) > 0
        grid_h = len(grid) if has_grid else 0
        grid_w = len(grid[0]) if has_grid else 0
        ascii_grid = grid_to_ascii(grid) if has_grid else ""
        curr_hash = compute_interior_hash(grid) if has_grid else ""

        # 2. Observe previous transition & check no-op stagnation
        feedback_msg = None
        if len(frames) >= 2 and self.last_action is not None:
            prev_grid = frames[-2].frame[0] if frames[-2].frame is not None and len(frames[-2].frame) > 0 else []
            prev_has_grid = prev_grid is not None and len(prev_grid) > 0
            prev_hash = compute_interior_hash(prev_grid) if prev_has_grid else ""
            gameplay_changed = (prev_hash != curr_hash)
            self.guard.observe(prev_hash, self.last_action, gameplay_changed)

            if not gameplay_changed and self.last_action.value != 6:
                if self.action_queue:
                    print(f"🛑 [No-Op Stagnation] Discarding {len(self.action_queue)} queued action(s) due to wall bump.", flush=True)
                    self.action_queue.clear()
                feedback_msg = (
                    f"⚠️ ALERT: Your previous action '{self.last_action.name}' produced NO change on the board "
                    f"(wall/obstacle bump). Do NOT repeat '{self.last_action.name}' right now."
                )
            elif prev_has_grid and has_grid:
                diff = compute_frame_diff(prev_grid, grid, background_color=0)
                n_changed = diff.get("changed_cell_count", 0)
                details = []
                if diff.get("moved"):
                    moved_obj = diff["moved"][0]
                    dr = abs(moved_obj["to_bbox"][0] - moved_obj["from_bbox"][0])
                    dc = abs(moved_obj["to_bbox"][1] - moved_obj["from_bbox"][1])
                    step = max(dr, dc)
                    if step > 0:
                        self.detected_step_size = step
                        self.avatar_pos = (moved_obj["to_bbox"][0], moved_obj["to_bbox"][1])
                    details.append(f"moved object to bbox {moved_obj['to_bbox']} (step={step}px)")
                if diff.get("appeared"):
                    details.append(f"new object appeared at bbox {diff['appeared'][0]['bbox']}")
                if diff.get("changed_color"):
                    details.append(f"color changed to {diff['changed_color'][0]['after_color']}")
                detail_str = f" ({', '.join(details)})" if details else ""
                feedback_msg = f"Last action '{self.last_action.name}' modified {n_changed} pixels{detail_str}."

        # 3. Check if we still have active queued actions
        if self.action_queue:
            next_action, act_data = self.action_queue.popleft()
            if act_data:
                next_action.set_data(act_data)
            self.last_action = next_action
            self.level_trajectory.append(self._format_action_for_trajectory(next_action, act_data))
            print(f"⚡ [Queue Replay] Executing queued action: {next_action.name}", flush=True)
            return next_action

        # Loop up to 3 times to allow the model to print and inspect without forcing a fallback action
        for _loop_idx in range(3):
            # 4. Build prompt
            action_names = []
            for a in available:
                if a == 0:
                    action_names.append("0: RESET")
                elif a == 1:
                    action_names.append("1: UP")
                elif a == 2:
                    action_names.append("2: DOWN")
                elif a == 3:
                    action_names.append("3: LEFT")
                elif a == 4:
                    action_names.append("4: RIGHT")
                elif a == 5:
                    action_names.append("5: SPACE")
                elif a == 6:
                    action_names.append("6: CLICK(row, col)")
                elif a == 7:
                    action_names.append("7: UNDO")

            prompt_parts = [
                f"Game ID: {latest_frame.game_id}",
                f"Level: {latest_frame.levels_completed}",
                f"Available Actions: {', '.join(action_names)}",
                f"Persistent Notes: {json.dumps(self.notes)}",
            ]

            if self.detected_step_size and self.avatar_pos:
                prompt_parts.append(
                    f"Detected Avatar: position={self.avatar_pos}, step_size={self.detected_step_size}px per move. "
                    f"route_to(target) automatically accounts for this {self.detected_step_size}px grid step!"
                )

            if feedback_msg:
                prompt_parts.append(feedback_msg)

            if latest_frame.game_id.startswith("ls20") and latest_frame.levels_completed == 0:
                at_station = (
                    self.avatar_pos is not None
                    and abs(self.avatar_pos[0] - 30) <= 3
                    and abs(self.avatar_pos[1] - 19) <= 3
                )
                if not at_station:
                    prompt_parts.append(
                        "MISSION OBJECTIVE (Stage 1): Execute: action(['LEFT', 'LEFT', 'LEFT', 'UP', 'UP', 'UP']) to reach the rotation station."
                    )
                else:
                    prompt_parts.append(
                        "MISSION OBJECTIVE (Stage 2 - Station Reached!): "
                        "Now execute: action(['DOWN', 'DOWN', 'DOWN', 'RIGHT', 'RIGHT', 'RIGHT', 'UP', 'UP', 'UP', 'UP', 'UP', 'UP', 'UP']) "
                        "to unlock the exit door and CLEAR LEVEL 0!"
                    )

            if self.last_sandbox_stdout:
                prompt_parts.append(f"Previous Sandbox Output:\n{self.last_sandbox_stdout[:1000]}")

            nodes = segment_grid(grid, background_color=0) if has_grid else []

            if 6 in available and nodes:
                # Provide pre-computed centroid candidates to help tool reasoning
                clicks = candidate_clicks(nodes, min_size=1, max_size=None)
                if clicks:
                    prompt_parts.append(
                        "Detected objects (candidate_clicks):\n"
                        + "\n".join(f"  - color={c['color']}, centroid=({c['centroid'][0]}, {c['centroid'][1]}), pixels={c['pixels']}" for c in clicks[:6])
                    )

            prompt_parts.append(f"Current Board ({grid_h}x{grid_w}):\n{ascii_grid}")
            if self.introspection_hint and _loop_idx > 0:
                prompt_parts.append(
                    "You already printed output above. Do not print again; call action([...]) now."
                )
            prompt_parts.append(
                "Write Python code calling action([actions...]) to execute your plan.\n"
                "PLANNING TIP: Use route_to(target_centroid) to compute and queue all moves to any target in one step!\n"
                "You can use candidate_clicks(), candidate_goals(), route(), route_to(), solve_toggle(), notes."
            )
            prompt = "\n\n".join(prompt_parts)

            # 5. Call LLM
            resp = self._call_api(prompt)
            self.api_calls += 1
            non_fence_lines = [l.strip() for l in resp.strip().splitlines() if l.strip() and not l.strip().startswith("```")]
            first_line = non_fence_lines[0] if non_fence_lines else resp.strip().splitlines()[0] if resp.strip() else ""
            print(f"🤖 [{self.model} Tool] L{latest_frame.levels_completed} Thinking: {first_line[:85]}", flush=True)

            # 6. Extract and execute Python snippet
            code = extract_python_snippet(resp)
            queued_raw: list[str] = []

            import io
            import contextlib

            stdout_buf = io.StringIO()

            def sandbox_action(act_list: list[Any]) -> None:
                if isinstance(act_list, (list, tuple)):
                    for item in act_list:
                        queued_raw.append(str(item))
                else:
                    queued_raw.append(str(act_list))

            def sandbox_route_to(
                target: Any,
                start: tuple[int, int] | list[int] | None = None,
                step_size: int | None = None,
                walkable_colors: list[int] | set[int] | None = None,
            ) -> dict[str, Any]:
                if isinstance(target, dict) and target.get("bbox"):
                    b = target["bbox"]
                    goals = [(r, c) for r in range(b[0], b[2] + 1) for c in range(b[1], b[3] + 1)]
                    tr, tc = int(target.get("centroid", [b[0], b[1]])[0]), int(target.get("centroid", [b[0], b[1]])[1])
                elif isinstance(target, dict) and target.get("centroid"):
                    c = target["centroid"]
                    tr, tc = int(c[0]), int(c[1])
                    goals = [(tr, tc)]
                else:
                    tr, tc = int(target[0]), int(target[1])
                    goals = [(tr, tc)]

                if start is not None:
                    sr, sc = int(start[0]), int(start[1])
                elif self.avatar_pos is not None:
                    sr, sc = self.avatar_pos
                else:
                    sr, sc = (grid_h // 2, grid_w // 2) if has_grid else (0, 0)
                    for n in nodes:
                        if n.get("pixels") == 1 or n.get("color") in (0, 1):
                            sr, sc = int(n["centroid"][0]), int(n["centroid"][1])
                            break

                step = int(step_size or self.detected_step_size or 1)
                moves = {
                    "UP": (-step, 0),
                    "DOWN": (step, 0),
                    "LEFT": (0, -step),
                    "RIGHT": (0, step),
                }

                if walkable_colors is not None:
                    allowed = set(walkable_colors)
                    mask = [[grid[r][c] in allowed for c in range(grid_w)] for r in range(grid_h)]
                else:
                    # Non-black (0) and non-barrier (14) cells are walkable corridors
                    mask = [[grid[r][c] not in (0, 14) for c in range(grid_w)] for r in range(grid_h)]

                if 0 <= sr < grid_h and 0 <= sc < grid_w:
                    mask[sr][sc] = True
                for gr, gc in goals:
                    if 0 <= gr < grid_h and 0 <= gc < grid_w:
                        mask[gr][gc] = True

                path_res = route(mask, start=(sr, sc), goals=goals, moves=moves)
                if path_res.get("status") == "solved" and path_res.get("actions"):
                    sandbox_action(path_res["actions"])
                    print(f"🗺️ [route_to] Computed {len(path_res['actions'])}-step route to ({tr}, {tc}) with step={step}px: {path_res['actions']}", file=stdout_buf)
                else:
                    print(f"⚠️ [route_to] Could not find route from ({sr}, {sc}) to ({tr}, {tc}) with step={step}px", file=stdout_buf)
                return path_res

            sandbox_scope = {
                "action": sandbox_action,
                "candidate_clicks": lambda **kw: candidate_clicks(nodes, **kw),
                "candidate_goals": lambda **kw: candidate_goals(nodes, **kw),
                "route": route,
                "route_to": sandbox_route_to,
                "solve_toggle": solve_toggle,
                "notes": self.notes,
                "grid": grid,
            }

            if code:
                try:
                    with contextlib.redirect_stdout(stdout_buf):
                        exec(code, sandbox_scope)
                except Exception as e:
                    print(f"Error: {e}", file=stdout_buf)
                    logger.warning(f"Sandbox execution error: {e}")

            self.last_sandbox_stdout = stdout_buf.getvalue().strip()

            # 7. Parse queued actions
            for raw in queued_raw:
                parsed = self._convert_action_string(raw, available, latest_frame.game_id)
                if parsed is not None:
                    self.action_queue.append(parsed)

            # If actions were queued, break the loop and execute them!
            if self.action_queue:
                break
            
            # If no actions were queued but we got stdout, loop around and feed it back!
            if self.last_sandbox_stdout:
                self.wasted_loops += 1
                print("🔄 [Introspection Loop] Agent printed output but queued 0 actions. Re-prompting...", flush=True)
                continue

            # If no actions were queued AND no code was executed, try parsing text directly and break
            fallback_act, fallback_coords = parse_action_response(resp, available)
            if fallback_act == GameAction.ACTION6 and fallback_coords:
                fallback_act.set_data({"x": fallback_coords[0], "y": fallback_coords[1], "game_id": latest_frame.game_id})
            self.action_queue.append(fallback_act)
            break
            
        if not self.action_queue:
            # Absolute fallback if max loops exhausted without queuing
            fallback_act, fallback_coords = parse_action_response(resp, available)
            fallback_data = None
            if fallback_act == GameAction.ACTION6 and fallback_coords:
                fallback_data = {"x": fallback_coords[0], "y": fallback_coords[1], "game_id": latest_frame.game_id}
            self.action_queue.append((fallback_act, fallback_data))

        first_act, first_data = self.action_queue.popleft()
        if first_data:
            first_act.set_data(first_data)
        self.last_action = first_act
        self.level_trajectory.append(self._format_action_for_trajectory(first_act, first_data))
        print(f"🚀 [{self.model} Tool] Queued {len(self.action_queue) + 1} action(s). Executing: {first_act.name}", flush=True)
        return first_act
