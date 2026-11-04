"""BFS shortest pathfinder for grid navigation in ARC-AGI-3."""
from __future__ import annotations

from collections import deque
from collections.abc import Collection, Sequence


def bfs_path(
    start: tuple[int, int] | Sequence[int] | None,
    goal: tuple[int, int] | Sequence[int] | Collection[tuple[int, int]] | None,
    walkable: Collection[tuple[int, int]] | None = None,
    blocked: Collection[tuple[int, int]] | None = None,
    step: int = 1,
    bounds: tuple[int, int] = (64, 64),
) -> list[str] | None:
    """Find shortest action sequence of UP/DOWN/LEFT/RIGHT from start to goal.

    Parameters
    ----------
    start : (row, col) tuple
    goal : (row, col) or collection of (row, col) targets
    walkable : optional set of allowed (row, col) cells
    blocked : optional set of obstacle (row, col) cells
    step : grid step distance (default 1)
    bounds : (max_rows, max_cols) grid boundary limits
    """
    if start is None or goal is None:
        return None
    try:
        start_pt = (int(start[0]), int(start[1]))
    except (TypeError, IndexError, ValueError):
        return None

    try:
        if isinstance(goal, (tuple, list)) and len(goal) == 2 and isinstance(goal[0], (int, float)):
            goal_set = {(int(goal[0]), int(goal[1]))}
        else:
            goal_set = {(int(p[0]), int(p[1])) for p in goal}
    except (TypeError, IndexError, ValueError):
        return None

    if not goal_set:
        return None

    if start_pt in goal_set:
        return []

    walk_set = {(int(p[0]), int(p[1])) for p in walkable} if walkable is not None else None
    block_set = {(int(p[0]), int(p[1])) for p in blocked} if blocked is not None else set()

    max_r, max_c = bounds
    dirs = [("UP", -step, 0), ("DOWN", step, 0), ("LEFT", 0, -step), ("RIGHT", 0, step)]
    visited = {start_pt: None}
    q = deque([start_pt])

    while q:
        curr = q.popleft()
        if curr in goal_set:
            path: list[str] = []
            c = curr
            while visited[c] is not None:
                prev_pt, act = visited[c]
                path.append(act)
                c = prev_pt
            return list(reversed(path))

        for act_name, dr, dc in dirs:
            nr, nc = curr[0] + dr, curr[1] + dc
            nxt = (nr, nc)
            if nxt in visited:
                continue
            if nxt in block_set:
                continue
            if walk_set is not None and nxt not in walk_set:
                continue
            if nr < 0 or nr >= max_r or nc < 0 or nc >= max_c:
                continue
            visited[nxt] = (curr, act_name)
            q.append(nxt)

    return None
