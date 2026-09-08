import math
import pytest

torch = pytest.importorskip("torch")


def test_scalar_equation(submission):
    x = torch.tensor([[[2.0]]])
    y = submission.swiglu(
        x, torch.ones(1, 1), torch.ones(1, 1) * 3, torch.ones(1, 1) * 4
    )
    assert y.item() == pytest.approx(48 / (1 + math.exp(-2)))


def test_zero_gate(submission):
    assert (
        submission.swiglu(
            torch.ones(2, 3, 4), torch.zeros(5, 4), torch.ones(5, 4), torch.ones(4, 5)
        )
        .abs()
        .sum()
        == 0
    )


def test_zero_up(submission):
    assert (
        submission.swiglu(
            torch.ones(2, 3, 4), torch.ones(5, 4), torch.zeros(5, 4), torch.ones(4, 5)
        )
        .abs()
        .sum()
        == 0
    )


def test_no_token_mixing(submission):
    x = torch.randn(1, 3, 2)
    a = torch.randn(4, 2)
    b = torch.randn(4, 2)
    c = torch.randn(2, 4)
    y = submission.swiglu(x, a, b, c)
    changed = x.clone()
    changed[:, 2] += 7
    torch.testing.assert_close(y[:, :2], submission.swiglu(changed, a, b, c)[:, :2])


def test_token_loop(submission):
    x = torch.randn(2, 3, 4)
    a = torch.randn(5, 4)
    b = torch.randn(5, 4)
    c = torch.randn(4, 5)
    y = submission.swiglu(x, a, b, c)
    expected = torch.stack(
        [
            torch.stack(
                [
                    submission.swiglu(x[i : i + 1, j : j + 1], a, b, c)[0, 0]
                    for j in range(3)
                ]
            )
            for i in range(2)
        ]
    )
    torch.testing.assert_close(y, expected)
