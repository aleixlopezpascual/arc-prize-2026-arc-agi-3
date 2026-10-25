#!/usr/bin/env python3
"""Build Duck V17 submission package.

Combines:
1. Kaggle platform timeout armor (55m startup, 900s HTTP retry, warmup reset keepalive)
2. Candidate G adaptive primitives: solve_toggle, route, bounded_search, follow_plan, notes memory
3. Duck V12/V15/V16 core: candidate_clicks, candidate_goals, in-sandbox early stopping, Fable 30k, temp 0.6
"""
import json
import shutil
from pathlib import Path

V16_DIR = Path("submissions/duck_v16")
V17_DIR = Path("submissions/duck_v17")
V17_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Create kernel-metadata.json
# ---------------------------------------------------------------------------
metadata = {
    "id": "aleixlopez/arc-agi-3-duck-v17",
    "title": "ARC-AGI-3 Duck V17",
    "code_file": "notebook.ipynb",
    "language": "python",
    "kernel_type": "notebook",
    "is_private": True,
    "enable_gpu": True,
    "enable_tpu": False,
    "enable_internet": False,
    "keywords": ["gpu"],
    "dataset_sources": [
        "dfranzen/pennyroyal-v253",
        "dfranzen/taaf-kaggle-source-bundle-copy"
    ],
    "kernel_sources": [],
    "competition_sources": [
        "arc-prize-2026-arc-agi-3"
    ],
    "model_sources": [
        "dfranzen/albucino-qwen3-8-flash-next-drafter/Transformers/default/1",
        "dfranzen/intel-qwen3.8-flash-next-w4a16-autoround/Transformers/default/1"
    ],
    "docker_image": "gcr.io/kaggle-private-byod/python@sha256:57e612b484cf3df5026ee4dcc3cb176974b22b2bc0937fb1e16132a8be4cb13c",
    "machine_shape": "NvidiaRtxPro6000"
}
(V17_DIR / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2))
print("Wrote submissions/duck_v17/kernel-metadata.json")

# ---------------------------------------------------------------------------
# 2. Build apply_enhancements_v17.py
# ---------------------------------------------------------------------------
v16_script = (V16_DIR / "apply_enhancements_v16.py").read_text()

# Additional doc lines in prompts.py
v17_prompt_doc = """    "- `candidate_clicks(color=None, min_size=1, max_size=None, exclude_border=True)` returns candidate click targets with their `centroid` [row, col], `bbox`, and `color`.\\n"
    "- `candidate_goals(exclude_border=True, max_candidates=8)` returns candidate destination targets, sockets, and landmarks with their `centroid` [row, col] and `goal_score`.\\n"
    "- `solve_toggle(button_masks, target, n_cells=None)` solves binary XOR puzzles from measured independent button masks, returning verified button indices and minimality flag.\\n"
    "- `route(mask, start, goals, moves=None)` finds shortest paths on an explicit boolean mask; coordinates are (row, col), goals is a list of cells.\\n"
    "- `bounded_search(start, successors, is_goal, heuristic=None, max_nodes=40000, max_depth=200, seconds=3)` plans in your simulator.\\n"
    "- `notes['game']` and `notes['level']` are compact JSON dicts (<=16 KiB total) kept across tool calls; notes['level'] resets on level change.\\n"
    "- `follow_plan(actions, predict, encode, max_actions=6)` acts through the action tool, verifying each prediction and stopping at any mismatch.\\n" """

old_v16_prompt_doc = """    "- `candidate_clicks(color=None, min_size=1, max_size=None, exclude_border=True)` returns candidate click targets with their `centroid` [row, col], `bbox`, and `color`.\\n"
    "- `candidate_goals(exclude_border=True, max_candidates=8)` returns candidate destination targets, sockets, and landmarks with their `centroid` [row, col] and `goal_score`.\\n" """

v17_script = v16_script.replace(old_v16_prompt_doc, v17_prompt_doc)

