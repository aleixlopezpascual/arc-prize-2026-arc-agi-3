from src.experiments.records import RunRecord, append_record, load_records


def _rec(game: str, seed: int = 0, error: str | None = None) -> RunRecord:
    return RunRecord("a", game, seed, 12.5, 2, 40, error)


def test_round_trip_and_ok_flag(tmp_path):
    path = tmp_path / "r.jsonl"
    append_record(path, _rec("g0"))
    append_record(path, _rec("g1", error="RuntimeError: boom"))
    loaded = load_records(path)
    assert [r.game for r in loaded] == ["g0", "g1"]
    assert loaded[0].ok is True
    assert loaded[1].ok is False
    assert loaded[0].key == ("a", "g0", 0)


def test_load_missing_file_is_empty(tmp_path):
    assert load_records(tmp_path / "nope.jsonl") == []


def test_append_after_truncated_line_does_not_merge_records(tmp_path):
    path = tmp_path / "r.jsonl"
    append_record(path, _rec("g0"))
    with open(path, "a", encoding="utf-8") as handle:
        handle.write('{"arm": "a", "gam')  # crash mid-write, no trailing newline
    append_record(path, _rec("g1"))
    assert [r.game for r in load_records(path)] == ["g0", "g1"]
