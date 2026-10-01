from __future__ import annotations

import argparse
import datetime
import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from arc_agi import Arcade, OperationMode
from arcengine import GameState

from src.agents import AVAILABLE_AGENTS, BaseAgent
from src.config import DOCS_DIR, ENVIRONMENTS_DIR, PUBLIC_GAMES
from src.metrics import compute_competition_score

logger = logging.getLogger("evaluate")


@dataclass
class GameEvalSummary:
    game_id: str
    levels_completed: int
    total_actions: int
    score: float
    level_outcomes: list[tuple[int, int, bool]] = field(default_factory=list)


@dataclass
class SuiteEvalSummary:
    agent_name: str
    total_score: float
    total_levels_completed: int
    total_actions: int
    game_summaries: list[GameEvalSummary] = field(default_factory=list)


class EvaluationRunner:
    def __init__(
        self,
        environments_dir: Path | str = ENVIRONMENTS_DIR,
        max_actions_per_level: int = 400,
    ) -> None:
        self.environments_dir = str(environments_dir)
        self.max_actions_per_level = max_actions_per_level
        self.arcade = Arcade(
            operation_mode=OperationMode.OFFLINE,
            environments_dir=self.environments_dir,
        )

    def _resolve_game_id(self, game_prefix: str) -> str:
        envs = self.arcade.get_environments()
        for env in envs:
            if env.game_id.startswith(game_prefix):
                return env.game_id
        raise ValueError(f"Game prefix '{game_prefix}' not found in {self.environments_dir}")

    def run_game(self, agent: BaseAgent, game_prefix: str) -> GameEvalSummary:
        agent.reset()
        full_game_id = self._resolve_game_id(game_prefix)
        card_id = self.arcade.open_scorecard()

        scorecard = None
        try:
            env = self.arcade.make(full_game_id, scorecard_id=card_id)
            if env is None:
                raise RuntimeError(f"Failed to create environment for {full_game_id}")

            frame = env.reset()
            frames = [frame]
            action_count = 0
            level_action_count = 0
            current_level = frame.levels_completed

            while not agent.is_done(frames, frame):
                action = agent.choose_action(frames, frame)
                frame = env.step(action)
                frames.append(frame)
                action_count += 1
                level_action_count += 1

                if frame.levels_completed != current_level:
                    # Level transitioned
                    current_level = frame.levels_completed
                    level_action_count = 0

                if frame.state in (GameState.WIN, GameState.GAME_OVER):
                    break

                if level_action_count >= self.max_actions_per_level:
                    break
        finally:
            scorecard = self.arcade.close_scorecard(card_id)

        # Extract levels outcome from scorecard
        env_score_list = scorecard.find_environment(game_prefix) if scorecard else None
        level_outcomes: list[tuple[int, int, bool]] = []
        score = 0.0
        levels_completed = 0

        if env_score_list and env_score_list.runs:
            best_run = max(env_score_list.runs, key=lambda r: r.score)
            score = best_run.score
            levels_completed = best_run.levels_completed
            actions = best_run.level_actions or []
            baselines = best_run.level_baseline_actions or []
            scores = best_run.level_scores or []
            for a, b, s in zip(actions, baselines, scores):
                level_outcomes.append((b, a, s > 0.0))
        else:
            score = 0.0

        return GameEvalSummary(
            game_id=full_game_id,
            levels_completed=levels_completed,
            total_actions=action_count,
            score=score,
            level_outcomes=level_outcomes,
        )

    def run_suite(
        self,
        agent: BaseAgent,
        agent_name: str,
        games: Sequence[str],
    ) -> SuiteEvalSummary:
        summaries: list[GameEvalSummary] = []
        for game in games:
            summary = self.run_game(agent, game)
            summaries.append(summary)

        game_scores = [s.score for s in summaries]
        total_score = compute_competition_score(game_scores)
        total_levels = sum(s.levels_completed for s in summaries)
        total_actions = sum(s.total_actions for s in summaries)

        return SuiteEvalSummary(
            agent_name=agent_name,
            total_score=total_score,
            total_levels_completed=total_levels,
            total_actions=total_actions,
            game_summaries=summaries,
        )


def log_experiment(summary: SuiteEvalSummary, games_str: str) -> None:
    ledger_path = DOCS_DIR / "experiments.md"
    if not ledger_path.exists():
        return

    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    exp_id = f"eval-{summary.agent_name}-{today}"
    row = (
        f"| `{exp_id}` | {today} | {summary.agent_name} on {games_str} | "
        f"{summary.total_score:.2f}% | {summary.total_levels_completed} | "
        f"{summary.total_actions} | - | Offline evaluation runner pass. |\n"
    )

    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(row)
    print(f"📝 Appended results to {ledger_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="ARC-AGI-3 Local Evaluation Runner")
    parser.add_argument(
        "--agent",
        choices=AVAILABLE_AGENTS.keys(),
        default="random",
        help="Agent identifier to evaluate",
    )
    parser.add_argument(
        "--games",
        type=str,
        default="ls20,ar25,dc22",
        help="Comma-separated game prefixes or '--all' for 25 public games",
    )
    parser.add_argument(
        "--max-actions",
        type=int,
        default=400,
        help="Max action count per level before termination",
    )
    parser.add_argument(
        "--log-ledger",
        action="store_true",
        help="Log experiment results into docs/experiments.md",
    )

    args = parser.parse_args()

    target_games = (
        PUBLIC_GAMES
        if args.games.strip() == "--all"
        else [g.strip() for g in args.games.split(",")]
    )
    agent_cls = AVAILABLE_AGENTS[args.agent]
    agent = agent_cls()

    runner = EvaluationRunner(max_actions_per_level=args.max_actions)
    print(f"\n🎮 Evaluating Agent '{args.agent}' across {len(target_games)} game(s)...")

    suite_summary = runner.run_suite(agent=agent, agent_name=args.agent, games=target_games)

    print("\n" + "=" * 65)
    print(f"{'Game ID':<20} | {'Levels':<8} | {'Actions':<8} | {'Score (%)':<10}")
    print("-" * 65)
    for g in suite_summary.game_summaries:
        print(f"{g.game_id:<20} | {g.levels_completed:<8} | {g.total_actions:<8} | {g.score:<10.2f}")
    print("=" * 65)
    print(f"Overall Competition Score: {suite_summary.total_score:.2f}%")
    print(f"Total Levels Cleared:      {suite_summary.total_levels_completed}")
    print(f"Total Actions Taken:       {suite_summary.total_actions}\n")

    if args.log_ledger:
        log_experiment(suite_summary, args.games)


if __name__ == "__main__":
    main()
