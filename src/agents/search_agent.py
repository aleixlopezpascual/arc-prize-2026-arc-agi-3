from __future__ import annotations

import random
from collections.abc import Sequence

from arcengine import FrameData, GameAction

from src.agents.base import BaseAgent
from src.guards.noop_repeat_guard import NoopRepeatGuard, compute_interior_hash
from src.perception.centroids import extract_candidate_clicks
from src.search.action_selector import SearchAwareAgent


class PerceptionSearchAgent(BaseAgent, SearchAwareAgent):
    """Search-guided agent combining object centroid clicks and no-op pruning."""

    def __init__(self, seed: int | None = None, epsilon: float = 0.1) -> None:
        super().__init__(evaluator=None)
        self.rng = random.Random(seed)
        self.epsilon = epsilon
        self.guard = NoopRepeatGuard()
        self.current_level = 0

    def reset(self) -> None:
        self.guard.note_level(0)
        self.current_level = 0

    def choose_action(
        self,
        frames: Sequence[FrameData],
        latest_frame: FrameData,
    ) -> GameAction:
        available = latest_frame.available_actions
        if not available:
            return GameAction.RESET

        if latest_frame.levels_completed != self.current_level:
            self.current_level = latest_frame.levels_completed
            self.guard.note_level(self.current_level)

        grid = latest_frame.frame[0] if latest_frame.frame and len(latest_frame.frame) > 0 else []
        state_hash = compute_interior_hash(grid)

        # Build candidate action pool
        candidates: list[GameAction] = []

        for act_int in available:
            if act_int == 6:
                # ACTION6: generate coordinate clicks from segmented centroids
                clicks = extract_candidate_clicks(grid, max_candidates=6)
                for r, c in clicks:
                    act = GameAction.from_id(6)
                    act.set_data({"x": r, "y": c, "game_id": latest_frame.game_id})
                    candidates.append(act)
            else:
                candidates.append(GameAction.from_id(act_int))

        # Filter out candidates blocked by NoopRepeatGuard
        unblocked = [
            c
            for c in candidates
            if not self.guard.should_block(
                state_hash,
                c.name
                if c != GameAction.ACTION6
                else f"ACTION6({c.action_data.x},{c.action_data.y})",
            )
        ]

        active_pool = unblocked if unblocked else candidates

        if self.rng.random() < self.epsilon or len(active_pool) == 1:
            chosen = self.rng.choice(active_pool)
        else:
            # Prefer ACTION6 clicks over random simple actions when objects exist
            click_actions = [a for a in active_pool if a == GameAction.ACTION6]
            if click_actions and self.rng.random() < 0.6:
                chosen = self.rng.choice(click_actions)
            else:
                chosen = self.rng.choice(active_pool)

        return chosen
