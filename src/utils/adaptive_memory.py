"""Bounded JSON memory and solved-level evidence extraction."""
from __future__ import annotations

import json
from typing import Any


def normalize_notes(
    notes: dict[str, Any],
    level: int,
    max_bytes: int = 16384,
) -> dict[str, Any]:
    """Bounded JSON memory; the level bucket clears only on level change."""
    if not isinstance(notes, dict):
        raise ValueError("notes must be a dict")
    encoded = json.dumps(notes, ensure_ascii=True, allow_nan=False)
    if len(encoded.encode("utf-8")) > max_bytes:
        raise ValueError("notes exceed the 16 KiB memory limit; compact old evidence")
    result = json.loads(encoded)
    if not isinstance(result.get("game"), dict) or not isinstance(result.get("level"), dict):
        raise ValueError("notes must retain dict buckets: game and level")
    if result.get("_level") != level:
        result["level"] = {}
    result["_level"] = level
    return result


def solved_evidence(history: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Extract attempt tails and action counts from solved levels in history."""
    records = []
    current = None
    count = 0
    tail = []
    for entry in history or []:
        frame = entry.get("frame") or {}
        level = frame.get("level")
        action = str(entry.get("action") or "")
        if current is None:
            current = level
        elif isinstance(level, int) and isinstance(current, int) and level > current:
            records.append(
                dict(
                    level=current,
                    recorded_actions=count,
                    last_attempt_tail=list(tail),
                )
            )
            current, count, tail = level, 0, []

        if action:
            count += 1
            if action.upper() == "RESET":
                tail = []
            else:
                tail.append(action)
                tail = tail[-12:]
    return records[-10:]

