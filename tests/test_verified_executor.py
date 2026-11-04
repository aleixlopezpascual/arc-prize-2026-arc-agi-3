from types import SimpleNamespace

from src.search.verified_executor import check_model, make_verified_executor


def test_check_model_matching():
    # Setup dummy transitions where action "INC" increments val by 1
    t1 = SimpleNamespace(
        before_frame=SimpleNamespace(level=1),
        after_frame=SimpleNamespace(level=1),
        action="INC",
        result={},
    )
    transitions = [t1]
    encode = lambda f: 0
    predict = lambda s, a: 0  # Matches
    res = check_model(predict, encode, transitions)
    assert res["checked"] == 1
    assert res["matches_observations"] is True
    assert len(res["mismatches"]) == 0


def test_check_model_mismatch():
    t1 = SimpleNamespace(
        before_frame=SimpleNamespace(level=1),
        after_frame=SimpleNamespace(level=1),
        action="INC",
        result={},
    )
    transitions = [t1]
    encode = lambda f: 0
    predict = lambda s, a: 1  # Mismatch (predicts 1, observed 0)
    res = check_model(predict, encode, transitions)
    assert res["checked"] == 1
    assert res["matches_observations"] is False
    assert len(res["mismatches"]) == 1


def test_follow_plan_stops_on_mismatch():
    frames = [{"val": 0}, {"val": 1}, {"val": 2}]
    idx = [0]
    def get_frame():
        return frames[idx[0]]
    def act(actions):
        idx[0] += len(actions)
        return {"executed": True, "executed_count": len(actions)}

    executor = make_verified_executor(get_frame, act)
    # Bad prediction for second action
    encode = lambda f: f["val"]
    predict = lambda s, a: s + 2  # Predicted 2, but actual next state is 1!
    res = executor(["R", "R"], predict, encode)
    assert res["stop"] == "prediction_mismatch"
    assert res["executed"] == 1


def test_follow_plan_success():
    frames = [{"val": 0}, {"val": 1}, {"val": 2}, {"val": 3}]
    idx = [0]
    def get_frame():
        return frames[idx[0]]
    def act(actions):
        idx[0] += len(actions)
        return {"executed": True, "executed_count": len(actions)}

    executor = make_verified_executor(get_frame, act)
    encode = lambda f: f["val"]
    predict = lambda s, a: s + 1
    res = executor(["R", "R"], predict, encode)
    assert res["stop"] == "plan_complete"
    assert res["executed"] == 2
