from __future__ import annotations

from typing import Any


def extract_winning_segments(
    recording: list[tuple[str, dict[str, Any], int, Any, bool]],
    max_level: int,
) -> dict[int, list[tuple[str, dict[str, Any]]]]:
    """Extracts contiguous, death-free winning action sequences per level.

    Args:
        recording: List of (action_name, action_data, levels_completed, state, just_won_level).
        max_level: Highest level reached/completed.

    Returns:
        Dict mapping level_number (1-indexed) to list of (action_name, action_data).
    """
    if max_level < 1 or not recording:
        return {}

    segments: dict[int, list[tuple[str, dict[str, Any]]]] = {}
    current_level = 1
    buffer: list[tuple[str, dict[str, Any]]] = []
    prev_completed_levels = 0

    state_name = lambda s: getattr(s, "name", str(s))

    for action_name, action_data, levels_completed, state, won in recording:
        if state_name(state) == "GAME_OVER":
            buffer.clear()
            prev_completed_levels = levels_completed
            continue

        if action_name == "RESET":
            buffer.clear()
            prev_completed_levels = levels_completed
            continue

        buffer.append((action_name, dict(action_data or {})))
        level_won = won or (levels_completed > prev_completed_levels)
        prev_completed_levels = levels_completed

        if level_won and levels_completed >= current_level:
            segments[current_level] = list(buffer)
            buffer.clear()
            current_level += 1
            if current_level > max_level:
                break

    return segments
