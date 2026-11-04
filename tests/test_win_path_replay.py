from src.utils.win_path_replay import extract_winning_segments


def test_extract_winning_segments_simple_win():
    # Recording: 3 actions on level 1, then level completed
    rec = [
        ("ACTION1", {}, 0, "PLAYING", False),
        ("ACTION4", {}, 0, "PLAYING", False),
        ("ACTION4", {}, 1, "PLAYING", True),
    ]
    segs = extract_winning_segments(rec, max_level=1)
    assert len(segs) == 1
    assert segs[1] == [
        ("ACTION1", {}),
        ("ACTION4", {}),
        ("ACTION4", {}),
    ]

def test_extract_winning_segments_discards_failed_attempts():
    # Recording: starts, hits RESET, dies with GAME_OVER, then clean 2 actions to win
    rec = [
        ("ACTION1", {}, 0, "PLAYING", False),
        ("RESET", {}, 0, "PLAYING", False),
        ("ACTION2", {}, 0, "PLAYING", False),
        ("ACTION3", {}, 0, "GAME_OVER", False),
        ("ACTION4", {}, 0, "PLAYING", False),
        ("ACTION4", {}, 1, "PLAYING", True),
    ]
    segs = extract_winning_segments(rec, max_level=1)
    assert len(segs) == 1
    # Only the last 2 actions after the death/reset are kept!
    assert segs[1] == [
        ("ACTION4", {}),
        ("ACTION4", {}),
    ]

def test_extract_winning_segments_multi_level():
    # Level 1 solved, then Level 2 fails once and solved on retry
    rec = [
        # Level 1
        ("ACTION1", {}, 0, "PLAYING", False),
        ("ACTION2", {}, 1, "PLAYING", True),
        # Level 2 failed attempt
        ("ACTION3", {}, 1, "PLAYING", False),
        ("RESET", {}, 1, "PLAYING", False),
        # Level 2 successful attempt
        ("ACTION4", {"row": 5, "col": 10}, 1, "PLAYING", False),
        ("ACTION5", {}, 2, "PLAYING", True),
    ]
    segs = extract_winning_segments(rec, max_level=2)
    assert len(segs) == 2
    assert segs[1] == [("ACTION1", {}), ("ACTION2", {})]
    assert segs[2] == [("ACTION4", {"row": 5, "col": 10}), ("ACTION5", {})]

def test_extract_winning_segments_empty():
    rec = [
        ("ACTION1", {}, 0, "PLAYING", False),
        ("ACTION2", {}, 0, "PLAYING", False),
    ]
    segs = extract_winning_segments(rec, max_level=0)
    assert segs == {}
