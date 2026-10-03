from src.agents.base import BaseAgent
from src.search.action_selector import SearchAwareAgent


class SearchAgent(SearchAwareAgent, BaseAgent):
    def choose_action(self, frames, latest_frame):
        return None


def test_search_agent_integration():
    agent = SearchAgent(evaluator=None)
    assert hasattr(agent, "rank_branches")
    assert agent.rank_branches([{"changed_cell_count": 5}]) == 0
