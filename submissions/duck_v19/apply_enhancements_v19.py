import sys
from pathlib import Path

src_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")

# ---------------------------------------------------------------------------
# 0. Write fable_layer_core.py
# ---------------------------------------------------------------------------
fable_core_file = src_root / "ARC3-Inference/inference/agent/fable_layer_core.py"
FABLE_CORE_SRC = 'r"""Fable layer, core (pure functions, standard library only).\n\nWhat strong runs do that ours does not, turned into things the harness can compute from the recorded frames\n(no model call, nothing written by the model):\n\n  * watch the legend / tray / counter every turn and note which action changed it   -> small_far_changes, Ledger.feed\n  * keep per-key notes of what each control did, with the state it was pressed in    -> Ledger.key_lines\n  * remember what the previous levels taught (the keys\' effects, the clearing run)  -> Ledger.digest_lines\n  * record the step budget early and warn when little is left                        -> detect_budget, budget_alert\n\nThe text goes into the agent\'s context only in two places: one short line per turn when an indicator patch changed or the\nbudget runs low, and one pinned LEVEL LOG when a level has taken a long time (see fable_layer_patch.py). Everything is\nconservative: a detector that is unsure says nothing.\n\nFrames are 2-D integer grids (rows of ints 0-15). History entries are (action_name, result_dict, grid_after) in order.\n"""\nfrom __future__ import annotations\n\nfrom collections import Counter\n\nLETTERS = "WwgGcBMPRbSYOrNp"\nCOLOR_NAMES = {\n    "W": "white", "w": "light gray", "g": "gray", "G": "dark gray", "c": "charcoal", "B": "black", "M": "magenta", "P": "pink",\n    "R": "red", "b": "blue", "S": "sky blue", "Y": "yellow", "O": "orange", "r": "dark red", "N": "light green", "p": "purple",\n}\nBORDER = 4  # the harness treats changes within 4 cells of the grid edge as "edge only" (timer bars)\n\n\ndef letter(v):\n    try:\n        return LETTERS[int(v)]\n    except (IndexError, ValueError, TypeError):\n        return "?"\n\n\ndef key_of(action):\n    """\'MOUSE(row=3, col=4)\' -> \'MOUSE\'; \'UP\' -> \'UP\'; \'\' -> \'\'."""\n    a = str(action or "").strip()\n    return a.split("(")[0].strip().upper()\n\n\ndef diff_cells(a, b):\n    out = []\n    for r, (ra, rb) in enumerate(zip(a, b)):\n        if ra == rb:\n            continue\n        for c, (va, vb) in enumerate(zip(ra, rb)):\n            if va != vb:\n                out.append((r, c))\n    return out\n\n\ndef inner_changed(cells, rows=64, cols=64):\n    return sum(1 for (r, c) in cells if BORDER <= r < rows - BORDER and BORDER <= c < cols - BORDER)\n\n\ndef components8(cells):\n    """8-connected components of a set of (r, c); returns a list of sorted lists."""\n    left = set(cells)\n    comps = []\n    while left:\n        seed = left.pop()\n        stack = [seed]\n        comp = [seed]\n        while stack:\n            r, c = stack.pop()\n            for dr in (-1, 0, 1):\n                for dc in (-1, 0, 1):\n                    n = (r + dr, c + dc)\n                    if n in left:\n                        left.remove(n)\n                        stack.append(n)\n                        comp.append(n)\n        comps.append(sorted(comp))\n    return comps\n\n\ndef bbox_of(cells):\n    rs = [p[0] for p in cells]\n    cs = [p[1] for p in cells]\n    return (min(rs), min(cs), max(rs), max(cs))\n\n\ndef bbox_gap(b1, b2):\n    """Chebyshev gap between two boxes (0 when they touch or overlap)."""\n    dr = max(b2[0] - b1[2], b1[0] - b2[2], 0)\n    dc = max(b2[1] - b1[3], b1[1] - b2[3], 0)\n    return max(dr, dc)\n\n\ndef _run_len(grid, r, c, dr, dc, value):\n    """Number of consecutive cells equal to `value` starting next to (r, c) in direction (dr, dc)."""\n    n = 0\n    r += dr\n    c += dc\n    while 0 <= r < len(grid) and 0 <= c < len(grid[0]) and grid[r][c] == value:\n        n += 1\n        r += dr\n        c += dc\n    return n\n\n\ndef _bar_like(before, after, comp, box):\n    """A budget / timer bar changes a few cells at the end of a long straight run of ONE colour.\n\n    The run is measured in the grid where that colour is present (the colour the cells had before, in the grid before;\n    the colour they have after, in the grid after), so a dashed beam or a legend icon is not mistaken for a bar.\n    """\n    r0, c0, r1, c1 = box\n    rows, cols = len(before), len(before[0])\n    if min(r0, c0, rows - 1 - r1, cols - 1 - c1) > 6:\n        return False  # a bar sits at the edge of the frame; a beam or wire in the middle of the field is not a bar\n    for grid, pick in ((before, before), (after, after)):\n        r, c = comp[0]\n        value = pick[r][c]\n        if any(pick[rr][cc] != value for rr, cc in comp):\n            continue\n        horiz = _run_len(grid, r0, c0, 0, -1, value) + _run_len(grid, r0, c1, 0, 1, value) + (c1 - c0 + 1)\n        vert = _run_len(grid, r0, c0, -1, 0, value) + _run_len(grid, r1, c0, 1, 0, value) + (r1 - r0 + 1)\n        if horiz >= 12 or vert >= 12:\n            return True\n    return False\n\n\ndef _dominant(grid, comp):\n    cnt = Counter(letter(grid[r][c]) for (r, c) in comp)\n    return "".join(ch for ch, _ in cnt.most_common(2)), cnt.most_common(1)[0][0]\n\n\ndef _clusters(comps, gap=8):\n    """Group components whose boxes are within `gap` cells of each other."""\n    boxes = [bbox_of(c) for c in comps]\n    parent = list(range(len(comps)))\n\n    def find(i):\n        while parent[i] != i:\n            parent[i] = parent[parent[i]]\n            i = parent[i]\n        return i\n\n    for i in range(len(comps)):\n        for j in range(i + 1, len(comps)):\n            if bbox_gap(boxes[i], boxes[j]) <= gap:\n                parent[find(i)] = find(j)\n    groups = {}\n    for i in range(len(comps)):\n        groups.setdefault(find(i), []).append(i)\n    return [[comps[i] for i in idxs] for idxs in groups.values()]\n\n\ndef small_far_changes(before, after, *, small_max=16, box_max=6, gap_min=8, max_events=2):\n    """Small patches that changed far away from the main activity of one action (a legend mark, a counter tick).\n\n    The changed cells are grouped into clusters; bar-like cells (timer bars) are dropped first. The biggest cluster (ties:\n    the one made of more pieces, a moving thing breaks into several) is the main activity. Every other small, compact\n    cluster at least `gap_min` cells away from it is reported, unless it looks like a small object that moved (a vacated and\n    an occupied piece of the same size). Returns [] whenever the picture is ambiguous.\n    """\n    cells = diff_cells(before, after)\n    if len(cells) < 3:\n        return []\n    raw = components8(cells)\n    if len(raw) > 60:\n        return []  # a busy frame (animation, big redraw): nothing here is a clean indicator signal\n    comps = [c for c in raw if not _bar_like(before, after, c, bbox_of(c))]\n    clusters = _clusters(comps)\n    if len(clusters) < 2:\n        return []\n    clusters.sort(key=lambda g: (sum(len(c) for c in g), len(g)), reverse=True)\n    main = clusters[0]\n    mbox = bbox_of([p for c in main for p in c])\n    out = []\n    for g in clusters[1:]:\n        pts = [p for c in g for p in c]\n        box = bbox_of(pts)\n        if len(pts) < 2 or len(pts) > small_max or box[2] - box[0] + 1 > box_max or box[3] - box[1] + 1 > box_max:\n            continue  # one cell is a timer tick; a legend or tray mark is several cells\n        if bbox_gap(mbox, box) < gap_min:\n            continue\n        if len(g) >= 2:\n            sizes = sorted(len(c) for c in g)\n            if sizes[0] >= 1 and abs(sizes[0] - sizes[-1]) <= 1:\n                continue  # a vacated and an occupied piece: a small object moved\n        bl, _ = _dominant(before, pts)\n        al, _ = _dominant(after, pts)\n        out.append({"box": box, "size": len(pts), "before": bl, "after": al})\n    if len(out) > max_events:\n        return []\n    return out\n\n\ndef detect_budget(frames, min_actions=3):\n    """Same detector as budget_bar_patch.py: a straight line whose run of equal cells loses cells from one end."""\n    k = len(frames) - 1\n    if k < min_actions:\n        return None\n    n = len(frames[0])\n    best = None\n    lines = [("row", i) for i in range(n)] + [("col", j) for j in range(len(frames[0][0]))]\n    for kind, idx in lines:\n        def line(frame):\n            return list(frame[idx]) if kind == "row" else [row[idx] for row in frame]\n\n        first = line(frames[0])\n        runs, start = [], 0\n        for i in range(1, len(first) + 1):\n            if i == len(first) or first[i] != first[start]:\n                if i - start >= 12:\n                    runs.append((start, i - 1))\n                start = i\n        if not runs:\n            continue\n        if line(frames[-1]) == first:\n            continue  # a bar that is being used up differs between the first and the last frame; most lines do not\n        series = [line(f) for f in frames]\n        changed_prev = set()\n        ok = True\n        steps_with_change = 0\n        max_step = 0\n        for t in range(1, len(series)):\n            changed = {i for i in range(len(first)) if series[t][i] != first[i]}\n            if not changed >= changed_prev:\n                ok = False\n                break\n            if len(changed) > len(changed_prev):\n                steps_with_change += 1\n                max_step = max(max_step, len(changed) - len(changed_prev))\n            changed_prev = changed\n        if not ok or not changed_prev or max_step > 6 or steps_with_change < 0.3 * k:\n            continue\n        for lo, hi in runs:\n            d = {i for i in changed_prev if lo <= i <= hi}\n            if not d or d != changed_prev:\n                continue\n            cells = sorted(d)\n            contiguous = cells[-1] - cells[0] + 1 == len(cells)\n            at_end = cells[0] == lo or cells[-1] == hi\n            if not (contiguous and at_end):\n                continue\n            new_colors = {series[-1][i] for i in cells}\n            if len(new_colors) != 1:\n                continue\n            used, cap = len(cells), hi - lo + 1\n            rate = used / k\n            if not (0.15 <= rate <= 4.0):\n                continue\n            cand = dict(kind=kind, index=idx, cap=cap, used=used, left=cap - used, rate=rate,\n                        remaining=int((cap - used) / rate), actions=k)\n            if best is None or (cap, used) > (best["cap"], best["used"]):\n                best = cand\n    return best\n\n\ndef budget_alert(b, *, first_time):\n    """One line, or \'\' when nothing is worth saying: the first time a bar is found, then only when it runs low."""\n    if not b or b["left"] <= 0:\n        return ""  # an empty bar means the attempt is already over; there is nothing left to warn about\n    frac = b["left"] / float(b["cap"])\n    low = frac <= 0.25 or b["remaining"] <= 12\n    if not (first_time or low):\n        return ""\n    where = f"row {b[\'index\']}" if b["kind"] == "row" else f"column {b[\'index\']}"\n    tail = ""\n    if low:\n        tail = f" At this rate about {b[\'remaining\']} more actions empty it, and the level then resets (actions already spent still count)."\n    return (\n        f"Step budget (read from the frames by the harness): the bar along {where} has {b[\'left\']} of {b[\'cap\']} cells left "\n        f"after {b[\'actions\']} actions on this attempt (about {b[\'rate\']:.1f} cells per action).{tail}"\n    )\n\n\ndef _move_of(before, after):\n    """(colour, cells, d_row, d_col) of the colour that shifted most between two grids, or None.\n\n    Cells that left a colour and cells that took it are compared by their centres; a colour only counts when both sets are of\n    similar size (an object moved, not painted over), which keeps counters and animations out.\n    """\n    cells = diff_cells(before, after)\n    if not cells or len(cells) > 400:\n        return None\n    left, took = {}, {}\n    for r, c in cells:\n        left.setdefault(before[r][c], []).append((r, c))\n        took.setdefault(after[r][c], []).append((r, c))\n    total = sum(len(row) for row in before)\n    census = Counter(v for row in before for v in row)\n    best = None\n    for col in set(left) & set(took):\n        if census[col] > 0.25 * total:\n            continue  # the background "moves" the opposite way to every object; it is not what the key moves\n        v, e = left[col], took[col]\n        big = max(len(v), len(e))\n        if min(len(v), len(e)) < 4 or abs(len(v) - len(e)) > 0.25 * big:\n            continue\n        dr = round(sum(p[0] for p in e) / len(e) - sum(p[0] for p in v) / len(v))\n        dc = round(sum(p[1] for p in e) / len(e) - sum(p[1] for p in v) / len(v))\n        if dr == 0 and dc == 0:\n            continue\n        if best is None or big > best[1]:\n            best = (col, big, dr, dc)\n    return best\n\n\ndef _span(lo, hi):\n    return f"{lo}" if lo == hi else f"{lo}-{hi}"\n\n\ndef describe_box(box):\n    r0, c0, r1, c1 = box\n    return f"rows {_span(r0, r1)}, cols {_span(c0, c1)}"\n\n\nclass Ledger:\n    """Per-level facts, fed one transition at a time (action name, result dict, grid before, grid after)."""\n\n    def __init__(self, level):\n        self.level = level\n        self.n_actions = 0           # real actions on this level (RESET not counted)\n        self.keys = {}               # key -> {"n", "changed", "noop", "first_noop", "moves": Counter, "samples": [(before, after)]}\n        self.events = []             # {"idx", "action", "box", "before", "after", "revert_of"}\n        self.marks = {}              # box -> list of (idx, before_letters, after_letters)\n        self.undo = 0\n        self.resets = 0\n        self.mouse_targets = []      # (row, col) of clicks\n        self.noisy = False\n\n    # ---- feeding -------------------------------------------------------------------------------------------------\n    def feed(self, action, result, before, after):\n        """Returns the new indicator events produced by this transition (usually an empty list)."""\n        key = key_of(action)\n        if key == "RESET":\n            self.resets += 1\n            self.marks = {}          # a restarted level legitimately clears its marks\n            return []\n        self.n_actions += 1\n        idx = self.n_actions\n        rec = self.keys.setdefault(key, {"n": 0, "changed": 0, "noop": 0, "first_noop": None, "samples": []})\n        rec["n"] += 1\n        cells = diff_cells(before, after)\n        inner = inner_changed(cells, len(after), len(after[0]) if after else 64)\n        if inner > 0:\n            rec["changed"] += 1\n            if len(rec["samples"]) < 40:\n                rec["samples"].append((before, after))\n            else:\n                rec["samples"][rec["n"] % 40] = (before, after)\n        else:\n            rec["noop"] += 1\n            if rec["first_noop"] is None:\n                rec["first_noop"] = idx\n        if key == "UNDO":\n            self.undo += 1\n        if key == "MOUSE":\n            s = str(action)\n            try:\n                rr = int(s.split("row=")[1].split(",")[0])\n                cc = int(s.split("col=")[1].split(")")[0])\n                if len(self.mouse_targets) < 12:\n                    self.mouse_targets.append((rr, cc))\n            except (IndexError, ValueError):\n                pass\n        if self.noisy:\n            return []\n        patches = small_far_changes(before, after) if inner else []\n        out = []\n        for p in patches:\n            ev = {"idx": idx, "action": key, "box": p["box"], "before": p["before"], "after": p["after"],\n                  "revert_of": None, "kind": "first", "original": p["before"]}\n            hist = self.marks.setdefault(p["box"], [])\n            if hist:\n                original = hist[0][1]            # the colour the patch had before anything changed it\n                ev["original"] = original\n                if p["after"] == original:\n                    ev["kind"] = "lost"          # back to the original colour: a mark that was earned may be gone\n                    ev["revert_of"] = next((i for (i, _b, a) in reversed(hist) if a != original), None)\n                else:\n                    earlier = next((i for (i, _b, a) in hist if a == p["after"]), None)\n                    ev["kind"] = "again" if earlier is not None else "other"\n                    ev["revert_of"] = earlier\n            hist.append((idx, p["before"], p["after"]))\n            self.events.append(ev)\n            out.append(ev)\n        if len(self.marks) > 6:\n            # many different places flicker (a busy board, not a legend): say nothing rather than add noise.\n            # One place that changes back and forth many times is a signal, so repeats at one place do not count.\n            self.noisy = True\n            self.events = []\n            out = []\n        return out\n\n    # ---- text ----------------------------------------------------------------------------------------------------\n    @staticmethod\n    def _names(ev):\n        b, a, o = ev["before"][:1], ev["after"][:1], ev.get("original", ev["before"])[:1]\n        return COLOR_NAMES.get(b, b), COLOR_NAMES.get(a, a), COLOR_NAMES.get(o, o)\n\n    @staticmethod\n    def event_line(ev):\n        box = describe_box(ev["box"])\n        bn, an, on = Ledger._names(ev)\n        kind = ev.get("kind", "first")\n        if kind == "lost":\n            since = f" (it had changed to {bn} after action {ev[\'revert_of\']})" if ev["revert_of"] is not None else ""\n            return (\n                f"Indicator note: after action {ev[\'idx\']} on this level ({ev[\'action\']}), the small patch at {box} went back to "\n                f"its original colour, {on}{since}. A mark you earned may have been lost: compare what you did between those "\n                "two actions."\n            )\n        if kind == "again":\n            return (\n                f"Indicator note: after action {ev[\'idx\']} on this level ({ev[\'action\']}), the small patch at {box} changed to "\n                f"{an} again ({bn} before; it was {an} after action {ev[\'revert_of\']})."\n            )\n        return (\n            f"Indicator note: after action {ev[\'idx\']} on this level ({ev[\'action\']}), a small patch away from the moved objects "\n            f"changed: {box}, {bn} to {an}. Legends, trays and counters often report progress; note which action did this."\n        )\n\n    def key_lines(self, valid_actions=None):\n        lines = []\n        order = [k for k in ("UP", "DOWN", "LEFT", "RIGHT") if k in self.keys] + sorted(k for k in self.keys if k not in ("UP", "DOWN", "LEFT", "RIGHT"))\n        for k in order:\n            rec = self.keys[k]\n            line = f"- {k}: pressed {rec[\'n\']}, changed the board {rec[\'changed\']}, did nothing {rec[\'noop\']}"\n            if rec["first_noop"] is not None and rec["noop"]:\n                line += f" (first at action {rec[\'first_noop\']})"\n            sig = self.move_signature(k)\n            if sig:\n                line += f"; typical effect: {sig}"\n            if k == "MOUSE" and self.mouse_targets:\n                line += "; clicked at " + ", ".join(f"({r},{c})" for r, c in self.mouse_targets[:6])\n            lines.append(line)\n        few = [k for k in order if self.keys[k]["n"] < 2 and k not in ("RESET",)]\n        if few:\n            lines.append("- Pressed fewer than twice (one result says little about other board states): " + ", ".join(few) + ".")\n        if valid_actions:\n            unused = [a for a in valid_actions if key_of(a) not in self.keys and key_of(a) not in ("RESET",)]\n            if unused:\n                lines.append("- Valid but not pressed on this level: " + ", ".join(sorted(set(key_of(a) for a in unused))) + ".")\n        return lines\n\n    def move_signature(self, key, limit=8):\n        """Most common shift of the cells of one colour over up to `limit` recent effective presses of one key.\n\n        Pure grid arithmetic: the cells that left a colour and the cells that took it, compared by their centres.\n        """\n        rec = self.keys.get(key)\n        if not rec or not rec["samples"]:\n            return ""\n        sig = Counter()\n        sizes = {}\n        used = 0\n        for before, after in rec["samples"][-limit:]:\n            used += 1\n            m = _move_of(before, after)\n            if m is None:\n                continue\n            color, n, dr, dc = m\n            sig[(color, dr, dc)] += 1\n            sizes[(color, dr, dc)] = max(sizes.get((color, dr, dc), 0), n)\n        if not sig or not used:\n            return ""\n        (color, dr, dc), cnt = sig.most_common(1)[0]\n        if cnt * 2 < used:\n            return ""  # no consistent move: say nothing rather than a number that most presses contradict\n        parts = []\n        if dr:\n            parts.append(f"{\'down\' if dr > 0 else \'up\'} {abs(dr)}")\n        if dc:\n            parts.append(f"{\'right\' if dc > 0 else \'left\'} {abs(dc)}")\n        name = COLOR_NAMES.get(letter(color), str(color))\n        return f"{name} cells shifted {\' and \'.join(parts)} ({cnt} of {used} presses checked)"\n\n    def event_lines(self, last=5):\n        out = []\n        for ev in self.events[-last:]:\n            box = describe_box(ev["box"])\n            bn, an, on = Ledger._names(ev)\n            kind = ev.get("kind", "first")\n            if kind == "lost":\n                out.append(f"- after action {ev[\'idx\']} ({ev[\'action\']}): the patch at {box} went back to its original colour, {on} (a mark may have been lost).")\n            elif kind == "again":\n                out.append(f"- after action {ev[\'idx\']} ({ev[\'action\']}): the patch at {box} changed to {an} again.")\n            else:\n                out.append(f"- after action {ev[\'idx\']} ({ev[\'action\']}): the patch at {box} changed from {bn} to {an}.")\n        return out\n\n    def digest_lines(self, clear_actions):\n        """Short facts of a cleared level, for the LEVEL LOG of a later level."""\n        bits = []\n        for k in ("UP", "DOWN", "LEFT", "RIGHT"):\n            if k in self.keys:\n                sig = self.move_signature(k, limit=4)\n                if sig:\n                    bits.append(f"{k}: {sig}")\n        extra = [f"{k} pressed {r[\'n\']} times" for k, r in self.keys.items() if k not in ("UP", "DOWN", "LEFT", "RIGHT", "RESET")]\n        text = f"- Level {self.level} was cleared with {self.n_actions} actions."\n        if bits:\n            text += " Effects seen there: " + "; ".join(bits) + "."\n        if extra:\n            text += " Other keys used: " + ", ".join(extra[:4]) + "."\n        if clear_actions:\n            text += " The last actions before clearing it: " + " ".join(clear_actions[-10:]) + "."\n        return [text]\n\n\nACK_TEXT = "Noted: these are harness-computed facts about this level, and I will check my plan against them."\n\nPROTOCOL_LINES = [\n    "How strong runs work on a level like this (use it now):",\n    "1. Keep two or three readings of the goal side by side. For each, name the cheapest probe (1-2 actions) that would refute it and what you expect to see.",\n    "2. After every probe look at three things: the objects that moved, any legend/tray/counter marks that changed (and which action changed them), and the step bar.",\n    "3. Write results as \'action -> what changed, in which board state\'. One press with no effect in one state says nothing about the other states.",\n    "4. If a mark you had earned disappears, undo or avoid the last action before building on that state.",\n    "5. Send short batches (1-3 actions) while a rule is unconfirmed; longer batches only for sequences you have already verified.",\n]\n\n\ndef build_level_log(ledger, *, level_tokens, valid_actions, budget_text, earlier, undo_note=True):\n    lines = [\n        f"LEVEL LOG - facts the harness computed from the recorded frames of this level (not from your notes): level {ledger.level}, "\n        f"{ledger.n_actions} actions here, about {level_tokens} generated tokens so far.",\n        "Keys on this level:",\n        *ledger.key_lines(valid_actions),\n    ]\n    if undo_note and ledger.undo:\n        lines.append(f"- UNDO was pressed {ledger.undo} times; every press counts as one action.")\n    if ledger.events:\n        lines.append("Small patches that changed away from the moved objects (legend/tray/counter candidates):")\n        lines.extend(ledger.event_lines())\n    elif not ledger.noisy:\n        lines.append("No indicator patch (legend, tray, counter) has changed on this level so far; if the screen has one, no action of yours has moved it.")\n    if budget_text:\n        lines.append(budget_text)\n    if earlier:\n        lines.append("Earlier levels of this game:")\n        lines.extend(earlier[-2:])\n    lines.append("")\n    lines.extend(PROTOCOL_LINES)\n    return "\\n".join(lines)'
fable_core_file.write_text(FABLE_CORE_SRC, encoding="utf-8")
print("Successfully wrote fable_layer_core.py")

