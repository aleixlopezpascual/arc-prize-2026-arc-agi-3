import pytest

from src.utils.adaptive_memory import normalize_notes, solved_evidence


def test_normalize_notes_bounds_and_reset():
    notes = {"game": {"rule": "doors open on yellow"}, "level": {"key": 1}, "_level": 1}
    # Stay on level 1
    norm = normalize_notes(notes, level=1)
    assert norm["level"] == {"key": 1}
    assert norm["game"]["rule"] == "doors open on yellow"

    # Advance to level 2 -> level notes cleared, game notes preserved
    norm2 = normalize_notes(norm, level=2)
    assert norm2["level"] == {}
    assert norm2["game"]["rule"] == "doors open on yellow"
    assert norm2["_level"] == 2


def test_normalize_notes_oversized_rejected():
    huge_notes = {"game": {"data": "x" * 20000}, "level": {}, "_level": 1}
    with pytest.raises(ValueError, match="16 KiB memory limit"):
        normalize_notes(huge_notes, level=1)


def test_solved_evidence():
    history = [
        {"frame": {"level": 1}, "action": "UP"},
        {"frame": {"level": 1}, "action": "RIGHT"},
        {"frame": {"level": 2}, "action": "DOWN"},
    ]
    ev = solved_evidence(history)
    assert len(ev) == 1
    assert ev[0]["level"] == 1
    assert ev[0]["recorded_actions"] == 2
    assert ev[0]["last_attempt_tail"] == ["UP", "RIGHT"]


def test_solved_evidence_reset_clears_tail():
    history = [
        {"frame": {"level": 1}, "action": "UP"},
        {"frame": {"level": 1}, "action": "RESET"},
        {"frame": {"level": 1}, "action": "LEFT"},
        {"frame": {"level": 2}, "action": "DOWN"},
    ]
    ev = solved_evidence(history)
    assert len(ev) == 1
    assert ev[0]["last_attempt_tail"] == ["LEFT"]