# Adaptive tools code to inject in python_tool_sandbox.py
adaptive_helpers_code = '''
    def freeze_state(value):
        import math
        if isinstance(value, dict):
            pairs = [(freeze_state(k), freeze_state(v)) for k, v in value.items()]
            return ("dict", tuple(sorted(pairs, key=repr)))
        if isinstance(value, (set, frozenset)):
            return ("set", tuple(sorted((freeze_state(v) for v in value), key=repr)))
        if isinstance(value, (list, tuple)):
            return (type(value).__name__, tuple(freeze_state(v) for v in value))
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Search states must contain finite numbers")
        hash(value)
        return (type(value).__name__, value)

    def solve_toggle(button_masks, target, n_cells=None, max_nullity=18):
        masks = [int(x) for x in button_masks]
        target = int(target)
        if target < 0 or any(x < 0 for x in masks) or len(masks) > 256:
            raise ValueError("Use at most 256 nonnegative button masks and target")
        required = max([target.bit_length()] + [m.bit_length() for m in masks])
        n_cells = required if n_cells is None else int(n_cells)
        if not required <= n_cells <= 4096:
            raise ValueError("n_cells must cover all mask bits and be <=4096")
        basis, nullspace = {}, []
        for index, vector in enumerate(masks):
            combination = 1 << index
            while vector:
                pivot = vector.bit_length() - 1
                if pivot not in basis:
                    basis[pivot] = (vector, combination)
                    break
                row, row_combination = basis[pivot]
                vector ^= row
                combination ^= row_combination
            if not vector:
                nullspace.append(combination)
        residual, solution = target, 0
        while residual:
            pivot = residual.bit_length() - 1
            if pivot not in basis:
                return dict(solvable=False, indices=None, minimal=False, nullity=len(nullspace), clicks=0)
            row, combination = basis[pivot]
            residual ^= row
            solution ^= combination
        minimal = len(nullspace) <= min(18, max(0, int(max_nullity)))
        if minimal:
            current, best, last_gray = solution, solution, 0
            for i in range(1, 1 << len(nullspace)):
                gray = i ^ (i >> 1)
                current ^= nullspace[(gray ^ last_gray).bit_length() - 1]
                last_gray = gray
                if current.bit_count() < best.bit_count():
                    best = current
            solution = best
        else:
            for _ in range(3):
                for vector in nullspace:
                    if (solution ^ vector).bit_count() < solution.bit_count():
                        solution ^= vector
        indices = [i for i in range(len(masks)) if solution & (1 << i)]
        check = 0
        for i in indices:
            check ^= masks[i]
        if check != target:
            raise AssertionError("Toggle solution failed verification")
        return dict(solvable=True, indices=indices, clicks=len(indices), minimal=minimal, nullity=len(nullspace))

    def bounded_search(start, successors, is_goal, heuristic=None, max_nodes=40000, max_depth=200, seconds=3.0):
        import heapq, itertools, math, time
        max_nodes = min(200000, max(1, int(max_nodes)))
        max_depth = min(2000, max(0, int(max_depth)))
        deadline = time.monotonic() + min(10.0, float(seconds))
        h = heuristic if heuristic is not None else lambda _: 0.0
        key = freeze_state(start)
        sequence = itertools.count()
        root = (None, None)
        queue = [(float(h(start)), next(sequence), 0.0, 0, key, start, root)]
        best = {key: {0: 0.0}}
        expanded, generated, cut_depth = 0, 1, False
        while queue:
            if expanded >= max_nodes or time.monotonic() >= deadline:
                return dict(status="limit", actions=None, expanded=expanded, visited=len(best))
            _, _, cost, depth, key, state, path = heapq.heappop(queue)
            if cost != best.get(key, {}).get(depth):
                continue
            if is_goal(state):
                actions = []
                while path[0] is not None:
                    path, act = path
                    actions.append(act)
                actions.reverse()
                return dict(status="solved", actions=actions, cost=cost, expanded=expanded, visited=len(best))
            expanded += 1
            if depth >= max_depth:
                cut_depth = True
                continue
            for item in successors(state):
                if len(item) == 2:
                    act, nxt = item
                    step_cost = 1.0
                elif len(item) == 3:
                    act, nxt, step_cost = item
                    step_cost = float(step_cost)
                else:
                    raise ValueError("successors must yield (action, state[, cost])")
                nxt_key, nxt_cost, nxt_depth = freeze_state(nxt), cost + step_cost, depth + 1
                frontier = best.get(nxt_key, {})
                if any(d <= nxt_depth and c <= nxt_cost for d, c in frontier.items()):
                    continue
                estimate = float(h(nxt))
                if generated >= max_nodes:
                    return dict(status="limit", actions=None, expanded=expanded, visited=len(best))
                best[nxt_key] = {d: c for d, c in frontier.items() if not (d >= nxt_depth and c >= nxt_cost)}
                best[nxt_key][nxt_depth] = nxt_cost
                generated += 1
                heapq.heappush(queue, (nxt_cost + estimate, next(sequence), nxt_cost, nxt_depth, nxt_key, nxt, (path, act)))
        return dict(status="limit" if cut_depth else "exhausted", actions=None, expanded=expanded, visited=len(best))

    def route(mask, start, goals, moves=None):
        from collections import deque
        rows = tuple(tuple(bool(v) for v in row) for row in mask)
        height, width = len(rows), len(rows[0]) if rows else 0
        if not height or not width:
            return dict(status="exhausted", actions=None, cells=None)
        start = tuple(start)
        goals = {tuple(g) for g in goals}
        moves = moves or {"UP": (-1, 0), "DOWN": (1, 0), "LEFT": (0, -1), "RIGHT": (0, 1)}
        if not (0 <= start[0] < height and 0 <= start[1] < width and rows[start[0]][start[1]]):
            return dict(status="exhausted", actions=None, cells=None)
        queue, parents = deque([start]), {start: None}
        while queue:
            pos = queue.popleft()
            if pos in goals:
                actions, cells = [], [pos]
                while parents[pos] is not None:
                    pos, act = parents[pos]
                    actions.append(act)
                    cells.append(pos)
                return dict(status="solved", actions=actions[::-1], cells=cells[::-1], cost=len(actions))
            for act, (dr, dc) in moves.items():
                nxt = (pos[0] + dr, pos[1] + dc)
                if 0 <= nxt[0] < height and 0 <= nxt[1] < width and rows[nxt[0]][nxt[1]] and nxt not in parents:
                    parents[nxt] = (pos, act)
                    queue.append(nxt)
        return dict(status="exhausted", actions=None, cells=None)

    def normalize_notes(notes, level, max_bytes=16384):
        import json
        if not isinstance(notes, dict):
            return {"game": {}, "level": {}, "_level": level}
        try:
            encoded = json.dumps(notes, ensure_ascii=True, allow_nan=False)
            if len(encoded.encode("utf-8")) > max_bytes:
                return {"game": {}, "level": {}, "_level": level}
            result = json.loads(encoded)
            if not isinstance(result.get("game"), dict) or not isinstance(result.get("level"), dict):
                return {"game": {}, "level": {}, "_level": level}
            if result.get("_level") != level:
                result["level"] = {}
            result["_level"] = level
            return result
        except Exception:
            return {"game": {}, "level": {}, "_level": level}

    def check_model(predict, encode, transitions, limit=24):
        cases = []
        for t in transitions or []:
            res = getattr(t, "result", None) or {}
            bf = getattr(t, "before_frame", None)
            af = getattr(t, "after_frame", None)
            act = getattr(t, "action", "")
            if bf is None or af is None or getattr(bf, "level", None) != getattr(af, "level", None) or res.get("automatic") or act == "RESET":
                continue
            cases.append(t)
        selected = cases[-min(100, max(1, int(limit))):]
        mismatches, checked = [], 0
        for idx, t in enumerate(selected):
            try:
                exp = predict(encode(t.before_frame), t.action)
                obs = encode(t.after_frame)
                checked += 1
                if freeze_state(exp) != freeze_state(obs):
                    mismatches.append(dict(case=idx, action=t.action, predicted=repr(exp)[:240], observed=repr(obs)[:240]))
            except Exception as e:
                mismatches.append(dict(case=idx, action=t.action, error=str(e)[:160]))
        return dict(checked=checked, selected=len(selected), available=len(cases), matches_observations=bool(selected) and not mismatches, mismatches=mismatches[:6])

    def follow_plan(plan, predict, encode, max_actions=6):
        steps = 0
        cap = min(16, max(1, int(max_actions)))
        for a in plan:
            if steps >= cap:
                return dict(executed=steps, stop="chunk_limit")
            curr_f = runtime_globals.get("current_frame")
            expected = predict(encode(curr_f), a)
            res = action([a])
            if not res.get("executed"):
                return dict(executed=steps, stop="refused", result=res)
            steps += int(res.get("executed_count") or 1)
            if any(res.get(k) for k in ("game_over", "level_completed", "run_complete", "done")):
                return dict(executed=steps, stop="terminal", result=res)
            obs = encode(runtime_globals.get("current_frame"))
            if freeze_state(expected) != freeze_state(obs):
                return dict(executed=steps, stop="prediction_mismatch", predicted=repr(expected)[:240], observed=repr(obs)[:240])
        return dict(executed=steps, stop="plan_complete")
'''

