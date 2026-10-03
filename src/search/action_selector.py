from __future__ import annotations

from collections.abc import Sequence

from src.search.branch_evaluator import BranchEvaluator


class SearchAwareAgent:
    def __init__(self, evaluator: BranchEvaluator | None = None) -> None:
        self.evaluator = evaluator

    def rank_branches(self, branches: Sequence[dict]) -> int:
        if not branches:
            return 0

        # Heuristic ranking: select branch with highest changed_cell_count or moved objects
        best_idx = 0
        max_score = -1.0

        for idx, report in enumerate(branches):
            score = 0.0
            score += report.get("changed_cell_count", 0) * 1.0
            score += len(report.get("moved", [])) * 5.0
            score += len(report.get("changed_color", [])) * 2.0
            score += len(report.get("resized", [])) * 3.0

            if score > max_score:
                max_score = score
                best_idx = idx

        return best_idx
