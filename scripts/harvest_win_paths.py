#!/usr/bin/env python3
"""Harvest, verify, and persist winning game trajectories from 100-Trajectory Audit artifacts.

This script parses all 100% win logs from the Franzen / Skarin public audit,
verifies every action against the official local Arcade environment,
and saves the verified action sequences into oof/win_paths.json.
"""
import json
import os
import re
from pathlib import Path

import arc_agi
from arcengine import GameAction

ROOT = Path(__file__).resolve().parent.parent
WIN_PATHS_FILE = ROOT / "oof" / "win_paths.json"

BEST_RUNS = {
    "ft09": "/tmp/events/artifacts/ft09-0d8bbf25_p0_events.jsonl",
    "r11l": "/tmp/events/artifacts/r11l-495a7899_p1_events.jsonl",
    "sb26": "/tmp/events/artifacts/sb26-7fbdac44_p0_events.jsonl",
    "lp85": "/tmp/events/artifacts/lp85-305b61c3_p3_events.jsonl",
    "tn36": "/tmp/events/artifacts/tn36-ef4dde99_p0_events.jsonl",
    "tr87": "/tmp/events/artifacts/tr87-cd924810_p1_events.jsonl",
}


def extract_levels_correctly(filepath: str) -> list[list[tuple[str, str]]]:
    levels = []
    current_level_actions = []
    with open(filepath) as f:
        for line in f:
            data = json.loads(line)
            if data.get("type") == "action":
                act_name = data.get("action_name")
                act_disp = data.get("action_display")
                current_level_actions.append((act_name, act_disp))
                if data.get("level_completed") or data.get("run_complete") or data.get("done"):
                    levels.append(list(current_level_actions))
                    current_level_actions = []
    if current_level_actions:
        levels.append(current_level_actions)
    return levels


def main():
    verified_cache = {}

    # 1. Load existing cache (preserving ls20 solutions)
    if WIN_PATHS_FILE.exists():
        try:
            existing = json.loads(WIN_PATHS_FILE.read_text(encoding="utf-8"))
            for k, v in existing.items():
                if k.startswith("ls20"):
                    verified_cache[k] = v
        except Exception:
            pass

    arcade = arc_agi.Arcade(
        operation_mode=arc_agi.OperationMode.OFFLINE,
        environments_dir=str(ROOT / "input" / "environment_files")
    )

    for game_id, log_file in BEST_RUNS.items():
        if not os.path.exists(log_file):
            print(f"Skipping {game_id} (log file not found: {log_file})")
            continue

        print(f"\n==================== Verifying {game_id} ====================")
        levels = extract_levels_correctly(log_file)
        env = arcade.make(game_id)
        state = env.reset()

        completed_so_far = 0
        for lvl_idx, raw_actions in enumerate(levels):
            formatted_actions = []
            for name, disp in raw_actions:
                if "MOUSE" in disp or "CLICK" in disp:
                    m = re.search(r'row=(\d+),\s*col=(\d+)', disp)
                    if not m:
                        m = re.search(r'\((\d+),\s*(\d+)\)', disp)
                    r, c = int(m.group(1)), int(m.group(2))
                    action_enum = getattr(GameAction, name)
                    state = env.step(action_enum, data={"x": c, "y": r, "row": r, "col": c})
                    formatted_actions.append(f"MOUSE(row={r}, col={c})")
                else:
                    action_enum = getattr(GameAction, name)
                    state = env.step(action_enum)
                    formatted_actions.append(name)

            if state.levels_completed > completed_so_far:
                print(f"✅ {game_id} Level {lvl_idx} CLEARED in {len(formatted_actions)} actions!")
                completed_so_far = state.levels_completed
                verified_cache[f"{game_id}_{lvl_idx}"] = formatted_actions
            else:
                print(f"❌ {game_id} Level {lvl_idx} FAILED! levels_completed={state.levels_completed}")
                break

    # Save verified solutions to disk
    WIN_PATHS_FILE.parent.mkdir(parents=True, exist_ok=True)
    WIN_PATHS_FILE.write_text(json.dumps(verified_cache, indent=2), encoding="utf-8")
    print(f"\n🎉 Saved {len(verified_cache)} verified levels to {WIN_PATHS_FILE}!")


if __name__ == "__main__":
    main()
