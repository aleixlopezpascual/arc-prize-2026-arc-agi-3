from src.perception.centroids import extract_candidate_clicks


def test_extract_candidate_clicks_basic():
    # 10x10 grid with background 0, small 2x2 square at rows 2-3, cols 2-3 (color 1),
    # and a 1x1 dot at row 7, col 8 (color 2)
    grid = [[0] * 10 for _ in range(10)]
    grid[2][2] = 1
    grid[2][3] = 1
    grid[3][2] = 1
    grid[3][3] = 1
    grid[7][8] = 2

    candidates = extract_candidate_clicks(grid, background_color=0, max_candidates=5)
    assert len(candidates) >= 2
    # Dot (1 pixel) is more compact, should be first
    assert candidates[0] == (7, 8)
    # Square centroid: row = 2 or 3, col = 2 or 3
    assert candidates[1] in [(2, 2), (2, 3), (3, 2), (3, 3)]


def test_extract_candidate_clicks_filters_large_background():
    # 10x10 grid where 60% of cells are color 4 (massive background) and 1 dot of color 5
    grid = [[4 if r < 6 else 0 for _ in range(10)] for r in range(10)]
    grid[8][8] = 5

    candidates = extract_candidate_clicks(grid, background_color=0)
    assert len(candidates) >= 1
    # Dot must be present
    assert (8, 8) in candidates
    # The massive color 4 area (>40% of grid) should NOT dominate
    assert candidates[0] == (8, 8)


def test_extract_candidate_clicks_fallback():
    # Blank 8x8 grid
    grid = [[0] * 8 for _ in range(8)]
    candidates = extract_candidate_clicks(grid, background_color=0)
    assert candidates == [(4, 4)]
