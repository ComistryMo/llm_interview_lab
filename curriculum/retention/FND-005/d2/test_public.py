import pytest


def test_parses_objects_in_order(submission):
    assert list(submission.iter_jsonl_objects(['{"a":1}\n', '{"b":2}\n'])) == [{"a": 1}, {"b": 2}]


def test_is_lazy(submission):
    seen = []
    def lines():
        seen.append(1); yield '{"a":1}\n'
        seen.append(2); yield '{"b":2}\n'
    iterator = submission.iter_jsonl_objects(lines())
    assert seen == []
    assert next(iterator) == {"a": 1} and seen == [1]


def test_rejects_blank_with_line_number(submission):
    with pytest.raises(ValueError, match="2"):
        list(submission.iter_jsonl_objects(['{"a":1}\n', '\n']))


def test_rejects_non_object_json(submission):
    with pytest.raises(ValueError, match="1"):
        list(submission.iter_jsonl_objects(['[1,2]\n']))


def test_rejects_non_string_line(submission):
    with pytest.raises(ValueError, match="2"):
        list(submission.iter_jsonl_objects(['{"a":1}', 7]))
