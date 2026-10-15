"""Perception primitives injected into the Python tool sandbox."""
from __future__ import annotations

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

