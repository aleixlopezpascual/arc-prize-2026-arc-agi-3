from __future__ import annotations

import hashlib
from collections.abc import Sequence

import numpy as np


def _normalize_cells(cells: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    min_r = min(r for r, _ in cells)
    min_c = min(c for _, c in cells)
    return sorted((r - min_r, c - min_c) for r, c in cells)


def _rotate_cells_90(norm_cells: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    max_r = max(r for r, _ in norm_cells)
    return sorted((c, max_r - r) for r, c in norm_cells)


def _cells_hash(norm_cells: Sequence[tuple[int, int]], color_tag: str | int) -> str:
    payload = repr((color_tag, norm_cells)).encode()
    return hashlib.sha1(payload).hexdigest()[:16]


def compute_object_signature(
    cells: Sequence[tuple[int, int]] | set[tuple[int, int]],
    color: int,
) -> dict:
    if not cells:
        return {
            "canonical_hash": "",
            "rotation": 0,
            "rotational_symmetry": 1,
            "pose_hash": "",
            "shape_hash": "",
        }

    norm = _normalize_cells(list(cells))
    variants = [norm]
    for _ in range(3):
        variants.append(_rotate_cells_90(variants[-1]))

    hashes = [_cells_hash(v, color) for v in variants]
    shape_hashes = [_cells_hash(v, "__shape__") for v in variants]

    k = shape_hashes.index(min(shape_hashes))
    canonical = hashes[k]
    distinct = len(set(shape_hashes))
    symmetry = {1: 4, 2: 2, 4: 1}.get(distinct, 1)

    rotation = ((4 - k) % 4) * 90
    if symmetry == 4:
        rotation = 0
    elif symmetry == 2:
        rotation = rotation % 180

    canonical_shape_hash = shape_hashes[k]
    return {
        "canonical_hash": canonical,
        "rotation": rotation,
        "rotational_symmetry": symmetry,
        "pose_hash": hashes[0],
        "shape_hash": canonical_shape_hash,
    }


def segment_grid(
    grid: Sequence[Sequence[int]] | np.ndarray,
    background_color: int | None = 0,
) -> list[dict]:
    if grid is None or len(grid) == 0:
        return []

    arr = np.asarray(grid)
    if arr.ndim != 2 or arr.size == 0:
        return []

    h, w = arr.shape
    visited = np.zeros((h, w), dtype=bool)
    nodes: list[dict] = []
    node_id = 0

    for r in range(h):
        for c in range(w):
            val = int(arr[r, c])
            if visited[r, c] or (background_color is not None and val == background_color):
                continue

            # 4-connected flood-fill
            queue = [(r, c)]
            visited[r, c] = True
            cells: list[tuple[int, int]] = []

            while queue:
                curr_r, curr_c = queue.pop()
                cells.append((curr_r, curr_c))
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = curr_r + dr, curr_c + dc
                    if 0 <= nr < h and 0 <= nc < w and not visited[nr, nc] and arr[nr, nc] == val:
                        visited[nr, nc] = True
                        queue.append((nr, nc))

            min_r = min(cr for cr, _ in cells)
            max_r = max(cr for cr, _ in cells)
            min_c = min(cc for _, cc in cells)
            max_c = max(cc for _, cc in cells)

            sig = compute_object_signature(cells, val)
            nodes.append(
                {
                    "id": node_id,
                    "color": val,
                    "canonical_hash": sig["canonical_hash"],
                    "shape_hash": sig["shape_hash"],
                    "rotation": sig["rotation"],
                    "rotational_symmetry": sig["rotational_symmetry"],
                    "pose_hash": sig["pose_hash"],
                    "pixels": len(cells),
                    "bbox": [min_r, min_c, max_r, max_c],
                    "cells": cells,
                }
            )
            node_id += 1

    return nodes
