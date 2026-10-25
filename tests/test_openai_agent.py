import json
from unittest.mock import MagicMock, patch
import pytest
from arcengine import FrameData, GameAction, GameState

from src.agents.openai_agent import OpenAIAgent, parse_action_response, grid_to_ascii


def test_grid_to_ascii():
    grid = [[0, 1], [8, 0]]
    ascii_repr = grid_to_ascii(grid)
    assert len(ascii_repr.splitlines()) == 2
    assert ascii_repr.splitlines()[0] == "Ww"
    assert ascii_repr.splitlines()[1] == "RW"


def test_parse_action_response():
    # Simple directional
    act, coords = parse_action_response("I should move up.\nACTION: UP", [1, 2, 3, 4])
    assert act == GameAction.ACTION1
    assert coords is None

    # Numbered action
    act2, coords2 = parse_action_response("ACTION2", [1, 2, 3])
    assert act2 == GameAction.ACTION2
    assert coords2 is None

    # Click with coordinates
    act3, coords3 = parse_action_response("CLICK(15, 25)", [1, 6])
    assert act3 == GameAction.ACTION6
    assert coords3 == (15, 25)

    # Fallback to first available action
    act4, _ = parse_action_response("INVALID_UNKNOWN_ACTION", [3, 4])
    assert act4 == GameAction.ACTION3


def test_openai_agent_choose_action():
    agent = OpenAIAgent(model="gpt-6-luna", api_key="dummy-key")
    frame = FrameData(
        frame=[[[0, 1], [8, 0]]],
        available_actions=[1, 2, 6],
        state=GameState.NOT_FINISHED,
        game_id="ls20-1234",
        levels_completed=0,
    )

    with patch.object(agent, "_call_api", return_value="ACTION: CLICK(5, 10)"):
        action = agent.choose_action([frame], frame)
        assert action == GameAction.ACTION6
        assert action.action_data.x == 5
        assert action.action_data.y == 10
        assert action.action_data.game_id == "ls20-1234"
