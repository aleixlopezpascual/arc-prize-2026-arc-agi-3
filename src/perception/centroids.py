from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from src.perception.segmentation import segment_grid


def extract_candidate_clicks(
    grid: Sequence[Sequence[int]] | np.ndarray,
    background_color: int | None = 0,
    max_candidates: int = 8,
) -> list[tuple[int, int]]:
    arr = np.asarray(grid)
    if arr.ndim != 2 or arr.size == 0:
        return [(0, 0)]

    h, w = arr.shape
    total_pixels = h * w
    nodes = segment_grid(arr, background_color=background_color)

    # Filter out massive objects covering >= 40% of the entire grid
    valid_nodes = [n for n in nodes if n["pixels"] < 0.4 * total_pixels]

    if not valid_nodes:
        # Fallback to board center
        return [(h // 2, w // 2)]

    # Sort: smaller/more compact objects first (high probability of being tokens/buttons)
    valid_nodes.sort(key=lambda n: (n["pixels"], n["bbox"][0]))

    candidates: list[tuple[int, int]] = []
    seen = set()

    for node in valid_nodes:
        cells = node["cells"]
        # Integer centroid
        r_c = round(sum(r for r, _ in cells) / len(cells))
        c_c = round(sum(c for _, c in cells) / len(cells))
        # Clamp to grid bounds
        r_c = max(0, min(h - 1, r_c))
        c_c = max(0, min(w - 1, c_c))

        point = (r_c, c_c)
        if point not in seen:
            seen.add(point)
            candidates.append(point)
            if len(candidates) >= max_candidates:
                break

    if not candidates:
        candidates.append((h // 2, w // 2))

    return candidates
