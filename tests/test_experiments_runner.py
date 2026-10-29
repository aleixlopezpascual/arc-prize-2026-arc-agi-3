import dataclasses

import pytest

from src.evaluate import GameEvalSummary
from src.experiments.arms import ARMS
from src.experiments.records import load_records
from src.experiments.runner import resolve_games, run_arm


class FakeEvaluator:
    def __init__(self, fail_on: tuple[str, ...] = ()) -> None:
        self.max_actions_per_level = 0
        self.calls: list[tuple[str, int]] = []
        self.fail_on = set(fail_on)

    def run_game(self, agent, game_prefix):
        self.calls.append((game_prefix, self.max_actions_per_level))
        if game_prefix in self.fail_on:
            raise RuntimeError("boom")
        return GameEvalSummary(
            game_id=f"{game_prefix}-x", levels_completed=1, total_actions=7, score=12.5
        )


def test_run_arm_writes_one_record_per_game_and_seed(tmp_path):
    path = tmp_path / "r.jsonl"
    evaluator = FakeEvaluator()
    new = run_arm(ARMS["random"], ["g0", "g1"], [0, 1], path, evaluator)
    assert len(new) == 4
    assert len(load_records(path)) == 4
    assert {r.key for r in new} == {
        ("random", g, s) for g in ("g0", "g1") for s in (0, 1)
    }
    assert evaluator.max_actions_per_level == ARMS["random"].max_actions_per_level


def test_run_arm_resumes_and_skips_existing_runs(tmp_path):
    path = tmp_path / "r.jsonl"
    run_arm(ARMS["random"], ["g0", "g1"], [0], path, FakeEvaluator())
    evaluator = FakeEvaluator()
    new = run_arm(ARMS["random"], ["g0", "g1"], [0, 1], path, evaluator)
    assert [call[0] for call in evaluator.calls] == ["g0", "g1"]
    assert {r.seed for r in new} == {1}
    assert len(load_records(path)) == 4


def test_failed_run_is_recorded_with_error_and_not_retried(tmp_path):
    path = tmp_path / "r.jsonl"
    run_arm(ARMS["random"], ["g0", "g1"], [0], path, FakeEvaluator(fail_on=("g1",)))
    records = {r.game: r for r in load_records(path)}
    assert records["g0"].ok is True
    assert records["g1"].ok is False
    assert "RuntimeError: boom" in records["g1"].error
    evaluator = FakeEvaluator()
    run_arm(ARMS["random"], ["g0", "g1"], [0], path, evaluator)
    assert evaluator.calls == []


def test_resolve_games_rejects_ls20():
    with pytest.raises(ValueError, match="ls20"):
        resolve_games("ar25,ls20")


def test_resolve_games_splits_and_strips():
    assert resolve_games("ar25, cd82") == ["ar25", "cd82"]


class ApiFailingEvaluator(FakeEvaluator):
    def run_game(self, agent, game_prefix):
        agent.api_failures = 2
        return super().run_game(agent, game_prefix)


def test_run_with_api_failures_is_recorded_as_error(tmp_path):
    path = tmp_path / "r.jsonl"
    run_arm(ARMS["tool_baseline"], ["g0"], [0], path, ApiFailingEvaluator())
    record = load_records(path)[0]
    assert record.ok is False
    assert "2 API" in record.error


def test_changed_arm_config_refuses_to_resume(tmp_path):
    path = tmp_path / "r.jsonl"
    run_arm(ARMS["random"], ["g0"], [0], path, FakeEvaluator())
    changed = dataclasses.replace(ARMS["random"], max_actions_per_level=7)
    with pytest.raises(ValueError, match="config"):
        run_arm(changed, ["g0"], [0], path, FakeEvaluator())
