"""pre_explorer.py - Fast CPU pre-exploration and game manual generation.

Probes movement actions, mouse click coordinates, and action semantics on an
independent environment instance on frame 0 (consuming zero official actions)
before the main LLM run starts.
"""
from __future__ import annotations

import random
import time
from typing import Any, Callable, Iterable

ARC_COLOR_CHARS = "WwgGcBMPRbSYOrNp"

ENGINE_TO_MODEL_ACTION = {
    "ACTION1": "UP",
    "ACTION2": "DOWN",
    "ACTION3": "LEFT",
    "ACTION4": "RIGHT",
    "ACTION5": "SPACE",
    "ACTION6": "MOUSE",
    "RESET": "RESET",
}

_ARROW_ACTIONS = ("ACTION1", "ACTION2", "ACTION3", "ACTION4", "ACTION5", "ACTION7")
_CLICK_ACTION = "ACTION6"
_WALK_MAX_STEPS = 60
MIN_BUDGET_S = 30.0


def _model_action(name: str) -> str:
    return ENGINE_TO_MODEL_ACTION.get(name, name)


def to_grid(frame: Any) -> tuple[tuple[int, ...], ...] | None:
    data = frame
    if isinstance(data, (list, tuple)) and data:
        last = data[-1]
        if hasattr(last, "__len__") and not isinstance(last, (int, str, bytes)):
            try:
                first = last[0]
            except Exception:
                first = None
            if first is not None and hasattr(first, "__len__"):
                data = last
    shape = getattr(data, "shape", None)
    try:
        if shape is not None and len(shape) == 3:
            data = data[-1]
    except TypeError:
        pass
    try:
        rows = list(data)
        if not rows:
            return None
        grid = []
        for row in rows:
            cells = []
            for v in row:
                iv = int(v)
                cells.append(max(0, min(15, iv)))
            grid.append(tuple(cells))
        width = len(grid[0])
        if any(len(r) != width for r in grid):
            return None
        return tuple(grid)
    except (TypeError, ValueError):
        return None


def _color_char(v: int) -> str:
    return ARC_COLOR_CHARS[max(0, min(15, v))]


def _objects(grid: tuple[tuple[int, ...], ...]) -> list[tuple[int, frozenset[tuple[int, int]]]]:
    height, width = len(grid), len(grid[0])
    seen = [[False] * width for _ in range(height)]
    objects: list[tuple[int, frozenset[tuple[int, int]]]] = []
    for r0 in range(height):
        for c0 in range(width):
            if seen[r0][c0]:
                continue
            color = grid[r0][c0]
            stack = [(r0, c0)]
            seen[r0][c0] = True
            cells = []
            while stack:
                r, c = stack.pop()
                cells.append((r, c))
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < height and 0 <= nc < width and not seen[nr][nc] and grid[nr][nc] == color:
                        seen[nr][nc] = True
                        stack.append((nr, nc))
            objects.append((color, frozenset(cells)))
    return objects


def _centroid(cells: frozenset[tuple[int, int]]) -> tuple[float, float]:
    n = len(cells)
    return (sum(r for r, _ in cells) / n, sum(c for _, c in cells) / n)


