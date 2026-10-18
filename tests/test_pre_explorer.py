from src.perception.pre_explorer import (
    _GameFacts,
    build_manual,
    diff_summary,
    to_grid,
)


def test_to_grid_basic():
    data = [[0, 1], [2, 3]]
    grid = to_grid(data)
    assert grid == ((0, 1), (2, 3))


def test_diff_summary_no_change():
    grid = ((0, 0), (0, 0))
    assert diff_summary(grid, grid) == "no change"


def test_diff_summary_movement():
    # Background 0, single pixel 1 at (0, 0) moving to (1, 1)
    g1 = (
        (1, 0, 0),
        (0, 0, 0),
        (0, 0, 0),
    )
    g2 = (
        (0, 0, 0),
        (0, 1, 0),
        (0, 0, 0),
    )
    res = diff_summary(g1, g2)
    assert "moved" in res
    assert "dr=+1,dc=+1" in res


def test_build_manual_formatting():
    facts = _GameFacts()
    facts.probes.append(("ACTION1", "1 B-obj moved (dr=-1,dc=0)"))
    facts.probes.append(("ACTION5", "no change"))
    facts.click_tries = 16
    facts.click_hits = 2
    facts.click_examples = [(58, 19), (60, 20)]
    facts.click_rows = [58, 60]
    facts.click_cols = [19, 20]

    manual = build_manual("test_game", facts)
    assert "PRE-EXPLORATION REPORT" in manual
    assert "- UP: 1 B-obj moved" in manual
    assert "- SPACE: no change" in manual
    assert "Click probes (MOUSE): 2/16" in manual
    assert "(58,19)" in manual
