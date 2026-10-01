from arcengine import FrameData, GameAction, GameState

from src.agents import AVAILABLE_AGENTS
from src.agents.base import BaseAgent
from src.agents.random_agent import RandomAgent
from src.agents.stochastic_goose import StochasticGoose


class DummyAgent(BaseAgent):
    def choose_action(self, frames: list[FrameData], latest_frame: FrameData) -> GameAction:
        return GameAction.ACTION1


def test_base_agent_interface():
    agent = DummyAgent()
    frame = FrameData(state=GameState.NOT_FINISHED, levels_completed=0, available_actions=[1, 2])
    assert not agent.is_done([], frame)
    assert agent.choose_action([], frame) == GameAction.ACTION1

    win_frame = FrameData(state=GameState.WIN, levels_completed=1, available_actions=[1, 2])
    assert agent.is_done([], win_frame)

    over_frame = FrameData(state=GameState.GAME_OVER, levels_completed=0, available_actions=[1, 2])
    assert agent.is_done([], over_frame)


def test_random_agent_action_selection():
    agent = RandomAgent(seed=42)
    frame = FrameData(
        state=GameState.NOT_FINISHED,
        levels_completed=0,
        available_actions=[1, 2, 3],
    )
    action = agent.choose_action([], frame)
    assert action in (GameAction.ACTION1, GameAction.ACTION2, GameAction.ACTION3)


def test_random_agent_action6_coordinates():
    agent = RandomAgent(seed=42)
    frame = FrameData(
        state=GameState.NOT_FINISHED,
        levels_completed=0,
        available_actions=[6],
    )
    action = agent.choose_action([], frame)
    assert action == GameAction.ACTION6
    assert hasattr(action, "action_data")
    assert 0 <= action.action_data.x <= 63
    assert 0 <= action.action_data.y <= 63


def test_random_agent_registered():
    assert "random" in AVAILABLE_AGENTS
    assert AVAILABLE_AGENTS["random"] is RandomAgent


def test_stochastic_goose_initialization():
    agent = StochasticGoose()
    frame = FrameData(
        state=GameState.NOT_FINISHED,
        levels_completed=0,
        available_actions=[1, 2, 3, 4],
    )
    action = agent.choose_action([], frame)
    assert action in (
        GameAction.ACTION1,
        GameAction.ACTION2,
        GameAction.ACTION3,
        GameAction.ACTION4,
    )


def test_stochastic_goose_registered():
    assert "stochastic_goose" in AVAILABLE_AGENTS
    assert AVAILABLE_AGENTS["stochastic_goose"] is StochasticGoose
