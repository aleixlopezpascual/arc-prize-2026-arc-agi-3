from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from arcengine import FrameData, GameAction, GameState


class BaseAgent(ABC):
    """Abstract base class for all ARC-AGI-3 agents."""

    @abstractmethod
    def choose_action(
        self,
        frames: Sequence[FrameData],
        latest_frame: FrameData,
    ) -> GameAction | tuple[GameAction, tuple[int, int]]:
        """Choose the next action given frame history and latest frame."""

    def is_done(
        self,
        frames: Sequence[FrameData],
        latest_frame: FrameData,
    ) -> bool:
        """Return True if agent should terminate play for this environment."""
        return latest_frame.state in (GameState.WIN, GameState.GAME_OVER)

    def reset(self) -> None:
        """Reset internal episodic state between games."""