def diff_summary(
    before: tuple[tuple[int, ...], ...] | None,
    after: tuple[tuple[int, ...], ...] | None,
) -> str:
    if before is None or after is None:
        return "frame unreadable"
    if before == after:
        return "no change"

    def entities(grid):
        objs = _objects(grid)
        if len(objs) <= 1:
            return objs
        bg = max(objs, key=lambda o: len(o[1]))
        return [o for o in objs if o is not bg]

    ob = entities(before)
    oa = entities(after)
    parts: list[str] = [f"objects {len(ob)}->{len(oa)}"]

    def key(color: int, cells: frozenset) -> tuple:
        r0 = min(r for r, _ in cells)
        c0 = min(c for _, c in cells)
        norm = frozenset((r - r0, c - c0) for r, c in cells)
        return (color, norm)

    from collections import defaultdict

    gb: dict[tuple, list[frozenset]] = defaultdict(list)
    ga: dict[tuple, list[frozenset]] = defaultdict(list)
    for color, cells in ob:
        gb[key(color, cells)].append(cells)
    for color, cells in oa:
        ga[key(color, cells)].append(cells)

    moved_notes: list[str] = []
    appeared = 0
    disappeared = 0
    appear_colors: set[int] = set()
    disappear_colors: set[int] = set()
    for k in set(gb) | set(ga):
        b_list = gb.get(k, [])
        a_list = ga.get(k, [])
        color = k[0]
        if b_list and a_list:
            n = min(len(b_list), len(a_list))
            b_sorted = sorted(b_list, key=_centroid)
            a_sorted = sorted(a_list, key=_centroid)
            shifts = set()
            for i in range(n):
                br, bc = _centroid(b_sorted[i])
                ar, ac = _centroid(a_sorted[i])
                shifts.add((round(ar - br), round(ac - bc)))
            zero = {(0, 0)}
            if shifts != zero:
                if len(shifts) == 1:
                    (dr, dc) = next(iter(shifts))
                    moved_notes.append(f"{n} {_color_char(color)}-obj moved (dr={dr:+d},dc={dc:+d})")
                else:
                    moved_notes.append(f"{n} {_color_char(color)}-obj moved inconsistently")
        if len(a_list) > len(b_list):
            appeared += len(a_list) - len(b_list)
            appear_colors.add(color)
        elif len(b_list) > len(a_list):
            disappeared += len(b_list) - len(a_list)
            disappear_colors.add(color)

    if appeared:
        cs = ",".join(sorted(_color_char(c) for c in appear_colors))
        parts.append(f"+{appeared} new obj (colors {cs})")
    if disappeared:
        cs = ",".join(sorted(_color_char(c) for c in disappear_colors))
        parts.append(f"-{disappeared} gone obj (colors {cs})")
    parts.extend(moved_notes[:4])
    return "; ".join(parts)


class _GameFacts:
    __slots__ = (
        "probes",
        "click_hits",
        "click_tries",
        "click_rows",
        "click_cols",
        "click_examples",
        "walk_stats",
        "walk_steps",
        "level_path",
        "notes",
    )

    def __init__(self) -> None:
        self.probes: list[tuple[str, str]] = []
        self.click_hits = 0
        self.click_tries = 0
        self.click_rows: list[int] = []
        self.click_cols: list[int] = []
        self.click_examples: list[tuple[int, int]] = []
        self.walk_stats: dict[str, list[int]] = {}
        self.walk_steps = 0
        self.level_path: list[str] | None = None
        self.notes: list[str] = []


FULL_HEADER = (
    "PRE-EXPLORATION REPORT for this game (a scripted explorer probed a separate instance "
    "of this exact game with the same initial board you see at the start of level 1).\n"
    "Treat these mechanical observations as ground truth for level-1 mechanics and use them "
    "instead of re-discovering action semantics. Effects may differ on later levels - "
    "re-verify there. Board coordinates are (row, col), row 0 is the top. Action names here "
    "are the same names you pass to action().\n"
)


def build_manual(gid: str, facts: _GameFacts, max_chars: int = 2000) -> str:
    has_facts = bool(facts.probes or facts.click_tries or facts.walk_steps or facts.level_path)
    lines: list[str] = []
    if facts.level_path:
        seq = ", ".join(_model_action(a) for a in facts.level_path)
        lines.append(f"Verified level path: [{seq}] advanced the level (replayed and confirmed).")
    if facts.probes:
        lines.append("Action probes from the initial board (1 step each, then reset):")
        for name, summary in facts.probes:
            lines.append(f"- {_model_action(name)}: {summary}")
    if facts.click_tries:
        lines.append(
            f"Click probes ({_model_action(_CLICK_ACTION)}): {facts.click_hits}/{facts.click_tries} sampled points changed the board."
        )
        if facts.click_examples:
            pts = ", ".join(f"({r},{c})" for r, c in facts.click_examples)
            lines.append(f"  Effective points (row,col): {pts}.")
        if facts.click_rows:
            lines.append(
                f"  Effective region rows {min(facts.click_rows)}-{max(facts.click_rows)}, "
                f"cols {min(facts.click_cols)}-{max(facts.click_cols)}."
            )
    if facts.walk_steps:
        parts = []
        for name in sorted(facts.walk_stats):
            changed, tries = facts.walk_stats[name]
            parts.append(f"{_model_action(name)} {changed}/{tries}")
        lines.append(f"Random walk ({facts.walk_steps} steps), board changed per action: " + ", ".join(parts) + ".")
    for note in facts.notes:
        lines.append(f"Note: {note}")

    if not has_facts:
        return ""

    body = "\n".join(lines)
    result = FULL_HEADER + body
    if len(result) > max_chars:
        result = result[: max(0, max_chars - 16)] + "\n... (truncated)"
    return result
