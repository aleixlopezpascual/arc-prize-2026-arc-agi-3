from src.agents.base import BaseAgent
from src.agents.openai_agent import OpenAIAgent
from src.agents.random_agent import RandomAgent
from src.agents.search_agent import PerceptionSearchAgent
from src.agents.stochastic_goose import StochasticGoose

AVAILABLE_AGENTS: dict[str, type[BaseAgent]] = {
    "openai": OpenAIAgent,
    "perception_search": PerceptionSearchAgent,
    "random": RandomAgent,
    "stochastic_goose": StochasticGoose,
}

__all__ = [
    "AVAILABLE_AGENTS",
    "BaseAgent",
    "OpenAIAgent",
    "PerceptionSearchAgent",
    "RandomAgent",
    "StochasticGoose",
]

