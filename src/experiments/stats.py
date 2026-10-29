from __future__ import annotations

import random
import statistics
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from src.experiments.records import RunRecord


@dataclass(frozen=True)
class Verdict:
    label: str  # "better", "worse", "no difference" or "insufficient data"
    mean_diff: float
    ci_low: float
    ci_high: float
    noise_floor: float
    n_pairs: int
    seeds_baseline: int
    seeds_candidate: int


def suite_means(records: Sequence[RunRecord], arm: str) -> dict[int, float]:
    """Mean score over games for each seed of one arm (failed runs excluded)."""
    by_seed: dict[int, list[float]] = defaultdict(list)
    for rec in records:
        if rec.arm == arm and rec.ok:
            by_seed[rec.seed].append(rec.score)
    return {seed: sum(scores) / len(scores) for seed, scores in by_seed.items()}


def noise_floor(records: Sequence[RunRecord], arm: str) -> float | None:
    """Sample standard deviation of per-seed suite means; None with fewer than 2 seeds."""
    means = list(suite_means(records, arm).values())
    if len(means) < 2:
        return None
    return statistics.stdev(means)


def paired_diffs(
    records: Sequence[RunRecord], baseline: str, candidate: str
) -> list[tuple[str, float]]:
    """(game, candidate - baseline) for every (game, seed) that both arms completed."""
    base = {(r.game, r.seed): r.score for r in records if r.arm == baseline and r.ok}
    cand = {(r.game, r.seed): r.score for r in records if r.arm == candidate and r.ok}
    return [(game, cand[(game, seed)] - base[(game, seed)])
            for game, seed in sorted(base.keys() & cand.keys())]


def bootstrap_ci(
    diffs: Sequence[tuple[str, float]],
    level: float = 0.9,
    n_boot: int = 2000,
    seed: int = 0,
) -> tuple[float, float]:
    """Percentile CI of the mean difference, resampling whole games (seeds stay together)."""
    if not diffs:
        raise ValueError("bootstrap_ci needs at least one paired difference")
    by_game: dict[str, list[float]] = defaultdict(list)
    for game, diff in diffs:
        by_game[game].append(diff)
    games = sorted(by_game)
    rng = random.Random(seed)
    means: list[float] = []
    for _ in range(n_boot):
        picked = [rng.choice(games) for _ in games]
        values = [v for game in picked for v in by_game[game]]
        means.append(sum(values) / len(values))
    means.sort()
    alpha = (1.0 - level) / 2.0
    low = means[int(alpha * n_boot)]
    high = means[min(n_boot - 1, int((1.0 - alpha) * n_boot))]
    return low, high


def verdict(
    records: Sequence[RunRecord],
    baseline: str,
    candidate: str,
    min_seeds: int = 2,
    level: float = 0.9,
    n_boot: int = 2000,
) -> Verdict:
    floor = noise_floor(records, baseline)
    seeds_base = len(suite_means(records, baseline))
    seeds_cand = len(suite_means(records, candidate))
    diffs = paired_diffs(records, baseline, candidate)
    if floor is None or seeds_base < min_seeds or seeds_cand < min_seeds or not diffs:
        return Verdict("insufficient data", 0.0, 0.0, 0.0, floor or 0.0, len(diffs),
                       seeds_base, seeds_cand)
    mean_diff = sum(d for _, d in diffs) / len(diffs)
    low, high = bootstrap_ci(diffs, level=level, n_boot=n_boot)
    if low > 0.0 and mean_diff > floor:
        label = "better"
    elif high < 0.0 and -mean_diff > floor:
        label = "worse"
    else:
        label = "no difference"
    return Verdict(label, mean_diff, low, high, floor, len(diffs), seeds_base, seeds_cand)
