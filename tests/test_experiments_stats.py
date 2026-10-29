import random

from src.experiments.records import RunRecord
from src.experiments.stats import bootstrap_ci, noise_floor, paired_diffs, suite_means, verdict

GAMES = [f"g{i}" for i in range(8)]


def rec(arm, game, seed, score, error=None):
    return RunRecord(arm, game, seed, score, 0, 0, error)


def synthetic(effect, noise=2.0, seeds=3, rng_seed=0):
    rng = random.Random(rng_seed)
    out = []
    for gi, game in enumerate(GAMES):
        base_mean = 10.0 + 5.0 * gi
        for seed in range(seeds):
            out.append(rec("base", game, seed, base_mean + rng.gauss(0, noise)))
            out.append(rec("cand", game, seed, base_mean + effect + rng.gauss(0, noise)))
    return out


def test_suite_means_excludes_failed_runs():
    records = [rec("a", "g0", 0, 10.0), rec("a", "g1", 0, 20.0), rec("a", "g2", 0, 0.0, "boom")]
    assert suite_means(records, "a") == {0: 15.0}


def test_noise_floor_none_with_single_seed():
    assert noise_floor([rec("a", "g0", 0, 5.0)], "a") is None


def test_noise_floor_is_stdev_of_seed_means():
    records = [rec("a", "g0", 0, 10.0), rec("a", "g0", 1, 20.0)]
    assert abs(noise_floor(records, "a") - 7.0710678) < 1e-6


def test_paired_diffs_only_uses_pairs_present_in_both_arms():
    records = [rec("b", "g0", 0, 10.0), rec("b", "g1", 0, 10.0), rec("c", "g0", 0, 14.0)]
    assert paired_diffs(records, "b", "c") == [("g0", 4.0)]


def test_bootstrap_ci_constant_diffs_collapse_to_the_value():
    assert bootstrap_ci([("g0", 3.0), ("g1", 3.0)]) == (3.0, 3.0)


def test_verdict_better_on_real_gain():
    assert verdict(synthetic(effect=10.0), "base", "cand").label == "better"


def test_verdict_worse_on_real_loss():
    assert verdict(synthetic(effect=-10.0), "base", "cand").label == "worse"


def test_verdict_no_difference_for_identical_arms():
    records = []
    for game in GAMES:
        for seed in range(3):
            score = 10.0 + seed
            records += [rec("base", game, seed, score), rec("cand", game, seed, score)]
    result = verdict(records, "base", "cand")
    assert result.label == "no difference"
    assert result.mean_diff == 0.0


def test_verdict_no_difference_under_pure_noise():
    assert verdict(synthetic(effect=0.0), "base", "cand").label == "no difference"


def test_verdict_insufficient_with_one_seed():
    assert verdict(synthetic(effect=10.0, seeds=1), "base", "cand").label == "insufficient data"


def test_verdict_all_zero_scores_is_not_better():
    records = [rec(arm, g, s, 0.0) for arm in ("base", "cand") for g in GAMES for s in range(3)]
    assert verdict(records, "base", "cand").label == "no difference"
