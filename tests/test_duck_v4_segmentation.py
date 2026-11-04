from src.perception.segmentation import segment_grid, segment_layer


def test_is_border_detection_outer_strip():
    # 10x10 grid with top row filled with 2 (border/HUD bar) and center containing a 2x2 1 object
    grid = [[0 for _ in range(10)] for _ in range(10)]
    for c in range(10):
        grid[0][c] = 2
    grid[4][4] = 1
    grid[4][5] = 1
    grid[5][4] = 1
    grid[5][5] = 1

    nodes = segment_grid(grid, background_color=0)
    border_node = next(n for n in nodes if n["color"] == 2)
    center_node = next(n for n in nodes if n["color"] == 1)

    assert border_node["is_border"] is True
    assert center_node["is_border"] is False
    assert border_node["centroid"][0] == 0
    assert center_node["centroid"] in ([4, 4], [4, 5], [5, 4], [5, 5])

def test_is_border_small_or_empty_grid():
    grid = [[1]]
    nodes = segment_grid(grid, background_color=0)
    assert len(nodes) == 1
    assert "is_border" in nodes[0]
    assert nodes[0]["centroid"] == [0, 0]

def test_segment_layer_compatibility():
    grid = [
        "BBBBBBBBBB",
        "..........",
        "..........",
        "....RR....",
        "....RR....",
        "..........",
        "..........",
        "..........",
        "..........",
        "..........",
    ]
    seg = segment_layer(grid, ".BR")
    nodes = seg["nodes"]
    border_node = next(n for n in nodes if n["color"] == "B")
    center_node = next(n for n in nodes if n["color"] == "R")
    assert border_node["is_border"] is True
    assert center_node["is_border"] is False
    assert "centroid" in border_node
    assert "centroid" in center_node
