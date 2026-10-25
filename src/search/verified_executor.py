"""Verified execution and world model verification against observed transitions."""
from __future__ import annotations

from typing import Any, Callable
from src.search.bounded_search import freeze_state


def check_model(
    predict: Callable[[Any, str], Any],
    encode: Callable[[Any], Any],
    transitions: list[Any],
    limit: int = 24,
) -> dict[str, Any]:
    """Replay observed, nonterminal transitions against an inferred simulator."""
    cases = []
    for t in transitions:
        result = getattr(t, "result", None) or {}
        before = getattr(t, "before_frame", None)
        after = getattr(t, "after_frame", None)
        action = getattr(t, "action", "")
        if (
            before is None
            or after is None
            or getattr(before, "level", None) != getattr(after, "level", None)
            or result.get("automatic")
            or action == "RESET"
            or any(result.get(k) for k in ("game_over", "level_completed", "run_complete", "done"))
        ):
            continue
        cases.append(t)
    selected = cases[-min(100, max(1, int(limit))):]
    mismatches, checked = [], 0
    for index, t in enumerate(selected):
        try:
            expected = predict(encode(t.before_frame), t.action)
            actual = encode(t.after_frame)
            checked += 1
            if freeze_state(expected) != freeze_state(actual):
                mismatches.append(
                    dict(
                        case=index,
                        action=t.action,
                        predicted=repr(expected)[:240],
                        observed=repr(actual)[:240],
                    )
                )
        except Exception as exc:
            mismatches.append(dict(case=index, action=t.action, error=str(exc)[:160]))
    return dict(
        checked=checked,
        selected=len(selected),
        available=len(cases),
        matches_observations=bool(selected) and not mismatches,
        mismatches=mismatches[:6],
    )


def make_verified_executor(
    get_frame: Callable[[], Any],
    act: Callable[[list[str]], dict[str, Any]],
) -> Callable:
    def follow_plan(
        plan: list[str],
        predict: Callable[[Any, str], Any],
        encode: Callable[[Any], Any],
        max_actions: int = 6,
    ) -> dict[str, Any]:
        """Execute at most six predicted steps, stopping at the first mismatch."""
        steps = 0
        cap = min(16, max(1, int(max_actions)))
        for a in plan:
            if steps >= cap:
                return dict(executed=steps, stop="chunk_limit")
            expected = predict(encode(get_frame()), a)
            result = act([a])
            if not result.get("executed"):
                return dict(executed=steps, stop="refused", result=result)
            steps += int(result.get("executed_count") or 1)
            if any(result.get(k) for k in ("game_over", "level_completed", "run_complete", "done")):
                return dict(executed=steps, stop="terminal", result=result)
            observed = encode(get_frame())
            if freeze_state(expected) != freeze_state(observed):
                return dict(
                    executed=steps,
                    stop="prediction_mismatch",
                    predicted=repr(expected)[:240],
                    observed=repr(observed)[:240],
                )
        return dict(executed=steps, stop="plan_complete")

    return follow_plan
