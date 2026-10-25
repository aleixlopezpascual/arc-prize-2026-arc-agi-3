"""Perception primitives injected into the Python tool sandbox."""
from __future__ import annotations

from collections import Counter
from typing import Any


def candidate_clicks(
    nodes: list[dict[str, Any]] | None,
    color: str | int | None = None,
    min_size: int = 1,
    max_size: int | None = None,
    exclude_border: bool = True,
) -> list[dict[str, Any]]:
    """Return filtered, sorted candidate click targets from object nodes."""
    if not nodes:
        return []

    candidates: list[dict[str, Any]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if exclude_border and node.get("is_border", False):
            continue
        if color is not None and node.get("color") != color:
            continue
        pixels = int(node.get("pixels", 0))
        if pixels < min_size:
            continue
        if max_size is not None and pixels > max_size:
            continue

        centroid = node.get("centroid")
        bbox = node.get("bbox")
        candidates.append({
            "id": node.get("id"),
            "color": node.get("color"),
            "centroid": list(centroid) if centroid else None,
            "bbox": list(bbox) if bbox else None,
            "pixels": pixels,
        })

    # Sort largest objects first by default
    candidates.sort(key=lambda item: item["pixels"], reverse=True)
    return candidates


def candidate_goals(
    nodes: list[dict[str, Any]] | None,
    exclude_border: bool = True,
    max_candidates: int = 8,
) -> list[dict[str, Any]]:
    """Identify candidate goal targets and sockets from segmented object nodes.

    Ranks objects by goal likelihood based on:
    1. Color singularity: Colors that appear on 1 or 2 small objects only (rare landmarks).
    2. Small landmark size: Targets and sockets are typically 1 to 4 pixels.
    3. Non-border status.

    Returns:
        List of candidate goal objects with id, color, centroid, bbox, pixels, and goal_score.
    """
    if not nodes:
        return []

    valid_nodes = []
    color_counts = Counter()
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if exclude_border and node.get("is_border", False):
            continue
        c = node.get("color")
        color_counts[c] += 1
        valid_nodes.append(node)

    if not valid_nodes:
        return []

    scored_candidates = []
    for node in valid_nodes:
        c = node.get("color")
        pixels = int(node.get("pixels", 0))
        freq = color_counts[c]

        score = 0.0
        if freq == 1:
            score += 50.0  # Unique color on board
        elif freq == 2:
            score += 30.0  # Pair color (e.g. key and door)
        elif freq <= 4:
            score += 15.0

        if 1 <= pixels <= 4:
            score += 30.0 - (pixels * 3.0)  # Favor single pixel or 2x2 targets
        elif pixels <= 9:
            score += 10.0

        centroid = node.get("centroid")
        bbox = node.get("bbox")
        scored_candidates.append({
            "id": node.get("id"),
            "color": c,
            "centroid": list(centroid) if centroid else None,
            "bbox": list(bbox) if bbox else None,
            "pixels": pixels,
            "goal_score": round(score, 1),
        })

    scored_candidates.sort(key=lambda item: item["goal_score"], reverse=True)
    return scored_candidates[:max_candidates]


def object_at(
    nodes: list[dict[str, Any]] | None,
    row: int,
    col: int,
) -> dict[str, Any] | None:
    """Find the object node covering cell (row, col)."""
    if not nodes:
        return None

    for node in nodes:
        if not isinstance(node, dict):
            continue
        bbox = node.get("bbox")
        if not bbox or len(bbox) != 4:
            continue
        min_r, min_c, max_r, max_c = bbox
        if min_r <= row <= max_r and min_c <= col <= max_c:
            return dict(node)

    return None


def detect_indicators(
    before: list[list[int]] | None,
    after: list[list[int]] | None,
) -> list[dict[str, Any]]:
    """Detect small indicator patches far from moving clusters."""
    if not before or not after:
        return []
    from src.perception.fable_core import small_far_changes
    return small_far_changes(before, after)


def detect_budget_helper(
    frames: list[list[list[int]]] | None,
) -> dict[str, Any] | None:
    """Detect linear fuel or countdown budget bar across frames."""
    if not frames or len(frames) < 3:
        return None
    from src.perception.fable_core import detect_budget
    return detect_budget(frames)


def solve_toggle(
    button_masks: list[int],
    target: int,
    n_cells: int | None = None,
    max_nullity: int = 18,
) -> dict[str, Any]:
    """Solve independent binary XOR toggles from measured button effects via GF(2) Gaussian elimination."""
    masks = [int(x) for x in button_masks]
    target = int(target)
    if target < 0 or any(x < 0 for x in masks) or len(masks) > 256:
        raise ValueError("Use at most 256 nonnegative button masks and target")
    required = max([target.bit_length()] + [m.bit_length() for m in masks])
    n_cells = required if n_cells is None else int(n_cells)
    if not required <= n_cells <= 4096:
        raise ValueError("n_cells must cover all mask bits and be <=4096")
    basis = {}
    nullspace = []
    for index, vector in enumerate(masks):
        combination = 1 << index
        while vector:
            pivot = vector.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = (vector, combination)
                break
            row, row_combination = basis[pivot]
            vector ^= row
            combination ^= row_combination
        if not vector:
            nullspace.append(combination)
    residual, solution = target, 0
    while residual:
        pivot = residual.bit_length() - 1
        if pivot not in basis:
            return dict(
                solvable=False,
                indices=None,
                minimal=False,
                nullity=len(nullspace),
                clicks=0,
            )
        row, combination = basis[pivot]
        residual ^= row
        solution ^= combination
    minimal = len(nullspace) <= min(18, max(0, int(max_nullity)))
    if minimal:
        current, best, last_gray = solution, solution, 0
        for i in range(1, 1 << len(nullspace)):
            gray = i ^ (i >> 1)
            current ^= nullspace[(gray ^ last_gray).bit_length() - 1]
            last_gray = gray
            if current.bit_count() < best.bit_count():
                best = current
        solution = best
    else:
        for _ in range(3):
            for vector in nullspace:
                if (solution ^ vector).bit_count() < solution.bit_count():
                    solution ^= vector
    indices = [i for i in range(len(masks)) if solution & (1 << i)]
    check = 0
    for i in indices:
        check ^= masks[i]
    if check != target:
        raise AssertionError("Toggle solution failed verification")
    return dict(
        solvable=True,
        indices=indices,
        clicks=len(indices),
        minimal=minimal,
        nullity=len(nullspace),
    )

