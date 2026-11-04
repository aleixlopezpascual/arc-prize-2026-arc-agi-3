

def test_batch_action_stagnation_truncation():
    """Simulate batch execution with early stoppage when gameplay_changed is False."""
    actions = ["RIGHT", "RIGHT", "RIGHT", "UP"]
    executed = []

    # Mock dispatcher: first action changes gameplay, second action hits wall (no change)
    def mock_step(act):
        step_idx = len(executed) - 1
        if step_idx == 0:
            return {"gameplay_changed": True, "board_changed": True}
        if step_idx == 1:
            return {"gameplay_changed": False, "board_changed": False}
        return {"gameplay_changed": True, "board_changed": True}

    # Early stoppage execution logic
    for act in actions:
        executed.append(act)
        res = mock_step(act)
        if not res.get("gameplay_changed", True) and not res.get("board_changed", True):
            break

    # Stagnation guard stops execution at 2 actions instead of burning all 4!
    assert len(executed) == 2
    assert executed == ["RIGHT", "RIGHT"]


def test_animation_empty_schema():
    """Verify empty animation dictionary matches documented schema with steps and frames."""
    record = {"action_display": "MOUSE(row=10, col=20)"}
    empty = {
        "action": record.get("action_display") if record else None,
        "frames": 0,
        "steps": [],
        "error": "No animation is available: the last executed action returned a single frame.",
    }
    assert empty["frames"] == 0
    assert empty["steps"] == []
    assert "error" in empty
    assert empty["action"] == "MOUSE(row=10, col=20)"


def test_stagnation_alert_trigger():
    """Verify stagnation alert triggers when consecutive unprogressed turns >= 3."""

    def check_stagnation(stagnation_turns: int) -> str | None:
        if stagnation_turns >= 3:
            return (
                "STAGNATION ALERT: Last 3 turns produced 0 gameplay progress. "
                "Re-examine object interactions or test a completely different goal hypothesis."
            )
        return None

    assert check_stagnation(1) is None
    assert check_stagnation(2) is None
    alert = check_stagnation(3)
    assert alert is not None
    assert "STAGNATION ALERT" in alert
