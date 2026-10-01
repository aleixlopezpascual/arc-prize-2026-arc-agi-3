from src.guards.noop_repeat_guard import (
    NoopRepeatGuard,
    action_signature,
    compute_interior_hash,
)


def test_action_signature_normalization():
    assert action_signature("action1") == "ACTION1"
    assert action_signature({"action": "ACTION6", "row": 10, "col": 20}) == "ACTION6(10,20)"
    assert action_signature("ACTION6(row=10, col=20)") == "ACTION6(10,20)"


def test_noop_repeat_guard_blocking_and_override():
    guard = NoopRepeatGuard()
    guard.note_level(1)

    state_hash = "abc123state"
    action = "ACTION1"

    # Initially not blocked
    assert not guard.should_block(state_hash, action)

    # Observe that this action caused zero interior change
    guard.observe(state_hash, action, gameplay_changed=False)

    # Next attempt in the same state should block
    assert guard.should_block(state_hash, action)

    # Immediate repetition (override): should_block returns False and allows execution
    assert not guard.should_block(state_hash, action)


def test_interior_hash_border_crop():
    # 6x6 grid where outer border has changing timer bar, interior 2x2 is identical
    grid1 = [
        [1, 1, 1, 1, 1, 1],
        [1, 0, 0, 0, 0, 1],
        [1, 0, 9, 9, 0, 1],
        [1, 0, 9, 9, 0, 1],
        [1, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 1, 1],
    ]
    # Same interior 9s, but border timer changed from 1 to 2
    grid2 = [
        [2, 2, 2, 2, 2, 2],
        [2, 0, 0, 0, 0, 2],
        [2, 0, 9, 9, 0, 2],
        [2, 0, 9, 9, 0, 2],
        [2, 0, 0, 0, 0, 2],
        [2, 2, 2, 2, 2, 2],
    ]
    # Cropping border of 2 gives identical interior hashes
    h1 = compute_interior_hash(grid1, border_margin=2)
    h2 = compute_interior_hash(grid2, border_margin=2)
    assert h1 == h2