# ---------------------------------------------------------------------------
# 1. Update segmentation.py: bbox, centroid, and is_border
# ---------------------------------------------------------------------------
seg_file = src_root / "ARC3-Inference/inference/utils/segmentation.py"
seg_text = seg_file.read_text(encoding="utf-8")

if '"is_border": is_border' not in seg_text:
    v4_nodes_append = """        cells = comp["cells"]
        min_r = min(r for r, _ in cells)
        max_r = max(r for r, _ in cells)
        min_c = min(c for _, c in cells)
        max_c = max(c for _, c in cells)
        r_c = round(sum(r for r, _ in cells) / len(cells))
        c_c = round(sum(c for _, c in cells) / len(cells))
        H, W = len(layer), len(layer[0]) if layer else 0
        is_border = bool(
            H > 0 and W > 0 and (
                (min_r == 0 and max_r == 0 and len(cells) >= W * 0.75) or
                (min_r == H - 1 and max_r == H - 1 and len(cells) >= W * 0.75) or
                (min_c == 0 and max_c == 0 and len(cells) >= H * 0.75) or
                (min_c == W - 1 and max_c == W - 1 and len(cells) >= H * 0.75)
            )
        )
        nodes.append(
            {
                "id": cid,
                "color": color,
                "hash": signature[0],
                "rotation": signature[1],
                "rotational_symmetry": signature[2],
                "pose_hash": signature[3],
                "shape_hash": signature[4],
                "pixels": len(comp["cells"]),
                "bbox": [min_r, min_c, max_r, max_c],
                "centroid": [r_c, c_c],
                "is_border": is_border,
                "boundary": [[r, c] for r, c in boundary],
                "children": children[cid],
            }
        )"""

    old_seg_centroid = """        cells = comp["cells"]
        min_r = min(r for r, _ in cells)
        max_r = max(r for r, _ in cells)
        min_c = min(c for _, c in cells)
        max_c = max(c for _, c in cells)
        r_c = round(sum(r for r, _ in cells) / len(cells))
        c_c = round(sum(c for _, c in cells) / len(cells))
        nodes.append(
            {
                "id": cid,
                "color": color,
                "hash": signature[0],
                "rotation": signature[1],
                "rotational_symmetry": signature[2],
                "pose_hash": signature[3],
                "shape_hash": signature[4],
                "pixels": len(comp["cells"]),
                "bbox": [min_r, min_c, max_r, max_c],
                "centroid": [r_c, c_c],
                "boundary": [[r, c] for r, c in boundary],
                "children": children[cid],
            }
        )"""

    old_seg_pristine = """        nodes.append(
            {
                "id": cid,
                "color": color,
                "hash": signature[0],
                "rotation": signature[1],
                "rotational_symmetry": signature[2],
                "pose_hash": signature[3],
                "shape_hash": signature[4],
                "pixels": len(comp["cells"]),
                "boundary": [[r, c] for r, c in boundary],
                "children": children[cid],
            }
        )"""

    if old_seg_centroid in seg_text:
        seg_text = seg_text.replace(old_seg_centroid, v4_nodes_append, 1)
    elif old_seg_pristine in seg_text:
        seg_text = seg_text.replace(old_seg_pristine, v4_nodes_append, 1)
    else:
        raise ValueError("Failed to match nodes.append target in segmentation.py")

    seg_file.write_text(seg_text, encoding="utf-8")
    print("Successfully injected bbox, centroid, and is_border into segmentation.py")
