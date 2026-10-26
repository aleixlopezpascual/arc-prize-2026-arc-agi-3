from unittest.mock import patch
import pytest
from arcengine import FrameData, GameAction, GameState

from src.agents.openai_tool_agent import OpenAIToolAgent, extract_python_snippet


def test_extract_python_snippet():
    text = """I will find the path and act.
```python
path = route(mask, (0, 0), [(2, 2)])
action(["UP", "RIGHT"])
```
Done."""
    code = extract_python_snippet(text)
    assert 'action(["UP", "RIGHT"])' in code


def test_openai_tool_agent_executes_python_and_queues_actions():
    agent = OpenAIToolAgent(model="gpt-6-luna", api_key="dummy-key")
    frame = FrameData(
        frame=[[[0, 1], [8, 0]]],
        available_actions=[1, 2, 3, 4],
        state=GameState.NOT_FINISHED,
        game_id="ls20-1234",
        levels_completed=0,
    )

    llm_response = """
```python
# Move down then right
action(["DOWN", "RIGHT"])
```
"""
    with patch.object(agent, "_call_api", return_value=llm_response):
        # Step 1: LLM runs, queues DOWN and RIGHT, returns DOWN
        act1 = agent.choose_action([frame], frame)
        assert act1 == GameAction.ACTION2  # DOWN
        assert len(agent.action_queue) == 1

        # Step 2: Next step should pop RIGHT directly from queue without calling API!
        act2 = agent.choose_action([frame, frame], frame)
        assert act2 == GameAction.ACTION4  # RIGHT
        assert len(agent.action_queue) == 0


def test_openai_tool_agent_candidate_clicks_helper():
    agent = OpenAIToolAgent(model="gpt-6-luna", api_key="dummy-key")
    frame = FrameData(
        frame=[[[0, 8], [8, 0]]],
        available_actions=[1, 6],
        state=GameState.NOT_FINISHED,
        game_id="ls20-1234",
        levels_completed=0,
    )

    llm_response = """
```python
clicks = candidate_clicks(min_size=1)
if clicks:
    action([f"CLICK({clicks[0]['centroid'][0]}, {clicks[0]['centroid'][1]})"])
```
"""
    with patch.object(agent, "_call_api", return_value=llm_response):
        act = agent.choose_action([frame], frame)
        assert act == GameAction.ACTION6
        assert act.action_data is not None
