from src.agents.random_agent import RandomAgent
from src.evaluate import EvaluationRunner


def test_evaluation_runner_single_game():
    runner = EvaluationRunner(max_actions_per_level=10)
    agent = RandomAgent(seed=42)
    # Run against public game 'ls20'
    summary = runner.run_game(agent=agent, game_prefix="ls20")
    assert summary.game_id.startswith("ls20")
    assert summary.total_actions > 0
    assert summary.score >= 0.0