else:
    print("segmentation.py already has is_border")

# ---------------------------------------------------------------------------
# 2. Update prompts.py: Document candidate_clicks, object_at, solved_memory, bfs_path
# ---------------------------------------------------------------------------
prompt_file = src_root / "ARC3-Inference/inference/agent/prompts.py"
prompt_text = prompt_file.read_text(encoding="utf-8")

if "bfs_path" not in prompt_text:
    old_fields_centroid = """`pixels` (cell count), `bbox` ([min_row, min_col, max_row, max_col]), `centroid` (geometric center [row, col] for targeting clicks), `boundary`"""
    old_fields_pristine = """`pixels` (cell count), `boundary`"""
    new_fields = """`pixels` (cell count), `bbox` ([min_row, min_col, max_row, max_col]), `centroid` (geometric center [row, col] for targeting clicks), `is_border` (True if outer boundary/HUD bar), `boundary`"""

    if old_fields_centroid in prompt_text:
        prompt_text = prompt_text.replace(old_fields_centroid, new_fields, 1)
    elif old_fields_pristine in prompt_text:
        prompt_text = prompt_text.replace(old_fields_pristine, new_fields, 1)

    old_addendum_anchor = '    "- `frame_diff(before=None, after=None)` compares two frames. Omitted arguments default to `previous_frame` and `current_frame`, respectively.\\n"'
    new_addendum_block = '''    "- `candidate_clicks(color=None, min_size=1, max_size=None, exclude_border=True)` returns candidate click targets with their `centroid` [row, col], `bbox`, and `color`.\\n"
    "- `object_at(row, col)` returns the segmented object node covering cell `(row, col)`, or `None`.\\n"
    "- `bfs_path(start, goal, walkable=None, blocked=None, step=1)` returns shortest action list ['UP','RIGHT',...] or None.\\n"
    "- `current_frame.solved_memory` (also available as `solved_memory`) is a list of summaries from completed levels in this game: `[{'level': ..., 'actions_taken': ..., 'winning_actions': [...]}, ...]`. Core object mechanics and action patterns from earlier levels often carry forward.\\n"
    "- `current_frame.level_baseline` (also available as `level_baseline`): human reference action count for this level (when available). Plan direct, efficient routes to conserve actions and maximize efficiency.\\n"
    "- `frame_diff(before=None, after=None)` compares two frames. Omitted arguments default to `previous_frame` and `current_frame`, respectively.\\n"'''

    if "candidate_clicks" in prompt_text:
        old_v4_clicks = '''    "- `candidate_clicks(color=None, min_size=1, max_size=None, exclude_border=True)` returns candidate click targets with their `centroid` [row, col], `bbox`, and `color`.\\n"'''
        new_v5_clicks = '''    "- `candidate_clicks(color=None, min_size=1, max_size=None, exclude_border=True)` returns candidate click targets with their `centroid` [row, col], `bbox`, and `color`.\\n"
    "- `bfs_path(start, goal, walkable=None, blocked=None, step=1)` returns shortest action list ['UP','RIGHT',...] or None.\\n"'''
        prompt_text = prompt_text.replace(old_v4_clicks, new_v5_clicks, 1)
    else:
        assert old_addendum_anchor in prompt_text, "Failed to find frame_diff anchor in prompts.py"
        prompt_text = prompt_text.replace(old_addendum_anchor, new_addendum_block, 1)

    prompt_file.write_text(prompt_text, encoding="utf-8")
    print("Successfully documented candidate_clicks, object_at, bfs_path, and solved_memory in prompts.py")
