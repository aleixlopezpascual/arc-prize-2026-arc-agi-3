from __future__ import annotations

from collections.abc import Sequence

from arc_agi import Arcade
from arcengine import GameAction

from src.perception.frame_diff import compute_frame_diff


class BranchEvaluator:
    def __init__(self, arcade: Arcade) -> None:
        self.arcade = arcade

    def run_probe(
        self,
        game_id: str,
        scorecard_id: str,
        actions: Sequence[GameAction],
    ) -> dict:
        env = self.arcade.make(game_id, scorecard_id=scorecard_id)
        if env is None:
            return {"changed_cell_count": 0}

        before_state = env.reset()
        after_state = before_state

        for action in actions:
            step_res = env.step(action)
            if step_res is not None:
                after_state = step_res

        before_frame = before_state.frame[0] if before_state and before_state.frame else []
        after_frame = after_state.frame[0] if after_state and after_state.frame else []

        return compute_frame_diff(before_frame, after_frame)
