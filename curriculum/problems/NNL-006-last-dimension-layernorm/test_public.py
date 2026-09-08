import math
import pytest

torch = pytest.importorskip("torch")


def test_framework_alignment(submission):
    x = torch.arange(24.0, dtype=torch.float64).reshape(2, 3, 4)
    g = torch.arange(4.0, dtype=torch.float64) + 1
    b = -g
    torch.testing.assert_close(
        submission.layer_norm(x, g, b),
        torch.nn.functional.layer_norm(x, (4,), g, b, 1e-5),
    )


def test_constant_beta(submission):
    x = torch.ones(2, 1, 3) * 7
    b = torch.tensor([1.0, 2.0, 3.0])
    torch.testing.assert_close(
        submission.layer_norm(x, torch.ones(3), b), b.expand_as(x)
    )


def test_d_one(submission):
    assert (
        submission.layer_norm(
            torch.tensor([[[3.0]]]), torch.tensor([2.0]), torch.tensor([4.0])
        ).item()
        == 4
    )


def test_zero_input(submission):
    assert torch.isfinite(
        submission.layer_norm(torch.zeros(1, 1, 2), torch.ones(2), torch.zeros(2))
    ).all()


def test_invalid_eps(submission):
    with pytest.raises(ValueError):
        submission.layer_norm(torch.ones(1, 1, 2), torch.ones(2), torch.zeros(2), 0)