else:
    print("prompts.py already documented bfs_path")

# ---------------------------------------------------------------------------
# 3. Update python_tool_sandbox.py: inject candidate_clicks, object_at, bfs_path, solved_memory
# ---------------------------------------------------------------------------
sandbox_file = src_root / "ARC3-Inference/inference/agent/python_tool_sandbox.py"
sandbox_text = sandbox_file.read_text(encoding="utf-8")

if "def bfs_path" not in sandbox_text:
    old_frame_from_payload = """    def _frame_from_payload(payload):
        if not isinstance(payload, dict):
            return None
        return FrameView(
            ascii=str(payload.get("ascii", "")),
            step=int(payload.get("step", 0)),
            level=int(payload.get("level", 0)),
            shape=payload.get("shape", [0, 0]),
            grid=payload.get("grid", []),
        )"""

    new_helpers_def = """    def candidate_clicks(color=None, min_size=1, max_size=None, exclude_border=True, frame=None):
        target = frame if frame is not None else runtime_globals.get("current_frame")
        if target is None:
            return []
        seg = getattr(target, "segmentation", None)
        if not seg or not isinstance(seg, dict):
            return []
        nodes = seg.get("nodes") or []
        res = []
        for n in nodes:
            if not isinstance(n, dict):
                continue
            if exclude_border and n.get("is_border", False):
                continue
            if color is not None and n.get("color") != color:
                continue
            px = int(n.get("pixels", 0))
            if px < min_size:
                continue
            if max_size is not None and px > max_size:
                continue
            c = n.get("centroid")
            b = n.get("bbox")
            res.append({
                "id": n.get("id"),
                "color": n.get("color"),
                "centroid": list(c) if c else None,
                "bbox": list(b) if b else None,
                "pixels": px,
            })
        res.sort(key=lambda item: item["pixels"], reverse=True)
        return res

    def object_at(row, col, frame=None):
        target = frame if frame is not None else runtime_globals.get("current_frame")
        if target is None:
            return None
        seg = getattr(target, "segmentation", None)
        if not seg or not isinstance(seg, dict):
            return None
        nodes = seg.get("nodes") or []
        for n in nodes:
            if not isinstance(n, dict):
                continue
            bbox = n.get("bbox")
            if not bbox or len(bbox) != 4:
                continue
            min_r, min_c, max_r, max_c = bbox
            if min_r <= row <= max_r and min_c <= col <= max_c:
                return dict(n)
        return None

    def bfs_path(start, goal, walkable=None, blocked=None, step=1, bounds=(64, 64)):
        from collections import deque
        if start is None or goal is None:
            return None
        try:
            start_pt = (int(start[0]), int(start[1]))
            if isinstance(goal, (tuple, list)) and len(goal) == 2 and isinstance(goal[0], (int, float)):
                goal_set = {(int(goal[0]), int(goal[1]))}
            else:
                goal_set = {(int(p[0]), int(p[1])) for p in goal}
        except (TypeError, IndexError, ValueError):
            return None
        if not goal_set:
            return None
        if start_pt in goal_set:
            return []
        walk_set = {(int(p[0]), int(p[1])) for p in walkable} if walkable is not None else None
        block_set = {(int(p[0]), int(p[1])) for p in blocked} if blocked is not None else set()
        max_r, max_c = bounds
        dirs = [("UP", -step, 0), ("DOWN", step, 0), ("LEFT", 0, -step), ("RIGHT", 0, step)]
        visited = {start_pt: None}
        q = deque([start_pt])
        while q:
            curr = q.popleft()
            if curr in goal_set:
                path = []
                c = curr
                while visited[c] is not None:
                    prev_pt, act = visited[c]
                    path.append(act)
                    c = prev_pt
                return list(reversed(path))
            for act_name, dr, dc in dirs:
                nr, nc = curr[0] + dr, curr[1] + dc
                nxt = (nr, nc)
                if nxt in visited or nxt in block_set:
                    continue
                if walk_set is not None and nxt not in walk_set:
                    continue
                if nr < 0 or nr >= max_r or nc < 0 or nc >= max_c:
                    continue
                visited[nxt] = (curr, act_name)
                q.append(nxt)
        return None

    def _frame_from_payload(payload):
        if not isinstance(payload, dict):
            return None
        fv = FrameView(
            ascii=str(payload.get("ascii", "")),
            step=int(payload.get("step", 0)),
            level=int(payload.get("level", 0)),
            shape=payload.get("shape", [0, 0]),
            grid=payload.get("grid", []),
        )
        fv.solved_memory = list(payload.get("solved_memory") or [])
        fv.level_baseline = payload.get("level_baseline")
        return fv"""

    if "def candidate_clicks" in sandbox_text:
        bfs_insert = """    def bfs_path(start, goal, walkable=None, blocked=None, step=1, bounds=(64, 64)):
        from collections import deque
        if start is None or goal is None:
            return None
        try:
            start_pt = (int(start[0]), int(start[1]))
            if isinstance(goal, (tuple, list)) and len(goal) == 2 and isinstance(goal[0], (int, float)):
                goal_set = {(int(goal[0]), int(goal[1]))}
            else:
                goal_set = {(int(p[0]), int(p[1])) for p in goal}
        except (TypeError, IndexError, ValueError):
            return None
        if not goal_set:
            return None
        if start_pt in goal_set:
            return []
        walk_set = {(int(p[0]), int(p[1])) for p in walkable} if walkable is not None else None
        block_set = {(int(p[0]), int(p[1])) for p in blocked} if blocked is not None else set()
        max_r, max_c = bounds
        dirs = [("UP", -step, 0), ("DOWN", step, 0), ("LEFT", 0, -step), ("RIGHT", 0, step)]
        visited = {start_pt: None}
        q = deque([start_pt])
        while q:
            curr = q.popleft()
            if curr in goal_set:
                path = []
                c = curr
                while visited[c] is not None:
                    prev_pt, act = visited[c]
                    path.append(act)
                    c = prev_pt
                return list(reversed(path))
            for act_name, dr, dc in dirs:
                nr, nc = curr[0] + dr, curr[1] + dc
                nxt = (nr, nc)
                if nxt in visited or nxt in block_set:
                    continue
                if walk_set is not None and nxt not in walk_set:
                    continue
                if nr < 0 or nr >= max_r or nc < 0 or nc >= max_c:
                    continue
                visited[nxt] = (curr, act_name)
                q.append(nxt)
        return None\n\n"""
        sandbox_text = sandbox_text.replace("    def _frame_from_payload", bfs_insert + "    def _frame_from_payload", 1)
        sandbox_text = sandbox_text.replace('runtime_globals["object_at"] = object_at\n', 'runtime_globals["object_at"] = object_at\n            runtime_globals["bfs_path"] = bfs_path\n', 1)
    else:
        assert old_frame_from_payload in sandbox_text, "Failed to find _frame_from_payload in python_tool_sandbox.py"
        sandbox_text = sandbox_text.replace(old_frame_from_payload, new_helpers_def, 1)

        old_refresh_tail = """            runtime_globals["valid_actions"] = [str(item) for item in state_payload.get("valid_actions", [])]
            runtime_globals["death_ledger"] = state_payload.get("death_ledger") or {"attempts": []}
            runtime_globals["last_action_call_result"] = action_result"""

        new_refresh_tail = """            runtime_globals["valid_actions"] = [str(item) for item in state_payload.get("valid_actions", [])]
            runtime_globals["death_ledger"] = state_payload.get("death_ledger") or {"attempts": []}
            runtime_globals["last_action_call_result"] = action_result

    def candidate_goals(exclude_border=True, max_candidates=8):
        nodes = runtime_globals.get("candidate_clicks")(min_size=1, exclude_border=exclude_border)
        if not nodes:
            return []
        scores = []
        for n in nodes:
            c = n.get("color")
            p = n.get("pixels", 0)
            score = 0.0
            if p == 1:
                score += 35.0
            elif p <= 4:
                score += 20.0
            if c not in (0, 4):  # not background/floor
                score += 15.0
            n_copy = dict(n)
            n_copy["goal_score"] = score
            scores.append(n_copy)
        scores.sort(key=lambda x: x["goal_score"], reverse=True)
        return scores[:max_candidates]

            runtime_globals["candidate_clicks"] = candidate_clicks
            runtime_globals["candidate_goals"] = candidate_goals
            runtime_globals["object_at"] = object_at
            runtime_globals["bfs_path"] = bfs_path
            runtime_globals["solved_memory"] = list(state_payload.get("solved_memory") or [])
            runtime_globals["level_baseline"] = current_frame.level_baseline if current_frame else None"""

        assert old_refresh_tail in sandbox_text, "Failed to find _refresh_state tail in python_tool_sandbox.py"
        sandbox_text = sandbox_text.replace(old_refresh_tail, new_refresh_tail, 1)

    sandbox_file.write_text(sandbox_text, encoding="utf-8")
    print("Successfully injected candidate_clicks, object_at, bfs_path, and solved_memory into python_tool_sandbox.py")
