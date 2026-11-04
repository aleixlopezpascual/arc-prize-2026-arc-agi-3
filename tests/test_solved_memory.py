from src.utils.solved_memory import SolvedMemoryManager


def test_solved_memory_lifecycle():
    mem = SolvedMemoryManager()
    assert mem.get_memory_payload() == []

    # Record Level 1 clear
    mem.record_level_cleared(level=1, actions_taken=18, winning_actions=["UP", "UP", "SPACE"])
    payload = mem.get_memory_payload()
    assert len(payload) == 1
    assert payload[0]["level"] == 1
    assert payload[0]["actions_taken"] == 18
    assert payload[0]["winning_actions"] == ["UP", "UP", "SPACE"]

    # Record Level 2 clear
    mem.record_level_cleared(level=2, actions_taken=25, winning_actions=["ACTION6(10, 12)", "SPACE"])
    payload = mem.get_memory_payload()
    assert len(payload) == 2
    assert payload[1]["level"] == 2

    # Reset for next game
    mem.reset()
    assert mem.get_memory_payload() == []

def test_solved_memory_defensive():
    mem = SolvedMemoryManager()
    # None or empty winning actions
    mem.record_level_cleared(level=1, actions_taken=5, winning_actions=None)
    payload = mem.get_memory_payload()
    assert payload[0]["winning_actions"] == []
