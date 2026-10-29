import dataclasses
import random

from src.evaluate import GameEvalSummary
from src.experiments.arms import ARMS, PILOT_GAMES
from src.experiments.records import load_records
from src.experiments.runner import run_arm
from src.experiments.stats import verdict


class CapDependentEvaluator:
    """Score grows with the action cap; noise depends only on (game, seed)."""

    def __init__(self) -> None:
        self.max_actions_per_level = 0

    def run_game(self, agent, game_prefix):
        noise = random.Random(f"{game_prefix}-{agent.seed}").gauss(0.0, 2.0)
        score = max(0.0, min(self.max_actions_per_level, 50) * 0.8 + noise)
        return GameEvalSummary(game_id=game_prefix, levels_completed=1, total_actions=5, score=score)


def _run_all(tmp_path):
    path = tmp_path / "r.jsonl"
    evaluator = CapDependentEvaluator()
    copy_arm = dataclasses.replace(ARMS["tool_baseline"], name="tool_baseline_copy")
    for arm in (ARMS["tool_baseline"], copy_arm, ARMS["tool_weak"]):
        run_arm(arm, list(PILOT_GAMES), [0, 1, 2], path, evaluator)
    return load_records(path)


def test_weakened_arm_is_identified_as_worse(tmp_path):
    records = _run_all(tmp_path)
    assert verdict(records, "tool_baseline", "tool_weak").label == "worse"
    assert verdict(records, "tool_weak", "tool_baseline").label == "better"


def test_identical_arms_report_no_difference(tmp_path):
    records = _run_all(tmp_path)
    assert verdict(records, "tool_baseline", "tool_baseline_copy").label == "no difference"
