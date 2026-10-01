import pytest

from src.metrics import (
    GameScore,
    LevelScore,
    compute_competition_score,
    compute_game_score,
    compute_level_score,
)


def test_level_score_not_completed():
    assert compute_level_score(baseline_actions=50, actions_taken=50, completed=False) == 0.0
    assert compute_level_score(baseline_actions=50, actions_taken=10, completed=False) == 0.0


def test_level_score_perfect_efficiency():
    score = compute_level_score(baseline_actions=40, actions_taken=40, completed=True)
    assert score == pytest.approx(100.0)


def test_level_score_suboptimal_efficiency():
    # 2x actions taken -> 25%
    score = compute_level_score(baseline_actions=20, actions_taken=40, completed=True)
    assert score == pytest.approx(25.0)

    # 4x actions taken -> 6.25%
    score = compute_level_score(baseline_actions=20, actions_taken=80, completed=True)
    assert score == pytest.approx(6.25)


def test_level_score_super_human_efficiency():
    # 0.5x actions taken -> raw 400%, capped at 115.0
    score = compute_level_score(baseline_actions=40, actions_taken=20, completed=True)
    assert score == 115.0


def test_level_score_zero_guards():
    assert compute_level_score(baseline_actions=0, actions_taken=10, completed=True) == 0.0
    assert compute_level_score(baseline_actions=10, actions_taken=0, completed=True) == 0.0
    assert compute_level_score(baseline_actions=0, actions_taken=0, completed=True) == 0.0


def test_game_score_multi_level_weighting():
    # 2 levels: level 1 (weight 1), level 2 (weight 2)
    # Level 1 completed at 100%, Level 2 not completed (0%)
    # Weighted average: (100 * 1 + 0 * 2) / (1 + 2) = 100 / 3 = 33.333%
    levels = [
        (30, 30, True),
        (50, 80, False),
    ]
    score = compute_game_score(levels)
    assert score == pytest.approx(100.0 / 3.0)

    # Level 1 not completed (0%), Level 2 completed at 100%
    # Weighted average: (0 * 1 + 100 * 2) / (1 + 2) = 200 / 3 = 66.666%
    levels_rev = [
        (30, 60, False),
        (50, 50, True),
    ]
    score_rev = compute_game_score(levels_rev)
    assert score_rev == pytest.approx(200.0 / 3.0)


def test_game_score_cap_at_100():
    # Even if individual levels get 115.0, overall game score is capped at max possible completion (100.0)
    levels = [
        (100, 10, True),  # 115.0 * 1
        (100, 10, True),  # 115.0 * 2
    ]
    score = compute_game_score(levels)
    assert score <= 100.0
    assert score == pytest.approx(100.0)


def test_game_score_empty():
    assert compute_game_score([]) == 0.0


def test_dataclasses_game_score():
    game = GameScore(
        game_id="game_01",
        levels=[
            LevelScore(level_index=1, baseline_actions=20, actions_taken=20, completed=True),
            LevelScore(level_index=2, baseline_actions=40, actions_taken=80, completed=True),
        ],
    )
    assert game.levels_completed == 2
    assert game.total_actions == 100
    # Level 1 score: 100.0, weight 1 -> 100
    # Level 2 score: 25.0, weight 2 -> 50
    # Total: 150 / 3 = 50.0
    assert game.score == pytest.approx(50.0)


def test_competition_score():
    scores = [50.0, 100.0, 25.0, 0.0]
    assert compute_competition_score(scores) == pytest.approx(43.75)
    assert compute_competition_score({"g1": 50.0, "g2": 100.0}) == pytest.approx(75.0)
    assert compute_competition_score([]) == 0.0
