from src.perception.centroids import extract_candidate_clicks
from src.perception.frame_diff import compute_frame_diff
from src.perception.segmentation import compute_object_signature, segment_grid

__all__ = [
    "compute_frame_diff",
    "compute_object_signature",
    "extract_candidate_clicks",
    "segment_grid",
]
