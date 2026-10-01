from __future__ import annotations

import hashlib
import re
from collections import OrderedDict
from collections.abc import Sequence
from typing import Any

import numpy as np

_DISPLAY_COORDS_RE = re.compile(
    r"^([A-Z0-9_]+)\(\s*(?:ROW\s*=\s*)?(-?\d+)\s*,\s*(?:COL\s*=\s*)?(-?\d+)\s*\)$"
)


def action_signature(action: Any) -> str:
    if isinstance(action, dict):
        name = str(action.get("action") or action.get("name") or "").strip().upper()
        row = action.get("row")
        col = action.get("col")
        if row is not None or col is not None:
            return f"{name}({row},{col})"
        return name

    text = " ".join(str(action or "").split()).upper()
    match = _DISPLAY_COORDS_RE.match(text)
    if match:
        return f"{match.group(1)}({match.group(2)},{match.group(3)})"
    return text


def compute_interior_hash(
    grid: Sequence[Sequence[int]] | np.ndarray, border_margin: int = 4
) -> str:
    arr = np.asarray(grid)
    if arr.ndim != 2 or arr.size == 0:
        return ""
    h, w = arr.shape
    if h <= border_margin * 2 or w <= border_margin * 2:
        interior = arr
    else:
        interior = arr[border_margin : h - border_margin, border_margin : w - border_margin]
    return hashlib.sha1(interior.tobytes()).hexdigest()[:16]


class NoopRepeatGuard:
    def __init__(self, max_states: int = 512, max_actions: int = 16) -> None:
        self.max_states = max_states
        self.max_actions = max_actions
        self.states: OrderedDict[str, OrderedDict[str, None]] = OrderedDict()
        self.level: int | None = None
        self.armed_slot: tuple[str, str] | None = None

    def note_level(self, level: int) -> None:
        if level != self.level:
            self.level = level
            self.states.clear()
            self.armed_slot = None

    def observe(self, state_hash: str, action: Any, gameplay_changed: bool) -> None:
        sig = action_signature(action)
        if not state_hash or not sig:
            return

        if not gameplay_changed:
            entry = self.states.get(state_hash)
            if entry is None:
                entry = OrderedDict()
                self.states[state_hash] = entry
                while len(self.states) > self.max_states:
                    self.states.popitem(last=False)
            entry[sig] = None
            while len(entry) > self.max_actions:
                entry.popitem(last=False)
        else:
            entry = self.states.get(state_hash)
            if entry is not None and sig in entry:
                del entry[sig]
                if not entry:
                    del self.states[state_hash]

    def should_block(self, state_hash: str, action: Any) -> bool:
        sig = action_signature(action)
        if not state_hash or not sig:
            return False

        # Check if already armed for override
        if self.armed_slot == (state_hash, sig):
            self.armed_slot = None
            return False

        entry = self.states.get(state_hash)
        if entry is not None and sig in entry:
            self.armed_slot = (state_hash, sig)
            return True

        self.armed_slot = None
        return False
