#!/usr/bin/env python3
"""S16 token-patience sweep on tantan0327/arc-agi-3-agent scripts/sched_sim.py (paired seeds).

Usage: python3 scripts/sched_sim_s16_patience.py <path-to-arc-agi-3-agent clone> <seed0> <hard-game hazard scale, 1.0 = default>
"""

import importlib.util
import json
import statistics as st
import sys
from pathlib import Path

SIM = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("ss", SIM / "scripts/sched_sim.py")
ss = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ss)


def franzen_form(human, token_scale):
    def pol(g, phi):
        if not g.started:
            return ss.FRESH_BASE - g.queue_pos
        level, a, t = g.level, g.act_on_level, g.tok_on_level
        eff = (human / (human + a)) ** 2
        A = level * eff * ss.norm_N(g.N)
        tail = ss._tail_remaining(g.N, level) * phi
        chance = 0.25 * 0.5 ** ((a / 115.0) ** 2) + 0.75 * 0.5 ** ((t / token_scale) ** 2)
        return max(1.0, (A + tail) * chance * 100.0)

    return pol


POL = {
    "base(25,62k)": (franzen_form(25, 62000), 0.2),
    "S16(100,40k)": (franzen_form(100, 40000), 0.2),
    "S16+150k": (franzen_form(100, 150000), 0.2),
    "S16+200k": (franzen_form(100, 200000), 0.2),
    "S16+300k": (franzen_form(100, 300000), 0.2),
    "S16+500k": (franzen_form(100, 500000), 0.2),
    "S16+1e9": (franzen_form(100, 1e9), 0.2),
    "dprime": (ss.policy_dprime, 0.4),
}
d = 1.15
REG = {
    "main": (0.8, 0.1, d),
    "harder": (0.8, 0.1, d + 0.4),
    "easier": (0.8, 0.1, 1.0),
    "mix": (0.6, 0.1, d),
    "allhard": (1.0, 0.1, d),
}
SEEDS = list(range(int(sys.argv[2]), int(sys.argv[2]) + 16))
traces = json.loads((SIM / "scratchpad/sched/traces.json").read_text())
ss.build_hazards(traces)
res = {}
for rname, (hf, kappa, diff) in REG.items():
    ss.HAZ_SCALE = kappa
    ss.DIFFICULTY = diff
    ss.HAZ_HARD_SCALE = float(sys.argv[3])
    for pname, (pol, fade) in POL.items():
        out = []
        for seed in SEEDS:
            games = ss.hidden_population(traces, 110, seed, hf)
            ss.simulate(games, pol, wall=ss.WALL_BUDGET_S, allow_continue=True, fade=fade)
            out.append(ss.mean_score(games))
        res[(rname, pname)] = out
    print(rname, "done", flush=True)
print("\nmean score (16 paired seeds) and paired diff vs S16(100,40k) [mean +- sd of diff]")
print(f"{'policy':>14} " + " ".join(f"{r:>18}" for r in REG))
for pname in POL:
    cells = []
    for r in REG:
        m = st.mean(res[(r, pname)])
        diffs = [x - y for x, y in zip(res[(r, pname)], res[(r, "S16(100,40k)")])]
        cells.append(f"{m:6.2f} ({st.mean(diffs):+5.2f}±{st.pstdev(diffs):4.2f})")
    print(f"{pname:>14} " + " ".join(f"{c:>18}" for c in cells))
