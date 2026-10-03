from __future__ import annotations

import random
from collections.abc import Sequence

from arcengine import FrameData, GameAction

from src.agents.base import BaseAgent


class RandomAgent(BaseAgent):
    """Uniformly samples from available actions with coordinate generation for ACTION6."""

    def __init__(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed)

    def choose_action(
        self,
        frames: Sequence[FrameData],
        latest_frame: FrameData,
    ) -> GameAction:
        available = latest_frame.available_actions
        if not available:
            return GameAction.RESET

        action_int = self.rng.choice(available)
        action = GameAction.from_id(action_int)

        if action == GameAction.ACTION6:
            r = self.rng.randint(0, 63)
            c = self.rng.randint(0, 63)
            action.set_data({"x": r, "y": c, "game_id": latest_frame.game_id})

        return action
