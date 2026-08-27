import json
import pytest


def test_transforms_objects_and_returns_count(submission, tmp_path):
    source, destination = tmp_path / "in.jsonl", tmp_path / "out.jsonl"
    source.write_text('{"x":1}\n{"x":2}\n', encoding="utf-8")
    count = submission.transform_jsonl(source, destination, lambda row: {"y": row["x"] + 1})
    assert count == 2
    assert [json.loads(line) for line in destination.read_text(encoding="utf-8").splitlines()] == [{"y": 2}, {"y": 3}]


def test_accepts_string_paths(submission, tmp_path):
    source, destination = tmp_path / "in.jsonl", tmp_path / "out.jsonl"
    source.write_text('', encoding="utf-8")
    assert submission.transform_jsonl(str(source), str(destination), lambda row: row) == 0
    assert destination.read_text(encoding="utf-8") == ""


def test_rejects_malformed_line_without_replacing_destination(submission, tmp_path):
    source, destination = tmp_path / "in.jsonl", tmp_path / "out.jsonl"
    source.write_text('{"ok":1}\nBAD\n', encoding="utf-8"); destination.write_text("keep", encoding="utf-8")
    with pytest.raises(ValueError, match="2"):
        submission.transform_jsonl(source, destination, lambda row: row)
    assert destination.read_text(encoding="utf-8") == "keep"


def test_rejects_non_object_transform_result(submission, tmp_path):
    source = tmp_path / "in.jsonl"; source.write_text('{"x":1}\n', encoding="utf-8")
    with pytest.raises(ValueError):
        submission.transform_jsonl(source, tmp_path / "out.jsonl", lambda row: [row])


def test_does_not_modify_source(submission, tmp_path):
    source = tmp_path / "in.jsonl"; source.write_text('{"x":1}\n', encoding="utf-8")
    before = source.read_bytes()
    submission.transform_jsonl(source, tmp_path / "out.jsonl", lambda row: dict(row))
    assert source.read_bytes() == before
