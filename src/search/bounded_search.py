"""Bounded state-space search and boolean grid pathfinding primitives."""
from __future__ import annotations

import collections
import heapq
import itertools
import math
import time
from collections.abc import Callable
from typing import Any


def freeze_state(value: Any) -> Any:
    """Hashable, type-preserving key for small symbolic search states."""
    if isinstance(value, dict):
        pairs = [(freeze_state(k), freeze_state(v)) for k, v in value.items()]
        return ("dict", tuple(sorted(pairs, key=repr)))
    if isinstance(value, (set, frozenset)):
        return ("set", tuple(sorted((freeze_state(v) for v in value), key=repr)))
    if isinstance(value, (list, tuple)):
        return (type(value).__name__, tuple(freeze_state(v) for v in value))
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Search states must contain finite numbers")
    hash(value)
    return (type(value).__name__, value)


def bounded_search(
    start: Any,
    successors: Callable[[Any], list[tuple]],
    is_goal: Callable[[Any], bool],
    heuristic: Callable[[Any], float] | None = None,
    max_nodes: int = 40000,
    max_depth: int = 200,
    seconds: float = 3.0,
) -> dict[str, Any]:
    """Uniform-cost search, or A* with an admissible heuristic.

    successors(state) yields (action, next_state) or (action, next_state, cost).
    """
    max_nodes = min(200000, max(1, int(max_nodes)))
    max_depth = min(2000, max(0, int(max_depth)))
    seconds = float(seconds)
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("seconds must be finite and positive")
    deadline = time.monotonic() + min(10.0, seconds)
    h = heuristic if heuristic is not None else lambda _: 0.0
    key = freeze_state(start)
    sequence = itertools.count()
    root = (None, None)
    estimate = float(h(start))
    if not math.isfinite(estimate):
        raise ValueError("Heuristic must return finite numbers")
    queue = [(estimate, next(sequence), 0.0, 0, key, start, root)]
    best = {key: {0: 0.0}}
    expanded, generated, cut_depth = 0, 1, False
    while queue:
        if expanded >= max_nodes or time.monotonic() >= deadline:
            return dict(status="limit", actions=None, expanded=expanded, visited=len(best))
        _, _, cost, depth, key, state, path = heapq.heappop(queue)
        if cost != best.get(key, {}).get(depth):
            continue
        if is_goal(state):
            actions = []
            while path[0] is not None:
                path, act = path
                actions.append(act)
            actions.reverse()
            return dict(
                status="solved",
                actions=actions,
                cost=cost,
                expanded=expanded,
                visited=len(best),
            )
        expanded += 1
        if depth >= max_depth:
            cut_depth = True
            continue
        for item in successors(state):
            if len(item) == 2:
                act, nxt = item
                step_cost = 1.0
            elif len(item) == 3:
                act, nxt, step_cost = item
                step_cost = float(step_cost)
            else:
                raise ValueError("successors must yield (action, state[, cost])")
            if not math.isfinite(step_cost) or step_cost <= 0:
                raise ValueError("Search costs must be finite and strictly positive")
            nxt_key, nxt_cost, nxt_depth = freeze_state(nxt), cost + step_cost, depth + 1
            frontier = best.get(nxt_key, {})
            if any(d <= nxt_depth and c <= nxt_cost for d, c in frontier.items()):
                continue
            estimate = float(h(nxt))
            if not math.isfinite(estimate):
                raise ValueError("Heuristic must return finite numbers")
            if generated >= max_nodes:
                return dict(status="limit", actions=None, expanded=expanded, visited=len(best))
            best[nxt_key] = {
                d: c for d, c in frontier.items() if not (d >= nxt_depth and c >= nxt_cost)
            }
            best[nxt_key][nxt_depth] = nxt_cost
            generated += 1
            heapq.heappush(
                queue,
                (
                    nxt_cost + estimate,
                    next(sequence),
                    nxt_cost,
                    nxt_depth,
                    nxt_key,
                    nxt,
                    (path, act),
                ),
            )
    return dict(
        status="limit" if cut_depth else "exhausted",
        actions=None,
        expanded=expanded,
        visited=len(best),
    )


def route(
    mask: list[list[bool]],
    start: tuple[int, int] | list[int],
    goals: list[tuple[int, int]] | set[tuple[int, int]],
    moves: dict[str, tuple[int, int]] | None = None,
) -> dict[str, Any]:
    """Shortest route on an explicitly supplied boolean traversability mask."""
    rows = tuple(tuple(bool(v) for v in row) for row in mask)
    height, width = len(rows), len(rows[0]) if rows else 0
    if not height or not width or any(len(row) != width for row in rows):
        raise ValueError("mask must be a nonempty rectangular boolean grid")
    start = tuple(start)
    goals = {tuple(g) for g in goals}
    moves = moves or {"UP": (-1, 0), "DOWN": (1, 0), "LEFT": (0, -1), "RIGHT": (0, 1)}
    if len(start) != 2 or not (0 <= start[0] < height and 0 <= start[1] < width):
        raise ValueError("start must be an in-bounds (row, col)")
    if not rows[start[0]][start[1]]:
        raise ValueError("start is blocked in the supplied mask")
    queue, parents = collections.deque([start]), {start: None}
    while queue:
        pos = queue.popleft()
        if pos in goals:
            actions, cells = [], [pos]
            while parents[pos] is not None:
                pos, act = parents[pos]
                actions.append(act)
                cells.append(pos)
            return dict(
                status="solved",
                actions=actions[::-1],
                cells=cells[::-1],
                cost=len(actions),
            )
        for act, (dr, dc) in moves.items():
            nxt = (pos[0] + dr, pos[1] + dc)
            if (
                0 <= nxt[0] < height
                and 0 <= nxt[1] < width
                and rows[nxt[0]][nxt[1]]
                and nxt not in parents
            ):
                parents[nxt] = (pos, act)
                queue.append(nxt)
    return dict(status="exhausted", actions=None, cells=None)
