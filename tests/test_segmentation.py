from src.perception.segmentation import compute_object_signature, segment_grid


def test_segment_grid_basic_shapes():
    # 5x5 grid with a 2x2 square of color 1 and an L-shape of color 2
    grid = [
        [0, 0, 0, 0, 0],
        [0, 1, 1, 0, 0],
        [0, 1, 1, 0, 0],
        [0, 2, 0, 0, 0],
        [0, 2, 2, 0, 0],
    ]
    nodes = segment_grid(grid, background_color=0)
    assert len(nodes) == 2

    # Verify color 1 (2x2 square) has 4-fold rotational symmetry
    square = next(n for n in nodes if n["color"] == 1)
    assert square["pixels"] == 4
    assert square["rotational_symmetry"] == 4
    assert square["bbox"] == [1, 1, 2, 2]

    # Verify color 2 (L-shape) has 1-fold symmetry (asymmetric)
    l_shape = next(n for n in nodes if n["color"] == 2)
    assert l_shape["pixels"] == 3
    assert l_shape["rotational_symmetry"] == 1
    assert l_shape["bbox"] == [3, 1, 4, 2]


def test_segment_grid_rotation_invariance():
    # Corner L rotated 90 degrees must have identical canonical hash
    cells_original = {(0, 0), (0, 1), (1, 0)}  # Corner L
    cells_rotated = {(0, 0), (1, 0), (1, 1)}  # Rotated 90 deg
    sig1 = compute_object_signature(cells_original, color=3)
    sig2 = compute_object_signature(cells_rotated, color=3)

    assert sig1["canonical_hash"] == sig2["canonical_hash"]
    assert sig1["shape_hash"] == sig2["shape_hash"]


def test_segment_grid_empty_or_solid():
    nodes_empty = segment_grid([], background_color=0)
    assert nodes_empty == []

    solid = [[0, 0], [0, 0]]
    nodes_solid = segment_grid(solid, background_color=0)
    assert nodes_solid == []
