import math
import pytest

torch = pytest.importorskip("torch")


def test_identity_analytic(submission):
    x = torch.eye(3, dtype=torch.float64)
    assert submission.paired_infonce(x, x, 1).item() == pytest.approx(
        math.log(math.e + 2) - 1
    )


def test_identical_features_log_n(submission):
    assert submission.paired_infonce(
        torch.ones(4, 3), torch.ones(4, 3)
    ).item() == pytest.approx(math.log(4))


def test_common_permutation(submission):
    a = torch.randn(4, 3)
    b = torch.randn_like(a)
    ids = torch.tensor([2, 0, 3, 1])
    torch.testing.assert_close(
        submission.paired_infonce(a, b), submission.paired_infonce(a[ids], b[ids])
    )


def test_positive_scaling_invariant(submission):
    a = torch.randn(4, 3)
    b = torch.randn_like(a)
    torch.testing.assert_close(
        submission.paired_infonce(a, b), submission.paired_infonce(a * 3, b * 7)
    )


def test_zero_vector_rejected(submission):
    with pytest.raises(ValueError):
        submission.paired_infonce(torch.zeros(2, 3), torch.ones(2, 3))