# Insert adaptive helpers and runtime exports into apply_enhancements_v17.py
if "def solve_toggle" not in v17_script:
    # Inject helpers above candidate_goals
    v17_script = v17_script.replace("    def candidate_goals(", adaptive_helpers_code + "\n    def candidate_goals(", 1)
    
    # Expose in runtime_globals in _refresh_state
    old_tail = '            runtime_globals["candidate_goals"] = candidate_goals'
    new_tail = ('            runtime_globals["candidate_goals"] = candidate_goals\n'
                '            runtime_globals["solve_toggle"] = solve_toggle\n'
                '            runtime_globals["bounded_search"] = bounded_search\n'
                '            runtime_globals["route"] = route\n'
                '            runtime_globals["check_model"] = check_model\n'
                '            runtime_globals["follow_plan"] = follow_plan\n'
                '            cur_lvl = getattr(current_frame, "level", 1) if current_frame else 1\n'
                '            runtime_globals["notes"] = normalize_notes(state_payload.get("adaptive_notes"), cur_lvl)')
    v17_script = v17_script.replace(old_tail, new_tail, 1)

(V17_DIR / "apply_enhancements_v17.py").write_text(v17_script)
print("Wrote submissions/duck_v17/apply_enhancements_v17.py")

# ---------------------------------------------------------------------------
# 3. Assemble submissions/duck_v17/notebook.ipynb from duck_v16
# ---------------------------------------------------------------------------
v16_nb = json.loads((V16_DIR / "notebook.ipynb").read_text())

