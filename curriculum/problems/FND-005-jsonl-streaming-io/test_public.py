import json
from pathlib import Path
import pytest

def test_write_then_read_round_trip(submission, tmp_path):
    path = tmp_path / "toy.jsonl"
    records = [{"id":"一","value":1}, {"id":"b","value":[1,2]}]
    assert submission.JsonlIO.write(path, records) == 2
    assert list(submission.JsonlIO.read(path)) == records

def test_reader_is_lazy_iterator(submission, tmp_path):
    path = tmp_path / "data.jsonl"
    path.write_text('{"x":1}\n', encoding="utf-8")
    reader = submission.JsonlIO.read(path)
    assert iter(reader) is reader
    assert next(reader) == {"x": 1}

def test_writer_uses_one_object_per_line(submission, tmp_path):
    path = tmp_path / "data.jsonl"
    submission.JsonlIO.write(str(path), [{"x":1}, {"x":2}])
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2 and all(isinstance(json.loads(line), dict) for line in lines)

@pytest.mark.parametrize("content,line", [('{"x":1}\n\n', 2), ('{"x":1}\nnot-json\n', 2), ('[1,2]\n', 1)])
def test_reader_reports_invalid_line(submission, tmp_path, content, line):
    path = tmp_path / "bad.jsonl"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match=str(line)):
        list(submission.JsonlIO.read(path))

def test_writer_rejects_non_object_without_silent_coercion(submission, tmp_path):
    with pytest.raises(ValueError):
        submission.JsonlIO.write(tmp_path / "bad.jsonl", [{"ok":1}, [1,2]])

