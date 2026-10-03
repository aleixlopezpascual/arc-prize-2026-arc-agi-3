from arcengine import FrameData, GameAction, GameState

from src.agents import AVAILABLE_AGENTS
from src.agents.search_agent import PerceptionSearchAgent


def test_search_agent_registered():
    assert "perception_search" in AVAILABLE_AGENTS
    assert AVAILABLE_AGENTS["perception_search"] is PerceptionSearchAgent


def test_search_agent_action6_with_centroids():
    agent = PerceptionSearchAgent(seed=42)
    # Frame with ACTION6 available and a 5x5 grid containing a clickable dot at (1, 2)
    grid = [[0] * 5 for _ in range(5)]
    grid[1][2] = 3

    frame = FrameData(
        state=GameState.NOT_FINISHED,
        levels_completed=0,
        available_actions=[6],
        frame=[grid],
    )
    action = agent.choose_action([], frame)
    assert action == GameAction.ACTION6
    assert hasattr(action, "action_data")
    assert action.action_data.x == 1
    assert action.action_data.y == 2


def test_search_agent_simple_actions():
    agent = PerceptionSearchAgent(seed=42)
    frame = FrameData(
        state=GameState.NOT_FINISHED,
        levels_completed=0,
        available_actions=[1, 2],
        frame=[[[0, 0], [0, 0]]],
    )
    action = agent.choose_action([], frame)
    assert action in (GameAction.ACTION1, GameAction.ACTION2)
