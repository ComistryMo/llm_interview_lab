import math
import pytest

np = pytest.importorskip("numpy")


def test_seed_repeats(submission):
    x = np.arange(20.0).reshape(10, 2)
    np.testing.assert_array_equal(
        submission.kmeans_plus_plus(x, 4, 7), submission.kmeans_plus_plus(x, 4, 7)
    )


def test_unique_indices(submission):
    assert len(set(submission.kmeans_plus_plus(np.ones((5, 2)), 5))) == 5


def test_identical_deterministic_fill(submission):
    first = int(np.random.default_rng(0).integers(4))
    want = [first] + [i for i in range(4) if i != first]
    assert submission.kmeans_plus_plus(np.zeros((4, 2)), 4).tolist() == want


def test_single_center(submission):
    assert submission.kmeans_plus_plus(np.ones((1, 2)), 1).tolist() == [0]


def test_invalid_k(submission):
    with pytest.raises(ValueError):
        submission.kmeans_plus_plus(np.ones((2, 2)), 3)