else:
    print("python_tool_sandbox.py already has bfs_path")

# ---------------------------------------------------------------------------
# 4. Update tool_agent.py: record level clears and forward into runtime state
# ---------------------------------------------------------------------------
agent_file = src_root / "ARC3-Inference/inference/agent/tool_agent.py"
agent_text = agent_file.read_text(encoding="utf-8")

if "if current_frame_payload is not None:" not in agent_text:
    if 'current_frame_payload["solved_memory"] = list(getattr(self, "_cleared_level_memories", []))' in agent_text:
        old_v4_assign = 'current_frame_payload["solved_memory"] = list(getattr(self, "_cleared_level_memories", []))'
        new_v5_assign = '''if current_frame_payload is not None:
                current_frame_payload["solved_memory"] = list(getattr(self, "_cleared_level_memories", []))'''
        agent_text = agent_text.replace(old_v4_assign, new_v5_assign, 1)
    else:
        old_init = """        self._session_total_tokens = 0
        self._session_generated_tokens = 0
        self._step_env_callback: Callable[[dict[str, Any]], dict[str, Any]] | None = None"""

        new_init = """        self._session_total_tokens = 0
        self._session_generated_tokens = 0
        self._cleared_level_memories: list[dict[str, Any]] = []
        self._step_env_callback: Callable[[dict[str, Any]], dict[str, Any]] | None = None"""

        assert old_init in agent_text, "Failed to find session init in tool_agent.py"
        agent_text = agent_text.replace(old_init, new_init, 1)

        old_ensure = """            self._history_messages = []
            self._session_total_tokens = 0
            self._session_generated_tokens = 0"""

        new_ensure = """            self._history_messages = []
            self._session_total_tokens = 0
            self._session_generated_tokens = 0
            self._cleared_level_memories = []"""

        assert old_ensure in agent_text, "Failed to find _ensure_session in tool_agent.py"
        agent_text = agent_text.replace(old_ensure, new_ensure, 1)

        old_update_knowledge = """        if step_executed:
            self._last_step_summary = self._summarize_step_sequence(action_results)
            self._update_summarized_knowledge_from_step_summary()"""

        new_update_knowledge = """        if step_executed:
            self._last_step_summary = self._summarize_step_sequence(action_results)
            self._update_summarized_knowledge_from_step_summary()
            if getattr(self, "_cleared_level_memories", None) is not None and self._last_step_summary and self._last_step_summary.get("level_transition"):
                cleared_lvl = max(1, int(self._last_step_summary.get("level") or 2) - 1)
                acts = self._last_step_summary.get("executed_actions") or []
                self._cleared_level_memories.append({
                    "level": cleared_lvl,
                    "actions_taken": int(self._last_step_summary.get("executed_count", len(acts))),
                    "winning_actions": [str(a) for a in acts[-5:]] if acts else [],
                })"""

        assert old_update_knowledge in agent_text, "Failed to find _update_summarized_knowledge in tool_agent.py"
        agent_text = agent_text.replace(old_update_knowledge, new_update_knowledge, 1)

        old_state_return = """            return {
                "current_frame": current_frame_payload,
                "history": _ascii_history_view_payload(refreshed_history),
                "valid_actions": sanitized_actions,
                "death_ledger": (
                    self._death_ledger_payload()
                    if _get_env_bool("ARC3_DEATH_LEDGER", False)
                    else None
                ),
                "last_action_call_result": (
                    dict(persisted_action_result)
                    if isinstance(persisted_action_result, dict)
                    else {}
                ),
            }"""

        new_state_return = """            if current_frame_payload is not None:
                current_frame_payload["solved_memory"] = list(getattr(self, "_cleared_level_memories", []))
                current_frame_payload["level_baseline"] = getattr(self, "_current_level_baseline", None)
            return {
                "current_frame": current_frame_payload,
                "history": _ascii_history_view_payload(refreshed_history),
                "valid_actions": sanitized_actions,
                "death_ledger": (
                    self._death_ledger_payload()
                    if _get_env_bool("ARC3_DEATH_LEDGER", False)
                    else None
                ),
                "last_action_call_result": (
                    dict(persisted_action_result)
                    if isinstance(persisted_action_result, dict)
                    else {}
                ),
                "solved_memory": list(getattr(self, "_cleared_level_memories", [])),
            }"""

        assert old_state_return in agent_text, "Failed to find _serialized_runtime_state return in tool_agent.py"
        agent_text = agent_text.replace(old_state_return, new_state_return, 1)

    agent_file.write_text(agent_text, encoding="utf-8")
    print("Successfully injected null-safe solved level tracking into tool_agent.py")
