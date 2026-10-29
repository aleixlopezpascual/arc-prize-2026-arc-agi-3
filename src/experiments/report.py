from __future__ import annotations

import argparse
import datetime
from collections.abc import Sequence
from pathlib import Path

from src.config import DOCS_DIR
from src.experiments.records import RunRecord, load_records
from src.experiments.runner import DEFAULT_RESULTS
from src.experiments.stats import noise_floor, suite_means, verdict


def _mean_score(records: Sequence[RunRecord], arm: str) -> float | None:
    means = list(suite_means(records, arm).values())
    return sum(means) / len(means) if means else None


def render_table(records: Sequence[RunRecord], baseline: str, candidates: Sequence[str]) -> str:
    header = (
        f"{'Arm':<18} | {'Mean (%)':>9} | {'Seeds':>5} | {'Failed':>6} | "
        f"{'Delta':>8} | {'90% CI':<18} | Verdict"
    )
    lines = [header, "-" * len(header)]
    for arm in [baseline, *candidates]:
        mean = _mean_score(records, arm)
        mean_text = "n/a" if mean is None else f"{mean:.2f}"
        seeds = len(suite_means(records, arm))
        failed = sum(1 for rec in records if rec.arm == arm and not rec.ok)
        if arm == baseline:
            floor = noise_floor(records, baseline)
            floor_text = "n/a" if floor is None else f"{floor:.2f}"
            delta, interval, label = "-", "-", f"baseline (noise floor {floor_text})"
        else:
            result = verdict(records, baseline, arm)
            delta = f"{result.mean_diff:+.2f}"
            interval = f"[{result.ci_low:.2f}, {result.ci_high:.2f}]"
            label = result.label
        lines.append(
            f"{arm:<18} | {mean_text:>9} | {seeds:>5} | {failed:>6} | "
            f"{delta:>8} | {interval:<18} | {label}"
        )
    return "\n".join(lines)


def ledger_row(
    records: Sequence[RunRecord], baseline: str, candidate: str, today: str
) -> str:
    result = verdict(records, baseline, candidate)
    mean = _mean_score(records, candidate)
    mean_text = "n/a" if mean is None else f"{mean:.2f}%"
    ok_runs = [rec for rec in records if rec.arm == candidate and rec.ok]
    levels = sum(rec.levels_completed for rec in ok_runs)
    actions = sum(rec.total_actions for rec in ok_runs)
    notes = (
        f"{result.label}: delta {result.mean_diff:+.2f}, "
        f"90% CI [{result.ci_low:.2f}, {result.ci_high:.2f}], "
        f"noise floor {result.noise_floor:.2f}."
    )
    return (
        f"| `ab-{candidate}-vs-{baseline}-{today}` | {today} | "
        f"A/B {candidate} vs {baseline} ({result.n_pairs} paired runs) | "
        f"{mean_text} | {levels} | {actions} | - | {notes} |\n"
    )


def append_ledger_row(row: str, ledger_path: Path | str = DOCS_DIR / "experiments.md") -> None:
    target = Path(ledger_path)
    if not target.exists():
        return
    with open(target, "a", encoding="utf-8") as handle:
        handle.write(row)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare experiment arms against a baseline")
    parser.add_argument("--results", default=str(DEFAULT_RESULTS))
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", nargs="+", required=True)
    parser.add_argument("--log-ledger", action="store_true")
    args = parser.parse_args()

    records = load_records(args.results)
    print(render_table(records, args.baseline, args.candidate))
    if args.log_ledger:
        today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
        for candidate in args.candidate:
            append_ledger_row(ledger_row(records, args.baseline, candidate, today))


if __name__ == "__main__":
    main()
