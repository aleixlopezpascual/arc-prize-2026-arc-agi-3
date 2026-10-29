from unittest.mock import patch

from arcengine import FrameData, GameState

from src.agents.openai_tool_agent import OpenAIToolAgent

PRINT_ONLY = "```python\nprint(candidate_goals())\n```"
ACT = "```python\naction(['DOWN'])\n```"
HINT = "already printed"


def _frame() -> FrameData:
    return FrameData(
        frame=[[[0, 1], [8, 0]]],
        available_actions=[1, 2, 3, 4],
        state=GameState.NOT_FINISHED,
        game_id="test_hint-1234",
        levels_completed=0,
    )


def _run(tmp_path, introspection_hint: bool) -> tuple[OpenAIToolAgent, list[str]]:
    agent = OpenAIToolAgent(
        api_key="dummy",
        cache_path=tmp_path / "c.json",
        introspection_hint=introspection_hint,
    )
    prompts: list[str] = []
    responses = iter([PRINT_ONLY, ACT])

    def fake_call(prompt: str) -> str:
        prompts.append(prompt)
        return next(responses)

    frame = _frame()
    with patch.object(agent, "_call_api", side_effect=fake_call):
        agent.choose_action([frame], frame)
    return agent, prompts


def test_hint_added_only_after_the_first_prompt_when_enabled(tmp_path):
    _, prompts = _run(tmp_path, introspection_hint=True)
    assert len(prompts) == 2
    assert HINT not in prompts[0]
    assert HINT in prompts[1]


def test_no_hint_when_disabled(tmp_path):
    _, prompts = _run(tmp_path, introspection_hint=False)
    assert all(HINT not in prompt for prompt in prompts)


def test_counters_track_api_calls_and_wasted_loops(tmp_path):
    agent, _ = _run(tmp_path, introspection_hint=False)
    assert agent.api_calls == 2
    assert agent.wasted_loops == 1