else:
    print("tool_agent.py already has null-safe solved level tracking")

# 5. Inject Fable layer hooks into tool_agent.py
FABLE_METHODS = '\n    # ---- Fable layer (fable_layer_patch.py) -----------------------------------------------------------------------\n    def _fl_on(self) -> bool:\n        return _get_env_bool("ARC3_FABLE_LAYER", False)\n\n    def _fl_core(self):\n        mod = getattr(self, "_fl_mod", None)\n        if mod is None:\n            from inference.agent import fable_layer_core as mod  # noqa: PLC0415\n            self._fl_mod = mod\n        return mod\n\n    def _fl_log(self, kind: str, **data) -> None:\n        """Optional JSON-lines record of what the layer said (ARC3_FABLE_LAYER_LOG=<path>); never raises."""\n        path = os.environ.get("ARC3_FABLE_LAYER_LOG", "").strip()\n        if not path:\n            return\n        try:\n            row = {"t": round(time.time(), 1), "kind": kind, "game": str(self._session_runtime_dir), **data}\n            with open(path, "a", encoding="utf-8") as f:\n                f.write(json.dumps(row, ensure_ascii=False) + "\\n")\n        except Exception:  # noqa: BLE001\n            pass\n\n    def _fl_level_tokens(self) -> int:\n        return max(0, int(self._session_generated_tokens) - int(getattr(self, "_tokens_at_level_start", 0) or 0))\n\n    def _fl_reset_session(self) -> None:\n        self._fl_session = self._session_runtime_dir\n        self._fl_ledgers = {}\n        self._fl_actions = {}\n        self._fl_cleared = set()\n        self._fl_done = 0\n        self._fl_n_before = {}\n        self._fl_pinned = None\n        self._fl_pin_state = None\n        self._fl_budget_cache = None\n        self._fl_budget_alerted = None\n\n    def _fl_sync(self, history_entries) -> dict:\n        """Bring the per-level ledgers up to date with the recorded history; returns {level: Ledger}."""\n        FL = self._fl_core()\n        if getattr(self, "_fl_session", None) != self._session_runtime_dir:\n            self._fl_reset_session()\n        entries = list(history_entries or [])\n        if len(entries) < self._fl_done:\n            keep_pin = self._fl_pinned\n            keep_state = self._fl_pin_state\n            self._fl_reset_session()\n            self._fl_pinned, self._fl_pin_state = keep_pin, keep_state\n        self._fl_n_before = {lv: led.n_actions for lv, led in self._fl_ledgers.items()}\n        for i in range(max(1, self._fl_done), len(entries)):\n            prev, cur = entries[i - 1], entries[i]\n            if prev.frame is None or cur.frame is None:\n                continue\n            pg, cg = prev.frame.grid, cur.frame.grid\n            pl, cl = int(prev.frame.level), int(cur.frame.level)\n            result = cur.result if isinstance(cur.result, dict) else {}\n            name = result.get("action_display") or cur.action or ""\n            if cl != pl:\n                # the action that cleared level `pl`: its own frame already belongs to the next level\n                led = self._fl_ledgers.setdefault(pl, FL.Ledger(pl))\n                led.feed(name, result, pg, pg)\n                self._fl_cleared.add(pl)\n            else:\n                led = self._fl_ledgers.setdefault(cl, FL.Ledger(cl))\n                led.feed(name, result, pg, cg)\n            acts = self._fl_actions.setdefault(pl, [])\n            acts.append(FL.key_of(name))\n            del acts[:-12]\n        self._fl_done = len(entries)\n        return self._fl_ledgers\n\n    def _fl_attempt_frames(self, history_entries, level):\n        """Grids of the current attempt on `level`: from the last RESET (or the level\'s first frame) to now."""\n        entries = [e for e in (history_entries or []) if e.frame is not None]\n        start = 0\n        for i, e in enumerate(entries):\n            if str(e.action or "").upper() == "RESET" or int(e.frame.level) != level:\n                start = i\n        frames = [e.frame.grid for e in entries[start:] if int(e.frame.level) == level]\n        return frames\n\n    def _fl_budget(self, history_entries, level):\n        """Detected step-budget bar of the current attempt, recomputed at most every 6 new frames."""\n        FL = self._fl_core()\n        frames = self._fl_attempt_frames(history_entries, level)\n        cache = getattr(self, "_fl_budget_cache", None)\n        if cache is not None and cache[0] == level and 0 <= len(frames) - cache[1] < 6 and len(frames) >= cache[1]:\n            return cache[2]\n        b = FL.detect_budget(frames) if len(frames) >= 4 else None\n        self._fl_budget_cache = (level, len(frames), b)\n        return b\n\n    def _fl_opener_lines(self, current_frame, history_entries) -> list:\n        """Lines for the per-turn opener: indicator notes and a low-budget alert. [] whenever unsure."""\n        if not self._fl_on() or current_frame is None:\n            return []\n        try:\n            FL = self._fl_core()\n            ledgers = self._fl_sync(history_entries)\n            level = int(current_frame.level)\n            led = ledgers.get(level)\n            lines = []\n            level_tokens = self._fl_level_tokens()\n            after = _get_env_int("ARC3_FABLE_EVENTS_AFTER_TOKENS", 15000)\n            if led is not None and after >= 0 and level_tokens >= after and not led.noisy:\n                before_n = self._fl_n_before.get(level, 0)\n                fresh = [ev for ev in led.events if ev["idx"] > before_n]\n                for ev in fresh[-2:]:\n                    lines.append(FL.Ledger.event_line(ev))\n                    self._fl_log("note", level=level, level_tokens=level_tokens, text=lines[-1])\n            if led is not None and _get_env_bool("ARC3_FABLE_BUDGET_ALERT", True) and led.n_actions >= 6:\n                b = self._fl_budget(history_entries, level)\n                text = FL.budget_alert(b, first_time=False) if b else ""\n                if text:\n                    last = getattr(self, "_fl_budget_alerted", None)\n                    # one alert per attempt, then again only when about 10 actions have been used since\n                    if last is None or last[0] != level or b["remaining"] <= last[1] - 10:\n                        lines.append(text)\n                        self._fl_budget_alerted = (level, b["remaining"])\n                        self._fl_log("budget", level=level, level_tokens=level_tokens, text=text)\n            return lines\n        except Exception as exc:  # noqa: BLE001 - the layer is an extra; it must never stop a turn\n            log.debug("fable layer opener failed: %s", exc)\n            return []\n\n    def _fl_remove_pinned(self, pinned) -> None:\n        user_text = pinned[0].get("content")\n        kept = []\n        skip_reply = False\n        for m in self._history_messages:\n            if m.get("role") == "user" and m.get("content") == user_text:\n                skip_reply = True\n                continue\n            if skip_reply and m.get("role") == "assistant" and m.get("content") == pinned[1].get("content"):\n                skip_reply = False\n                continue\n            skip_reply = False\n            kept.append(m)\n        self._history_messages = kept\n\n    def _fl_maybe_pin(self, current_frame, history_entries) -> None:\n        """Append the harness-computed LEVEL LOG to the history once a level has taken long, and keep it pinned."""\n        if not self._fl_on() or current_frame is None:\n            return\n        try:\n            pin_at = _get_env_int("ARC3_FABLE_PIN_TOKENS", 30000)\n            if pin_at <= 0:\n                return\n            refresh = max(1, _get_env_int("ARC3_FABLE_PIN_REFRESH_TOKENS", 40000))\n            FL = self._fl_core()\n            ledgers = self._fl_sync(history_entries)\n            level = int(current_frame.level)\n            led = ledgers.get(level)\n            tokens = self._fl_level_tokens()\n            if led is None or led.n_actions < 3 or tokens < pin_at:\n                return\n            state = self._fl_pin_state\n            if state is not None and state[0] == level and tokens - state[1] < refresh:\n                return\n            history = self._history_messages\n            if history and str(history[-1].get("role", "")).strip() == "user":\n                return  # two user messages in a row would break the alternation; try again next turn\n            b = self._fl_budget(history_entries, level)\n            budget_text = FL.budget_alert(b, first_time=True) if b else ""\n            earlier = []\n            for lv in sorted(ledgers):\n                if lv < level and lv in self._fl_cleared:\n                    earlier.extend(ledgers[lv].digest_lines(self._fl_actions.get(lv)))\n            text = FL.build_level_log(\n                led,\n                level_tokens=tokens,\n                valid_actions=list(getattr(self, "_current_valid_actions", None) or []),\n                budget_text=budget_text,\n                earlier=earlier,\n            )\n            if self._fl_pinned:\n                self._fl_remove_pinned(self._fl_pinned)\n            user = {"role": "user", "content": text}\n            reply = {"role": "assistant", "content": FL.ACK_TEXT}\n            self._history_messages.append(user)\n            self._history_messages.append(reply)\n            self._fl_pinned = [user, reply]\n            self._fl_pin_state = (level, tokens)\n            log.info("fable layer: level log pinned (level %s, %s level tokens, %s chars)", level, tokens, len(text))\n            self._fl_log("pin", level=level, level_tokens=tokens, actions=led.n_actions, text=text)\n        except Exception as exc:  # noqa: BLE001\n            log.debug("fable layer pin failed: %s", exc)\n\n    def _fl_restore_pinned(self, history: list) -> list:\n        """After a trim: put the pinned LEVEL LOG back at the head when the trim dropped it."""\n        pinned = getattr(self, "_fl_pinned", None)\n        if not pinned or not self._fl_on():\n            return history\n        try:\n            text = pinned[0].get("content")\n            if any(m.get("role") == "user" and m.get("content") == text for m in history):\n                return history\n            return [*pinned, *history]\n        except Exception as exc:  # noqa: BLE001\n            log.debug("fable layer restore failed: %s", exc)\n            return history\n\n    def _fl_forget_pin(self) -> None:\n        self._fl_pinned = None\n        self._fl_pin_state = None\n        self._fl_budget_cache = None\n        self._fl_budget_alerted = None\n\n'

