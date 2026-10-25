import pytest
from src.perception.sandbox_primitives import solve_toggle
from src.search.bounded_search import freeze_state, bounded_search, route
from src.utils.adaptive_memory import normalize_notes, solved_evidence
from src.search.verified_executor import check_model, make_verified_executor


def test_v17_component_integration():
    # 1. Test solve_toggle
    # Button 0 -> 1, Button 1 -> 2, Button 2 -> 4
    toggle_sol = solve_toggle([1, 2, 4], target=5)
    assert toggle_sol["solvable"] is True
    assert set(toggle_sol["indices"]) == {0, 2}
    assert toggle_sol["clicks"] == 2

    # 2. Test bounded_search
    search_res = bounded_search(
        start=(0, 0),
        successors=lambda s: [("R", (s[0], s[1] + 1)), ("D", (s[0] + 1, s[1]))],
        is_goal=lambda s: s == (2, 2),
    )
    assert search_res["status"] == "solved"
    assert search_res["cost"] == 4.0
    assert len(search_res["actions"]) == 4

    # 3. Test route
    mask = [[True, True], [False, True]]
    route_res = route(mask, (0, 0), [(1, 1)])
    assert route_res["status"] == "solved"
    assert route_res["actions"] == ["RIGHT", "DOWN"]

    # 4. Test normalize_notes
    notes = {"game": {"rule": "avoid red"}, "level": {"doors": 2}, "_level": 1}
    updated = normalize_notes(notes, level=2)
    assert updated["game"] == {"rule": "avoid red"}
    assert updated["level"] == {}
    assert updated["_level"] == 2

    # 5. Test follow_plan with make_verified_executor
    frames = [{"step": 0}, {"step": 1}]
    idx = [0]
    executor = make_verified_executor(
        lambda: frames[idx[0]],
        lambda acts: (idx.__setitem__(0, idx[0] + len(acts)) or {"executed": True, "executed_count": len(acts)})
    )
    plan_res = executor(["ACT"], lambda s, a: {"step": s["step"] + 1}, lambda f: f)
    assert plan_res["stop"] == "plan_complete"
    assert plan_res["executed"] == 1
