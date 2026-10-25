import pytest
from src.search.bounded_search import freeze_state, bounded_search, route


def test_freeze_state():
    d = {"b": 2, "a": [1, {"x": 3}]}
    frozen = freeze_state(d)
    assert hash(frozen) is not None
    # Tuples and primitives
    assert freeze_state(42) == ("int", 42)
    assert freeze_state("test") == ("str", "test")


def test_bounded_search_simple():
    # Search from 0 to 5
    res = bounded_search(0, lambda s: [("INC", s + 1)], lambda s: s == 5)
    assert res["status"] == "solved"
    assert res["actions"] == ["INC"] * 5
    assert res["cost"] == 5.0


def test_bounded_search_limit():
    # Unreachable goal with low node limit
    res = bounded_search(0, lambda s: [("INC", s + 1)], lambda s: s == 100, max_nodes=10)
    assert res["status"] == "limit"
    assert res["actions"] is None


def test_route_simple_grid():
    # 3x3 open grid
    mask = [[True, True, True], [True, True, True], [True, True, True]]
    res = route(mask, (0, 0), [(2, 2)])
    assert res["status"] == "solved"
    assert res["cost"] == 4
    assert len(res["actions"]) == 4


def test_route_blocked_or_unreachable():
    # Blocked target
    mask = [[True, False], [True, False]]
    res = route(mask, (0, 0), [(0, 1)])
    assert res["status"] == "exhausted"
    assert res["actions"] is None
