import pytest
from src.perception.fable_core import (
    diff_cells,
    components8,
    small_far_changes,
    detect_budget,
    budget_alert,
    Ledger,
    build_level_log,
)

def test_diff_cells_and_components8():
    grid_a = [[0] * 10 for _ in range(10)]
    grid_b = [[0] * 10 for _ in range(10)]
    grid_b[2][2] = 1
    grid_b[2][3] = 1
    grid_b[8][8] = 2

    diffs = diff_cells(grid_a, grid_b)
    assert set(diffs) == {(2, 2), (2, 3), (8, 8)}

    comps = components8(diffs)
    assert len(comps) == 2
    comp_sizes = sorted(len(c) for c in comps)
    assert comp_sizes == [1, 2]

def test_small_far_changes_indicator_detection():
    before = [[0] * 64 for _ in range(64)]
    after = [[0] * 64 for _ in range(64)]

    # Main moving object in center
    for r in range(30, 35):
        for c in range(30, 35):
            before[r][c] = 3
    for r in range(30, 35):
        for c in range(31, 36):
            after[r][c] = 3

    # Small indicator patch far away in top-left legend (2x2 patch changes from color 1 to color 2)
    for r in range(5, 7):
        for c in range(5, 7):
            before[r][c] = 1
            after[r][c] = 2

    patches = small_far_changes(before, after)
    assert len(patches) == 1
    p = patches[0]
    assert p["box"] == (5, 5, 6, 6)
    assert p["size"] == 4

def test_detect_budget_and_alert():
    frames = []
    # Row 0 is a 64-column bar of color 5 shrinking from the right
    for step in range(10):
        grid = [[0] * 64 for _ in range(64)]
        bar_len = 40 - (step * 2)
        for c in range(bar_len):
            grid[0][c] = 5
        frames.append(grid)

    budget = detect_budget(frames)
    assert budget is not None
    assert budget["kind"] == "row"
    assert budget["index"] == 0
    assert budget["left"] == 22
    assert budget["rate"] == pytest.approx(2.0, abs=0.2)

    alert_text = budget_alert(budget, first_time=False)
    assert "Step budget" in alert_text
    assert "row 0" in alert_text

def test_ledger_feed_and_key_lines():
    led = Ledger(level=1)
    grid1 = [[0] * 64 for _ in range(64)]
    grid2 = [[0] * 64 for _ in range(64)]
    grid2[30][30] = 1

    events = led.feed("UP", {}, grid1, grid2)
    assert led.n_actions == 1
    assert led.keys["UP"]["changed"] == 1

    lines = led.key_lines()
    assert any("UP: pressed 1" in l for l in lines)

def test_build_level_log():
    led = Ledger(level=1)
    grid1 = [[0] * 64 for _ in range(64)]
    grid2 = [[0] * 64 for _ in range(64)]
    grid2[30][30] = 1
    led.feed("UP", {}, grid1, grid2)

    log_text = build_level_log(
        led,
        level_tokens=32000,
        valid_actions=["UP", "DOWN", "LEFT", "RIGHT"],
        budget_text="Low budget alert",
        earlier=[],
    )
    assert "LEVEL LOG" in log_text
    assert "level 1" in log_text
    assert "32000 generated tokens" in log_text
    assert "Low budget alert" in log_text
