from src.agents.base import BaseAgent
from src.agents.random_agent import RandomAgent
from src.agents.stochastic_goose import StochasticGoose

AVAILABLE_AGENTS: dict[str, type[BaseAgent]] = {
    "random": RandomAgent,
    "stochastic_goose": StochasticGoose,
}

__all__ = ["AVAILABLE_AGENTS", "BaseAgent", "RandomAgent", "StochasticGoose"]