# Cell 0: Title Duck V17
v16_nb["cells"][0]["source"] = [
    l.replace("Duck V16", "Duck V17 (Adaptive Armor + 55min Startup Shield + Bounded Memory + Exact Solvers)")
    for l in v16_nb["cells"][0]["source"]
]

# Cell 3: %%writefile /kaggle/apply_enhancements_v17.py
v17_body = (V17_DIR / "apply_enhancements_v17.py").read_text()
v16_nb["cells"][3]["source"] = [
    "%%writefile /kaggle/apply_enhancements_v17.py\n"
] + [l + "\n" for l in v17_body.splitlines()[:-1]] + [
    v17_body.splitlines()[-1]
]

# Cell 5: Setup timeout armor & run apply_enhancements_v17.py
cell5_src = "".join(v16_nb["cells"][5]["source"])
cell5_src = cell5_src.replace("SERVER_STARTUP_TIMEOUT = 12 * 60", "SERVER_STARTUP_TIMEOUT = 55 * 60")
cell5_src = cell5_src.replace("apply_enhancements_v16.py", "apply_enhancements_v17.py")
v16_nb["cells"][5]["source"] = [l + "\n" for l in cell5_src.splitlines()[:-1]] + [cell5_src.splitlines()[-1]]

(V17_DIR / "notebook.ipynb").write_text(json.dumps(v16_nb, indent=1))
print("Successfully generated submissions/duck_v17/notebook.ipynb")
