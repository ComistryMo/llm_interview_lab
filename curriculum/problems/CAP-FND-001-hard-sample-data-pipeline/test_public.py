import json
import pytest


def _write(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_runs_full_pipeline_in_order(submission, tmp_path):
    rows = [
        {"sample_id": "a", "label": 1, "predictions": [1, 0, 2]},
        {"sample_id": "b", "label": 0, "predictions": [0, 0]},
        {"sample_id": "c", "label": 1, "predictions": [0, 1]},
    ]
    source, output = tmp_path / "in.jsonl", tmp_path / "out.jsonl"; _write(source, rows)
    result = submission.run_hard_sample_pipeline(source, output, 1, 2)
    assert result == {
        "input_samples": 3, "total_predictions": 7, "total_errors": 3,
        "hard_samples": 2, "label_counts": {1: 2}, "batches": [[rows[0], rows[2]]],
    }
    assert [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()] == [rows[0], rows[2]]


def test_keeps_short_last_batch_and_uses_threshold(submission, tmp_path):
    rows = [
        {"sample_id": "a", "label": 0, "predictions": [1, 1]},
        {"sample_id": "b", "label": 1, "predictions": [0, 0]},
        {"sample_id": "c", "label": 2, "predictions": [0, 0]},
    ]
    source, output = tmp_path / "in.jsonl", tmp_path / "out.jsonl"; _write(source, rows)
    assert submission.run_hard_sample_pipeline(source, output, 2, 2)["batches"] == [rows[:2], rows[2:]]


def test_empty_input_writes_empty_output(submission, tmp_path):
    source, output = tmp_path / "in.jsonl", tmp_path / "out.jsonl"; source.write_text("", encoding="utf-8")
    result = submission.run_hard_sample_pipeline(str(source), str(output), 1, 3)
    assert result == {"input_samples": 0, "total_predictions": 0, "total_errors": 0, "hard_samples": 0, "label_counts": {}, "batches": []}
    assert output.read_text(encoding="utf-8") == ""


def test_invalid_record_keeps_existing_output(submission, tmp_path):
    source, output = tmp_path / "in.jsonl", tmp_path / "out.jsonl"
    source.write_text('{"sample_id":"a","label":1,"predictions":[1]}\n{"sample_id":"b","label":true,"predictions":[1]}\n', encoding="utf-8")
    output.write_text("keep", encoding="utf-8")
    with pytest.raises(ValueError, match="2"):
        submission.run_hard_sample_pipeline(source, output, 1, 2)
    assert output.read_text(encoding="utf-8") == "keep"


def test_rejects_invalid_controls(submission, tmp_path):
    source = tmp_path / "in.jsonl"; source.write_text("", encoding="utf-8")
    for threshold, size in [(0, 1), (True, 1), (1, 0), (1, True)]:
        with pytest.raises(ValueError):
            submission.run_hard_sample_pipeline(source, tmp_path / "out.jsonl", threshold, size)


def test_returned_batches_do_not_share_prediction_lists(submission, tmp_path):
    row = {"sample_id": "a", "label": 1, "predictions": [0]}
    source, output = tmp_path / "in.jsonl", tmp_path / "out.jsonl"; _write(source, [row])
    result = submission.run_hard_sample_pipeline(source, output, 1, 1)
    result["batches"][0][0]["predictions"].append(9)
    assert json.loads(output.read_text(encoding="utf-8"))["predictions"] == [0]
