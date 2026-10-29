import dataclasses

import pytest

from src.agents import OpenAIToolAgent, RandomAgent
from src.experiments.arms import ARMS, PILOT_GAMES, build_agent, validate_games


def test_baseline_arm_disables_win_path_cache(tmp_path):
    arm = ARMS["tool_baseline"]
    assert arm.use_win_cache is False
    agent = build_agent(arm, seed=3, workdir=tmp_path)
    assert isinstance(agent, OpenAIToolAgent)
    assert agent.cache_path == tmp_path / "win_paths.json"
    assert agent.cached_solutions == {}
    assert agent.seed == 3


def test_weak_arm_has_smaller_action_cap_than_baseline():
    assert ARMS["tool_weak"].max_actions_per_level < ARMS["tool_baseline"].max_actions_per_level


def test_random_arm_builds_random_agent(tmp_path):
    assert isinstance(build_agent(ARMS["random"], seed=1, workdir=tmp_path), RandomAgent)


def test_unknown_agent_key_raises(tmp_path):
    bad = dataclasses.replace(ARMS["random"], name="bad", agent="nope")
    with pytest.raises(ValueError):
        build_agent(bad, seed=0, workdir=tmp_path)


def test_validate_games_rejects_ls20():
    with pytest.raises(ValueError, match="ls20"):
        validate_games(["ar25", "ls20"])


def test_pilot_games_pass_validation():
    assert validate_games(list(PILOT_GAMES)) == list(PILOT_GAMES)
    assert len(PILOT_GAMES) == 8
