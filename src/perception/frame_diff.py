from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from src.perception.segmentation import segment_grid


def _bbox_area(bbox: Sequence[int]) -> int:
    return max(0, bbox[2] - bbox[0] + 1) * max(0, bbox[3] - bbox[1] + 1)


def _overlap_ratio(b1: Sequence[int], b2: Sequence[int]) -> float:
    inter_r = min(b1[2], b2[2]) - max(b1[0], b2[0]) + 1
    inter_c = min(b1[3], b2[3]) - max(b1[1], b2[1]) + 1
    if inter_r <= 0 or inter_c <= 0:
        return 0.0
    smaller = min(_bbox_area(b1), _bbox_area(b2))
    return (inter_r * inter_c) / smaller if smaller > 0 else 0.0


def compute_frame_diff(
    before_grid: Sequence[Sequence[int]] | np.ndarray,
    after_grid: Sequence[Sequence[int]] | np.ndarray,
    background_color: int | None = 0,
) -> dict:
    arr_b = np.asarray(before_grid)
    arr_a = np.asarray(after_grid)

    changed_cells = int(np.sum(arr_b != arr_a)) if arr_b.shape == arr_a.shape else 0

    nodes_before = segment_grid(arr_b, background_color=background_color)
    nodes_after = segment_grid(arr_a, background_color=background_color)

    moved: list[dict] = []
    rotated: list[dict] = []
    changed_color: list[dict] = []
    resized: list[dict] = []
    appeared: list[dict] = []
    disappeared: list[dict] = []

    used_before: set[int] = set()
    used_after: set[int] = set()

    # Match identical objects (unchanged)
    for bi, nb in enumerate(nodes_before):
        for ai, na in enumerate(nodes_after):
            if ai in used_after:
                continue
            if (
                nb["bbox"] == na["bbox"]
                and nb["pose_hash"] == na["pose_hash"]
                and nb["color"] == na["color"]
            ):
                used_before.add(bi)
                used_after.add(ai)
                break

    # Phase A: Changed color (same bbox and shape_hash, different color)
    for bi, nb in enumerate(nodes_before):
        if bi in used_before:
            continue
        for ai, na in enumerate(nodes_after):
            if ai in used_after:
                continue
            if (
                nb["bbox"] == na["bbox"]
                and nb["shape_hash"] == na["shape_hash"]
                and nb["color"] != na["color"]
            ):
                changed_color.append(
                    {
                        "bbox": nb["bbox"],
                        "before_color": nb["color"],
                        "after_color": na["color"],
                        "pixels": nb["pixels"],
                    }
                )
                used_before.add(bi)
                used_after.add(ai)
                break

    # Phase B: Resized (same color, bbox overlap >= 0.5)
    for bi, nb in enumerate(nodes_before):
        if bi in used_before:
            continue
        for ai, na in enumerate(nodes_after):
            if ai in used_after:
                continue
            if nb["color"] == na["color"] and _overlap_ratio(nb["bbox"], na["bbox"]) >= 0.5:
                resized.append(
                    {
                        "color": nb["color"],
                        "from_bbox": nb["bbox"],
                        "to_bbox": na["bbox"],
                        "before_pixels": nb["pixels"],
                        "after_pixels": na["pixels"],
                    }
                )
                used_before.add(bi)
                used_after.add(ai)
                break

    # Phase C: Moved or Rotated (same color and canonical_hash)
    for bi, nb in enumerate(nodes_before):
        if bi in used_before:
            continue
        for ai, na in enumerate(nodes_after):
            if ai in used_after:
                continue
            if nb["color"] == na["color"] and nb["canonical_hash"] == na["canonical_hash"]:
                if nb["rotation"] != na["rotation"]:
                    rotated.append(
                        {
                            "color": nb["color"],
                            "from_bbox": nb["bbox"],
                            "to_bbox": na["bbox"],
                            "from_rotation": nb["rotation"],
                            "to_rotation": na["rotation"],
                        }
                    )
                else:
                    moved.append(
                        {
                            "color": nb["color"],
                            "from_bbox": nb["bbox"],
                            "to_bbox": na["bbox"],
                            "pixels": nb["pixels"],
                        }
                    )
                used_before.add(bi)
                used_after.add(ai)
                break

    for bi, nb in enumerate(nodes_before):
        if bi not in used_before:
            disappeared.append(
                {
                    "color": nb["color"],
                    "bbox": nb["bbox"],
                    "pixels": nb["pixels"],
                }
            )

    for ai, na in enumerate(nodes_after):
        if ai not in used_after:
            appeared.append(
                {
                    "color": na["color"],
                    "bbox": na["bbox"],
                    "pixels": na["pixels"],
                }
            )

    return {
        "changed_cell_count": changed_cells,
        "moved": moved,
        "rotated": rotated,
        "appeared": appeared,
        "disappeared": disappeared,
        "changed_color": changed_color,
        "resized": resized,
    }
