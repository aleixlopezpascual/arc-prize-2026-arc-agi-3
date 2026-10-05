"""Manager for cross-level solved memory, serialized safely into the sandbox."""
from __future__ import annotations

from typing import Any


class SolvedMemoryManager:
    """Tracks cleared level mechanics and winning action patterns across levels."""

    def __init__(self) -> None:
        self._memories: list[dict[str, Any]] = []

    def record_level_cleared(
        self,
        *,
        level: int,
        actions_taken: int,
        winning_actions: list[str] | None = None,
    ) -> None:
        """Record the verified solution of a level."""
        self._memories.append({
            "level": int(level),
            "actions_taken": int(actions_taken),
            "winning_actions": [str(a) for a in (winning_actions or [])[-5:]],
        })

    def get_memory_payload(self) -> list[dict[str, Any]]:
        """Return JSON-safe copy of cleared level memories."""
        return [dict(m) for m in self._memories]

    def reset(self) -> None:
        """Clear memories when starting a new game."""
        self._memories.clear()
