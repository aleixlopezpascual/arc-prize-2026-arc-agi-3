from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from src.agents import BaseAgent
from src.config import OOF_DIR
from src.evaluate import EvaluationRunner, GameEvalSummary
from src.experiments.arms import ARMS, PILOT_GAMES, Arm, build_agent, validate_games
from src.experiments.records import RunRecord, append_record, load_records

DEFAULT_RESULTS = OOF_DIR / "experiments" / "results.jsonl"


def config_hash(arm: Arm) -> str:
    """Short stable digest of an arm's full config, stored on every record it produces."""
    payload = json.dumps(dataclasses.asdict(arm), sort_keys=True)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]


class Evaluator(Protocol):
    max_actions_per_level: int

    def run_game(self, agent: BaseAgent, game_prefix: str) -> GameEvalSummary: ...


def run_arm(
    arm: Arm,
    games: Sequence[str],
    seeds: Sequence[int],
    results_path: Path | str,
    evaluator: Evaluator,
) -> list[RunRecord]:
    """Run every (seed, game) not already in the results file; return the new records."""
    existing = load_records(results_path)
    digest = config_hash(arm)
    stale = sorted({rec.config for rec in existing if rec.arm == arm.name and rec.config != digest})
    if stale:
        raise ValueError(
            f"Arm '{arm.name}' config changed since existing results in {results_path} "
            f"({digest} vs {', '.join(stale)}); use a new arm name or a new results file"
        )
    done = {rec.key for rec in existing}
    evaluator.max_actions_per_level = arm.max_actions_per_level
    new: list[RunRecord] = []
    with tempfile.TemporaryDirectory() as tmp:
        for seed in seeds:
            for game in games:
                if (arm.name, game, seed) in done:
                    continue
                try:
                    agent = build_agent(arm, seed, Path(tmp) / f"{game}-{seed}")
                    summary = evaluator.run_game(agent, game)
                    failures = getattr(agent, "api_failures", 0)
                    if failures:
                        raise RuntimeError(f"{failures} API call(s) failed during the run")
                    record = RunRecord(
                        arm.name,
                        game,
                        seed,
                        summary.score,
                        summary.levels_completed,
                        summary.total_actions,
                        config=digest,
                    )
                except Exception as exc:  # noqa: BLE001 - a failed run is data, not a crash
                    record = RunRecord(
                        arm.name, game, seed, 0.0, 0, 0, f"{type(exc).__name__}: {exc}", digest
                    )
                append_record(results_path, record)
                new.append(record)
    return new


def resolve_games(csv: str) -> list[str]:
    return validate_games([game.strip() for game in csv.split(",") if game.strip()])


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an experiment arm over games and seeds")
    parser.add_argument("--arm", choices=sorted(ARMS), required=True)
    parser.add_argument("--games", default=",".join(PILOT_GAMES))
    parser.add_argument("--seeds", type=int, default=3, help="number of seeds (0..N-1)")
    parser.add_argument("--results", default=str(DEFAULT_RESULTS))
    args = parser.parse_args()

    arm = ARMS[args.arm]
    games = resolve_games(args.games)
    evaluator = EvaluationRunner(max_actions_per_level=arm.max_actions_per_level)
    new = run_arm(arm, games, list(range(args.seeds)), args.results, evaluator)
    failed = sum(1 for rec in new if not rec.ok)
    print(f"{arm.name}: {len(new)} new runs, {failed} failed -> {args.results}")


if __name__ == "__main__":
    main()
