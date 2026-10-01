"""Official Evaluation Metric for ARC Prize 2026 - ARC-AGI-3.

Scoring combines completion rate and efficiency (actions taken vs human baseline):
1. Per-level score: (baseline_actions / actions_taken)^2 * 100, capped at 115.0. 0 if not completed.
2. Per-game score: 1-indexed weighted average across levels, capped at (completed_weights / total_weights) * 100.
3. Total competition score: unweighted arithmetic mean across all evaluated games (0% - 100%).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass
class LevelScore:
    level_index: int  # 1-indexed (1, 2, ...)
    baseline_actions: int
    actions_taken: int
    completed: bool
    score: float = 0.0

    def __post_init__(self) -> None:
        if self.completed and self.actions_taken > 0 and self.baseline_actions > 0:
            raw_score = ((self.baseline_actions / self.actions_taken) ** 2) * 100.0
            self.score = min(raw_score, 115.0)
        else:
            self.score = 0.0


@dataclass
class GameScore:
    game_id: str
    levels: list[LevelScore] = field(default_factory=list)

    @property
    def levels_completed(self) -> int:
        return sum(1 for lvl in self.levels if lvl.completed)

    @property
    def total_actions(self) -> int:
        return sum(lvl.actions_taken for lvl in self.levels)

    @property
    def score(self) -> float:
        if not self.levels:
            return 0.0

        total_weighted_score = 0.0
        total_weights = 0
        completed_weights = 0

        for lvl in self.levels:
            weight = lvl.level_index
            total_weighted_score += lvl.score * weight
            total_weights += weight
            if lvl.score > 0.0:
                completed_weights += weight

        if total_weights == 0:
            return 0.0

        raw_game_score = total_weighted_score / total_weights
        max_allowed_score = (completed_weights / total_weights) * 100.0
        return min(raw_game_score, max_allowed_score)


def compute_level_score(
    baseline_actions: int,
    actions_taken: int,
    completed: bool,
) -> float:
    """Compute score for a single level in an ARC-AGI-3 environment.

    Args:
        baseline_actions: Benchmark human test-taker action count.
        actions_taken: Actions taken by agent on this level.
        completed: Whether the agent cleared the level.

    Returns:
        Level score as float in [0.0, 115.0].
    """
    if completed and actions_taken > 0 and baseline_actions > 0:
        raw = ((baseline_actions / actions_taken) ** 2) * 100.0
        return min(raw, 115.0)
    return 0.0


def compute_game_score(
    levels: Sequence[tuple[int, int, bool]],
) -> float:
    """Compute score for a single game from a sequence of level outcomes.

    Args:
        levels: Sequence of (baseline_actions, actions_taken, completed) tuples,
                assumed in sequential 1-indexed order (level 1, level 2, ...).

    Returns:
        Game score as float in [0.0, 100.0].
    """
    if not levels:
        return 0.0

    total_weighted_score = 0.0
    total_weights = 0
    completed_weights = 0

    for idx, (baseline_actions, actions_taken, completed) in enumerate(levels, start=1):
        weight = idx
        lvl_score = compute_level_score(baseline_actions, actions_taken, completed)
        total_weighted_score += lvl_score * weight
        total_weights += weight
        if lvl_score > 0.0:
            completed_weights += weight

    if total_weights == 0:
        return 0.0

    raw_game_score = total_weighted_score / total_weights
    max_score = (completed_weights / total_weights) * 100.0
    return min(raw_game_score, max_score)


def compute_competition_score(
    game_scores: Sequence[float] | dict[str, float],
) -> float:
    """Compute overall competition score across all evaluated games.

    Args:
        game_scores: Sequence or dict of per-game scores.

    Returns:
        Arithmetic mean of game scores in [0.0, 100.0].
    """
    if isinstance(game_scores, dict):
        scores = list(game_scores.values())
    else:
        scores = list(game_scores)

    if not scores:
        return 0.0

    return sum(scores) / len(scores)