FABLE_EDITS = [
    (
        "    def _build_user_prompt(\n        self,\n        action_num: int,\n",
        FABLE_METHODS + "    def _build_user_prompt(\n        self,\n        action_num: int,\n",
    ),
    (
        "                f\"Valid actions right now: {_format_valid_action_line(valid_actions)}.\",\n            ]\n        )\n",
        "                f\"Valid actions right now: {_format_valid_action_line(valid_actions)}.\",\n            ]\n        )\n"
        "        lines.extend(self._fl_opener_lines(current_frame, history_entries))\n",
    ),
    (
        "            self._actions_at_level_start = _priority_action_count(summary)\n"
        "            self._tokens_at_level_start = self._session_generated_tokens\n",
        "            self._actions_at_level_start = _priority_action_count(summary)\n"
        "            self._tokens_at_level_start = self._session_generated_tokens\n"
        "            self._fl_forget_pin()\n",
    ),
    (
        "        preserve_history = True\n        resuming_after_yield = bool(getattr(self, \"_resume_after_yield\", False))\n",
        "        self._fl_maybe_pin(current_frame, history_entries)\n"
        "        preserve_history = True\n        resuming_after_yield = bool(getattr(self, \"_resume_after_yield\", False))\n",
    ),
    (
        "        if len(history) != len(messages) - 1:\n"
        "            self._note_history_evicted()\n"
        "        return [system_message, *history]\n",
        "        if len(history) != len(messages) - 1:\n"
        "            self._note_history_evicted()\n"
        "        history = self._fl_restore_pinned(history)\n"
        "        return [system_message, *history]\n",
    ),
]

if "ARC3_FABLE_LAYER" not in agent_text:
    for old, new in FABLE_EDITS:
        assert agent_text.count(old) == 1, f"Failed to match anchor: {old[:50]}"
        agent_text = agent_text.replace(old, new, 1)
    agent_file.write_text(agent_text, encoding="utf-8")
    print("Successfully injected Fable layer into tool_agent.py")
else:
    print("tool_agent.py already has Fable layer")
