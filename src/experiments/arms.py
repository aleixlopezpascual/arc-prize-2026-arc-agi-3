from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from src.agents import BaseAgent, OpenAIToolAgent, RandomAgent

PILOT_GAMES: tuple[str, ...] = (
    "ar25",
    "cd82",
    "dc22",
    "ft09",
    "lp85",
    "sb26",
    "tr87",
    "vc33",
)
EXCLUDED_GAME_PREFIXES: tuple[str, ...] = ("ls20",)


@dataclass(frozen=True)
class Arm:
    name: str
    agent: str  # "random" or "openai_tool"
    model: str = "gpt-6-luna"
    max_actions_per_level: int = 400
    use_win_cache: bool = False
    temperature: float | None = None
    introspection_hint: bool = False


ARMS: dict[str, Arm] = {
    arm.name: arm
    for arm in (
        Arm("random", "random"),
        Arm("tool_baseline", "openai_tool", max_actions_per_level=100),
        Arm("tool_weak", "openai_tool", max_actions_per_level=5),
        Arm("tool_hint", "openai_tool", max_actions_per_level=100, introspection_hint=True),
    )
}


def build_agent(arm: Arm, seed: int, workdir: Path) -> BaseAgent:
    if arm.agent == "random":
        return RandomAgent(seed=seed)
    if arm.agent == "openai_tool":
        cache_path = None if arm.use_win_cache else workdir / "win_paths.json"
        return OpenAIToolAgent(
            model=arm.model,
            cache_path=cache_path,
            seed=seed,
            temperature=arm.temperature,
            introspection_hint=arm.introspection_hint,
        )
    raise ValueError(f"Unknown agent key '{arm.agent}' for arm '{arm.name}'")


def validate_games(games: Sequence[str]) -> list[str]:
    for game in games:
        if game.startswith(EXCLUDED_GAME_PREFIXES):
            raise ValueError(
                f"Game '{game}' is excluded from comparisons "
                "(ls20 is covered by the hardcoded win-path cache)"
            )
    return list(games)
