import math
import pytest

np = pytest.importorskip("numpy")


def test_perfect(submission):
    assert submission.ndcg_at_k([3, 2, 1], [9, 8, 7], 3) == pytest.approx(1)


def test_zero_gain(submission):
    assert submission.ndcg_at_k([0, 0], [1, 2], 2) == 0


def test_top_one(submission):
    assert submission.ndcg_at_k([1, 3], [2, 1], 1) == pytest.approx(1 / 7)


def test_tie_original_order(submission):
    assert submission.ndcg_at_k([1, 3], [1, 1], 1) == pytest.approx(1 / 7)


def test_bad_k(submission):
    with pytest.raises(ValueError):
        submission.ndcg_at_k([1], [1], 2)


def test_rank_discount(submission):
    want = (3 + 7 / math.log2(3)) / (7 + 3 / math.log2(3))
    assert submission.ndcg_at_k([3, 2], [0, 1], 2) == pytest.approx(want)
