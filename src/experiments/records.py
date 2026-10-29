from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunRecord:
    arm: str
    game: str
    seed: int
    score: float
    levels_completed: int
    total_actions: int
    error: str | None = None
    config: str = ""

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def key(self) -> tuple[str, str, int]:
        return (self.arm, self.game, self.seed)


def append_record(path: Path | str, record: RunRecord) -> None:
    """Append one record as a JSON line, first terminating a truncated final line."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    needs_newline = False
    if target.exists() and target.stat().st_size > 0:
        with open(target, "rb") as handle:
            handle.seek(-1, 2)
            needs_newline = handle.read(1) != b"\n"
    with open(target, "a", encoding="utf-8") as handle:
        if needs_newline:
            handle.write("\n")
        handle.write(json.dumps(asdict(record)) + "\n")


def load_records(path: Path | str) -> list[RunRecord]:
    """Load records, skipping blank or unparsable lines (e.g. a line cut off by a crash)."""
    target = Path(path)
    if not target.exists():
        return []
    records: list[RunRecord] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            records.append(RunRecord(**json.loads(text)))
        except (json.JSONDecodeError, TypeError):
            continue
    return records
