from __future__ import annotations

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
from src.perception.centroids import extract_candidate_clicks

logger = logging.getLogger("openai_agent")

ASCII_LETTERS = "WwgGcBMPRbSYOrNp"
ACTION_MAP = {
    "UP": GameAction.ACTION1,
    "DOWN": GameAction.ACTION2,
    "LEFT": GameAction.ACTION3,
    "RIGHT": GameAction.ACTION4,
    "SPACE": GameAction.ACTION5,
    "INTERACT": GameAction.ACTION5,
    "UNDO": GameAction.ACTION7,
    "RESET": GameAction.RESET,
}


def grid_to_ascii(grid: list[list[int]]) -> str:
    """Convert 2D integer grid (0-15) to compact ASCII character representation."""
    lines = []
    for row in grid:
        line = "".join(ASCII_LETTERS[val] if 0 <= val < len(ASCII_LETTERS) else "?" for val in row)
        lines.append(line)
    return "\n".join(lines)


def parse_action_response(
    response_text: str,
    available_actions: list[int],
) -> tuple[GameAction, tuple[int, int] | None]:
    """Parse model text response to GameAction and optional (row, col) coordinates."""
    text = response_text.strip().upper()

    # Match CLICK(r, c) or MOUSE(r, c) or ACTION6(r, c)
    coords_match = re.search(r"(?:CLICK|MOUSE|ACTION6)\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)", text)
    if coords_match:
        r, c = int(coords_match.group(1)), int(coords_match.group(2))
        return GameAction.ACTION6, (r, c)

    # Check for direct named actions
    for name, action in ACTION_MAP.items():
        if re.search(rf"\b{name}\b", text):
            if action.value in available_actions:
                return action, None

    # Check for ACTION<N>
    act_num_match = re.search(r"\bACTION([1-7])\b", text)
    if act_num_match:
        act_num = int(act_num_match.group(1))
        if act_num in available_actions:
            return GameAction.from_id(act_num), None

    # Fallback to first available action
    fallback_id = available_actions[0] if available_actions else 0
    return GameAction.from_id(fallback_id), None


class OpenAIAgent(BaseAgent):
    """Direct-action agent querying OpenAI models (e.g. gpt-6-luna) for action selection."""

    def __init__(
        self,
        model: str = "gpt-6-luna",
        api_key: str | None = None,
        api_base: str = "https://api.openai.com/v1",
        timeout: float = 30.0,
    ) -> None:
        self.model = os.environ.get("OPENAI_MODEL", model)
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.api_base = os.environ.get("OPENAI_BASE_URL", api_base).rstrip("/")
        self.timeout = timeout
        self.history: list[dict[str, Any]] = []

    def reset(self) -> None:
        self.history.clear()

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
                        "You are an expert game-playing agent for ARC-AGI-3. "
                        "Given the current board and available actions, determine the best move to advance levels or solve the puzzle. "
                        "Output a concise 1-sentence thought, followed by your chosen action in the format:\n"
                        "ACTION: <UP|DOWN|LEFT|RIGHT|SPACE|CLICK(row, col)|RESET|ACTION1..ACTION7>"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
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

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                return resp_data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            return "ACTION: RESET"

    def choose_action(
        self,
        frames: Sequence[FrameData],
        latest_frame: FrameData,
    ) -> GameAction:
        available = latest_frame.available_actions
        if not available:
            return GameAction.RESET

        grid = latest_frame.frame[0] if latest_frame.frame and len(latest_frame.frame) > 0 else []
        ascii_grid = grid_to_ascii(grid)

        # Build prompt
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
        ]

        if 6 in available and grid:
            clicks = extract_candidate_clicks(grid, max_candidates=6)
            if clicks:
                prompt_parts.append(
                    "Detected clickable objects (centroids):\n"
                    + "\n".join(f"  - click ({r}, {c})" for r, c in clicks)
                )

        prompt_parts.append(f"Current Board ({len(grid)}x{len(grid[0]) if grid else 0}):\n{ascii_grid}")
        prompt = "\n\n".join(prompt_parts)

        resp = self._call_api(prompt)
        action, coords = parse_action_response(resp, available)

        if action == GameAction.ACTION6:
            if coords is not None:
                r, c = coords
            else:
                # Fallback to first centroid or board center
                clicks = extract_candidate_clicks(grid, max_candidates=1) if grid else []
                if clicks:
                    r, c = clicks[0]
                else:
                    r, c = len(grid) // 2 if grid else 0, len(grid[0]) // 2 if grid and grid[0] else 0
            action.set_data({"x": r, "y": c, "game_id": latest_frame.game_id})

        return action
