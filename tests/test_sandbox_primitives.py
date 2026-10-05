import pytest
from src.perception.sandbox_primitives import candidate_clicks, object_at

def test_candidate_clicks_filtering():
    nodes = [
        {"id": 0, "color": "B", "pixels": 10, "centroid": [0, 5], "bbox": [0, 0, 0, 9], "is_border": True},
        {"id": 1, "color": "R", "pixels": 4, "centroid": [5, 5], "bbox": [4, 4, 5, 5], "is_border": False},
        {"id": 2, "color": "G", "pixels": 1, "centroid": [2, 2], "bbox": [2, 2, 2, 2], "is_border": False},
    ]
    # By default, exclude_border drops B
    targets = candidate_clicks(nodes)
    assert len(targets) == 2
    assert targets[0]["id"] == 1
    assert targets[1]["id"] == 2

    # Filter by color
    r_targets = candidate_clicks(nodes, color="R")
    assert len(r_targets) == 1
    assert r_targets[0]["color"] == "R"

    # Filter by min_size
    large_targets = candidate_clicks(nodes, min_size=2)
    assert len(large_targets) == 1
    assert large_targets[0]["pixels"] == 4

def test_object_at_lookup():
    nodes = [
        {"id": 1, "color": "R", "pixels": 4, "bbox": [4, 4, 5, 5], "is_border": False},
    ]
    assert object_at(nodes, 4, 4)["id"] == 1
    assert object_at(nodes, 5, 5)["id"] == 1
    assert object_at(nodes, 6, 6) is None
    assert object_at(nodes, -1, 0) is None

def test_primitives_empty_or_none():
    assert candidate_clicks(None) == []
    assert candidate_clicks([]) == []
    assert object_at(None, 0, 0) is None
    assert object_at([], 0, 0) is None
