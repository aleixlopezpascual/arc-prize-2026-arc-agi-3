from unittest.mock import patch

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


def test_openai_tool_agent_executes_python_and_queues_actions(tmp_path):
    agent = OpenAIToolAgent(model="gpt-6-luna", api_key="dummy-key", cache_path=tmp_path / "empty.json")
    frame = FrameData(
        frame=[[[0, 1], [8, 0]]],
        available_actions=[1, 2, 3, 4],
        state=GameState.NOT_FINISHED,
        game_id="test_exec-1234",
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
        frame2 = FrameData(
            frame=[[[0, 0], [8, 1]]],
            available_actions=[1, 2, 3, 4],
            state=GameState.NOT_FINISHED,
            game_id="test_exec-1234",
            levels_completed=0,
        )
        act2 = agent.choose_action([frame, frame2], frame2)
        assert act2 == GameAction.ACTION4  # RIGHT
        assert len(agent.action_queue) == 0


def test_openai_tool_agent_candidate_clicks_helper(tmp_path):
    agent = OpenAIToolAgent(model="gpt-6-luna", api_key="dummy-key", cache_path=tmp_path / "empty.json")
    frame = FrameData(
        frame=[[[0, 8], [8, 0]]],
        available_actions=[1, 6],
        state=GameState.NOT_FINISHED,
        game_id="test_clicks-1234",
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


def test_openai_tool_agent_aborts_queue_on_noop(tmp_path):
    agent = OpenAIToolAgent(model="gpt-6-luna", api_key="dummy-key", cache_path=tmp_path / "empty.json")
    frame1 = FrameData(
        frame=[[[0, 1], [8, 0]]],
        available_actions=[1, 2, 3, 4],
        state=GameState.NOT_FINISHED,
        game_id="test_noop-1234",
        levels_completed=0,
    )
    # Queue 3 actions: DOWN, DOWN, RIGHT
    llm_response = '```python\naction(["DOWN", "DOWN", "RIGHT"])\n```'
    with patch.object(agent, "_call_api", return_value=llm_response):
        act1 = agent.choose_action([frame1], frame1)
        assert act1 == GameAction.ACTION2
        assert len(agent.action_queue) == 2

    # Frame 2 is identical to Frame 1 (no movement, hit wall!)
    frame2 = FrameData(
        frame=[[[0, 1], [8, 0]]],
        available_actions=[1, 2, 3, 4],
        state=GameState.NOT_FINISHED,
        game_id="test_noop-1234",
        levels_completed=0,
    )
    # The agent should notice the no-op, abort the queue, call LLM to replan, and execute UP
    replan_response = '```python\naction(["UP"])\n```'
    with patch.object(agent, "_call_api", return_value=replan_response):
        act2 = agent.choose_action([frame1, frame2], frame2)
        assert act2 == GameAction.ACTION1
        assert len(agent.action_queue) == 0


def test_openai_tool_agent_aborts_queue_on_level_change(tmp_path):
    agent = OpenAIToolAgent(model="gpt-6-luna", api_key="dummy-key", cache_path=tmp_path / "empty.json")
    frame1 = FrameData(
        frame=[[[0, 1], [8, 0]]],
        available_actions=[1, 2, 3, 4],
        state=GameState.NOT_FINISHED,
        game_id="test_level-1234",
        levels_completed=0,
    )
    llm_response = '```python\naction(["DOWN", "RIGHT", "RIGHT"])\n```'
    with patch.object(agent, "_call_api", return_value=llm_response):
        act1 = agent.choose_action([frame1], frame1)
        assert act1 == GameAction.ACTION2
        assert len(agent.action_queue) == 2

    # Frame 2 advances to level 1!
    frame2 = FrameData(
        frame=[[[5, 5], [5, 5]]],
        available_actions=[1, 2, 3, 4],
        state=GameState.NOT_FINISHED,
        game_id="test_level-1234",
        levels_completed=1,
    )
    new_level_response = '```python\naction(["UP"])\n```'
    with patch.object(agent, "_call_api", return_value=new_level_response):
        act2 = agent.choose_action([frame1, frame2], frame2)
        assert act2 == GameAction.ACTION1
        assert len(agent.action_queue) == 0


def test_openai_tool_agent_frame_diff_feedback(tmp_path):
    cache_file = tmp_path / "win_paths.json"
    agent = OpenAIToolAgent(model="gpt-6-luna", api_key="dummy-key", cache_path=cache_file)
    frame1 = FrameData(
        frame=[[[0, 1], [8, 0]]],
        available_actions=[1, 2, 3, 4],
        state=GameState.NOT_FINISHED,
        game_id="mock_diff-1234",
        levels_completed=0,
    )
    with patch.object(agent, "_call_api", return_value='```python\naction(["DOWN"])\n```'):
        agent.choose_action([frame1], frame1)

    frame2 = FrameData(
        frame=[[[0, 0], [8, 1]]],  # pixels changed
        available_actions=[1, 2, 3, 4],
        state=GameState.NOT_FINISHED,
        game_id="mock_diff-1234",
        levels_completed=0,
    )
    with patch.object(agent, "_call_api", return_value='```python\naction(["RIGHT"])\n```') as mock_call:
        agent.choose_action([frame1, frame2], frame2)
        called_prompt = mock_call.call_args[0][0]
        assert "modified" in called_prompt or "pixels" in called_prompt


def test_openai_tool_agent_captures_sandbox_stdout(tmp_path):
    cache_file = tmp_path / "win_paths.json"
    agent = OpenAIToolAgent(model="gpt-6-luna", api_key="dummy-key", cache_path=cache_file)
    frame1 = FrameData(
        frame=[[[0, 1], [8, 0]]],
        available_actions=[1, 2, 3, 4],
        state=GameState.NOT_FINISHED,
        game_id="mock_stdout-1234",
        levels_completed=0,
    )
    # Turn 1: model executes Python print
    with patch.object(agent, "_call_api", return_value='```python\nprint("FOUND_TARGET_AT_32_20")\naction(["UP"])\n```'):
        agent.choose_action([frame1], frame1)
        assert "FOUND_TARGET_AT_32_20" in agent.last_sandbox_stdout

    frame2 = FrameData(
        frame=[[[0, 0], [8, 1]]],
        available_actions=[1, 2, 3, 4],
        state=GameState.NOT_FINISHED,
        game_id="mock_stdout-1234",
        levels_completed=0,
    )
    # Turn 2: verify prompt includes the captured output from Turn 1
    with patch.object(agent, "_call_api", return_value='```python\naction(["RIGHT"])\n```') as mock_call:
        agent.choose_action([frame1, frame2], frame2)
        called_prompt = mock_call.call_args[0][0]
        assert "FOUND_TARGET_AT_32_20" in called_prompt


def test_openai_tool_agent_route_to_helper():
    agent = OpenAIToolAgent(model="gpt-6-luna", api_key="dummy-key")
    # 3x3 open grid of color 1
    frame = FrameData(
        frame=[[[1, 1, 1], [1, 1, 1], [1, 1, 1]]],
        available_actions=[1, 2, 3, 4],
        state=GameState.NOT_FINISHED,
        game_id="custom-game-1234",
        levels_completed=0,
    )
    llm_response = """
```python
route_to((2, 2), start=(0, 0))
```
"""
    with patch.object(agent, "_call_api", return_value=llm_response):
        act = agent.choose_action([frame], frame)
        assert len(agent.action_queue) == 3
        assert act in (GameAction.ACTION2, GameAction.ACTION4)


def test_openai_tool_agent_detects_step_size(tmp_path):
    cache_file = tmp_path / "win_paths.json"
    agent = OpenAIToolAgent(model="gpt-6-luna", api_key="dummy-key", cache_path=cache_file)
    # Frame 1: player at row 45
    frame1 = FrameData(
        frame=[[[0]*64 for _ in range(64)]],
        available_actions=[1, 2, 3, 4],
        state=GameState.NOT_FINISHED,
        game_id="mock_step-1234",
        levels_completed=0,
    )
    frame1.frame[0][45][34] = 12

    with patch.object(agent, "_call_api", return_value='```python\naction(["UP"])\n```'):
        agent.choose_action([frame1], frame1)

    # Frame 2: player moved by 5 pixels to row 40
    frame2 = FrameData(
        frame=[[[0]*64 for _ in range(64)]],
        available_actions=[1, 2, 3, 4],
        state=GameState.NOT_FINISHED,
        game_id="mock_step-1234",
        levels_completed=0,
    )
    frame2.frame[0][40][34] = 12

    with patch.object(agent, "_call_api", return_value='```python\naction(["RIGHT"])\n```'):
        agent.choose_action([frame1, frame2], frame2)
        assert agent.detected_step_size == 5


def test_openai_tool_agent_win_path_cache(tmp_path):
    import json
    cache_file = tmp_path / "win_paths.json"
    cache_file.write_text(json.dumps({
        "test_ls20_0": ["ACTION1", "ACTION4"]
    }))

    agent = OpenAIToolAgent(model="gpt-6-luna", api_key="dummy-key", cache_path=cache_file)
    frame = FrameData(
        frame=[[[0, 1], [8, 0]]],
        available_actions=[1, 4],
        state=GameState.NOT_FINISHED,
        game_id="test_ls20-1234",
        levels_completed=0,
    )

    # Agent should immediately load ACTION1 and ACTION4 from cache without calling LLM
    with patch.object(agent, "_call_api", side_effect=Exception("Should not call API when cache hits")):
        act1 = agent.choose_action([frame], frame)
        assert act1 == GameAction.ACTION1
        assert len(agent.action_queue) == 1






