import random

from src.experiments.records import RunRecord
from src.experiments.report import append_ledger_row, ledger_row, render_table

GAMES = [f"g{i}" for i in range(8)]


def rec(arm, game, seed, score, error=None):
    return RunRecord(arm, game, seed, score, 1, 10, error)


def synthetic(effect, seeds=3):
    rng = random.Random(0)
    out = []
    for gi, game in enumerate(GAMES):
        base_mean = 10.0 + 5.0 * gi
        for seed in range(seeds):
            out.append(rec("base", game, seed, base_mean + rng.gauss(0, 2.0)))
            out.append(rec("cand", game, seed, base_mean + effect + rng.gauss(0, 2.0)))
    return out


def test_table_shows_verdict_and_both_arms():
    table = render_table(synthetic(effect=10.0), "base", ["cand"])
    assert "base" in table
    assert "cand" in table
    assert "better" in table


def test_table_reports_insufficient_data_with_one_seed():
    table = render_table(synthetic(effect=10.0, seeds=1), "base", ["cand"])
    assert "insufficient data" in table


def test_table_counts_failed_runs():
    records = synthetic(effect=10.0)
    records.append(rec("cand", "g_extra", 0, 0.0, error="RuntimeError: boom"))
    lines = render_table(records, "base", ["cand"]).splitlines()
    cand_line = next(line for line in lines if line.startswith("cand"))
    assert cand_line.split("|")[3].strip() == "1"


def test_ledger_row_has_eight_columns():
    row = ledger_row(synthetic(effect=10.0), "base", "cand", "2026-10-29")
    assert row.endswith("|\n")
    assert row.strip().count("|") == 9
    assert "better" in row
    assert "`ab-cand-vs-base-2026-10-29`" in row


def test_append_ledger_row_noops_when_ledger_missing(tmp_path):
    append_ledger_row("| x |\n", tmp_path / "missing.md")
    assert not (tmp_path / "missing.md").exists()


def test_append_ledger_row_appends(tmp_path):
    ledger = tmp_path / "experiments.md"
    ledger.write_text("header\n", encoding="utf-8")
    append_ledger_row("| row |\n", ledger)
    assert ledger.read_text(encoding="utf-8") == "header\n| row |\n"
