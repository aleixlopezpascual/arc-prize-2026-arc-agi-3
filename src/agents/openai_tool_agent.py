from __future__ import annotations

import collections
import json
import logging
import os
import re
import urllib.error
import urllib.request
from collections.abc import Sequence
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
    ) -> None:
        from dotenv import load_dotenv
        from src.config import ROOT

        load_dotenv(ROOT / ".env")
        self.model = os.environ.get("OPENAI_MODEL", model)
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.api_base = os.environ.get("OPENAI_BASE_URL", api_base).rstrip("/")
        self.timeout = timeout

        self.action_queue: collections.deque[GameAction] = collections.deque()
        self.notes: dict[str, Any] = {"game": {}, "level": {}}
        self.guard = NoopRepeatGuard()
        self.last_action: GameAction | None = None
        self.current_level = 0

    def reset(self) -> None:
        self.action_queue.clear()
        self.notes = {"game": {}, "level": {}}
        self.guard = NoopRepeatGuard()
        self.last_action = None
        self.current_level = 0

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
            return "action(['RESET'])"
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            return "action(['RESET'])"

    def _convert_action_string(
        self,
        act_str: str,
        available: list[int],
        game_id: str,
    ) -> GameAction | None:
        """Convert action string like 'UP' or 'CLICK(10, 20)' to GameAction."""
        raw = str(act_str).strip().upper()
        coords_match = re.search(r"(?:CLICK|MOUSE|ACTION6)\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)", raw)
        if coords_match:
            r, c = int(coords_match.group(1)), int(coords_match.group(2))
            if 6 in available:
                act = GameAction.ACTION6
                act.set_data({"x": r, "y": c, "game_id": game_id})
                return act

        for name, act in ACTION_MAP.items():
            if raw == name or raw == act.name:
                if act.value in available:
                    return act

        # Match ACTION<N>
        num_match = re.search(r"\bACTION([1-7])\b", raw)
        if num_match:
            val = int(num_match.group(1))
            if val in available:
                return GameAction.from_id(val)

        return None

    def choose_action(
        self,
        frames: Sequence[FrameData],
        latest_frame: FrameData,
    ) -> GameAction:
        available = latest_frame.available_actions
        if not available:
            return GameAction.RESET

        # 1. Check level change first and reset queue
        if latest_frame.levels_completed != self.current_level:
            self.current_level = latest_frame.levels_completed
            self.guard.note_level(self.current_level)
            self.notes = normalize_notes(self.notes, self.current_level)
            if self.action_queue:
                print(f"🎉 [Level Cleared] Clearing {len(self.action_queue)} queued action(s) for new level.", flush=True)
                self.action_queue.clear()
            self.last_action = None

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

            if not gameplay_changed:
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
                    details.append(f"moved object to bbox {diff['moved'][0]['to_bbox']}")
                if diff.get("appeared"):
                    details.append(f"new object appeared at bbox {diff['appeared'][0]['bbox']}")
                if diff.get("changed_color"):
                    details.append(f"color changed to {diff['changed_color'][0]['after_color']}")
                detail_str = f" ({', '.join(details)})" if details else ""
                feedback_msg = f"Last action '{self.last_action.name}' modified {n_changed} pixels{detail_str}."

        # 3. Check if we still have active queued actions
        if self.action_queue:
            next_action = self.action_queue.popleft()
            self.last_action = next_action
            print(f"⚡ [Queue Replay] Executing queued action: {next_action.name}", flush=True)
            return next_action

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

        if feedback_msg:
            prompt_parts.append(feedback_msg)

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
        prompt_parts.append(
            "Write Python code calling action([actions...]) to execute your plan.\n"
            "PLANNING TIP: If navigating open corridors or paths, plan multiple moves in a sequence like action(['UP', 'UP', 'RIGHT', 'RIGHT'])!\n"
            "You can use candidate_clicks(), candidate_goals(), route(), solve_toggle(), notes."
        )
        prompt = "\n\n".join(prompt_parts)

        # 4. Call LLM
        resp = self._call_api(prompt)
        non_fence_lines = [l.strip() for l in resp.strip().splitlines() if l.strip() and not l.strip().startswith("```")]
        first_line = non_fence_lines[0] if non_fence_lines else resp.strip().splitlines()[0] if resp.strip() else ""
        print(f"🤖 [{self.model} Tool] L{latest_frame.levels_completed} Thinking: {first_line[:85]}", flush=True)

        # 5. Extract and execute Python snippet
        code = extract_python_snippet(resp)
        queued_raw: list[str] = []

        def sandbox_action(act_list: list[Any]) -> None:
            if isinstance(act_list, (list, tuple)):
                for item in act_list:
                    queued_raw.append(str(item))
            else:
                queued_raw.append(str(act_list))

        sandbox_scope = {
            "action": sandbox_action,
            "candidate_clicks": lambda **kw: candidate_clicks(nodes, **kw),
            "candidate_goals": lambda **kw: candidate_goals(nodes, **kw),
            "route": route,
            "solve_toggle": solve_toggle,
            "notes": self.notes,
            "grid": grid,
        }

        if code:
            try:
                exec(code, sandbox_scope)
            except Exception as e:
                logger.warning(f"Sandbox execution error: {e}")

        # 6. Parse queued actions
        for raw in queued_raw:
            parsed = self._convert_action_string(raw, available, latest_frame.game_id)
            if parsed is not None:
                self.action_queue.append(parsed)

        # If nothing was queued via code, try parsing standard text response
        if not self.action_queue:
            fallback_act, fallback_coords = parse_action_response(resp, available)
            if fallback_act == GameAction.ACTION6 and fallback_coords:
                fallback_act.set_data({"x": fallback_coords[0], "y": fallback_coords[1], "game_id": latest_frame.game_id})
            self.action_queue.append(fallback_act)

        first_act = self.action_queue.popleft()
        self.last_action = first_act
        print(f"🚀 [{self.model} Tool] Queued {len(self.action_queue) + 1} action(s). Executing: {first_act.name}", flush=True)
        return first_act
