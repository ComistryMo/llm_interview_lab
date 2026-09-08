import math
import pytest

np = pytest.importorskip("numpy")


def test_size_weighting(submission):
    r = submission.grouped_auc(
        ["a", "a", "b", "b", "b", "b"], [0, 1, 1, 1, 0, 0], [0, 1, 0, 0, 1, 1]
    )
    assert r["gauc"] == pytest.approx(1 / 3)
    assert r["valid_groups"] == 2


def test_single_class_excluded(submission):
    r = submission.grouped_auc([1, 1, 2], [0, 1, 1], [0, 1, 9])
    assert r == dict(gauc=1.0, valid_groups=1, excluded_samples=1)


def test_all_invalid(submission):
    with pytest.raises(ValueError):
        submission.grouped_auc([1, 2], [0, 1], [0, 1])


def test_tied_scores(submission):
    assert submission.grouped_auc([1, 1], [0, 1], [3, 3])["gauc"] == 0.5


def test_group_score_offsets(submission):
    assert (
        submission.grouped_auc([1, 1, 2, 2], [0, 1, 0, 1], [0, 1, 100, 101])["gauc"]
        == 1
    )
