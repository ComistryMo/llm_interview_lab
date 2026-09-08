import math
import pytest

torch = pytest.importorskip("torch")


def test_equal_distributions(submission):
    x = torch.randn(2, 3, 4)
    assert (
        submission.masked_distillation_kl(
            x, x, torch.ones(2, 3, dtype=torch.bool)
        ).abs()
        < 1e-6
    )


def test_forward_direction(submission):
    p = torch.tensor([[[0.8, 0.2]]], dtype=torch.float64)
    q = torch.tensor([[[0.5, 0.5]]], dtype=torch.float64)
    expected = (p * (p.log() - q.log())).sum()
    torch.testing.assert_close(
        submission.masked_distillation_kl(p.log(), q.log(), torch.tensor([[True]])),
        expected,
    )


def test_padding_invariant(submission):
    t = torch.randn(1, 3, 4)
    s = torch.randn_like(t)
    mask = torch.tensor([[True, False, False]])
    torch.testing.assert_close(
        submission.masked_distillation_kl(t, s, mask),
        submission.masked_distillation_kl(t[:, :1], s[:, :1], mask[:, :1]),
    )


def test_teacher_no_gradient(submission):
    t = torch.randn(1, 2, 3, requires_grad=True)
    s = torch.randn_like(t, requires_grad=True)
    submission.masked_distillation_kl(
        t, s, torch.ones(1, 2, dtype=torch.bool), 2
    ).backward()
    assert t.grad is None and torch.isfinite(s.grad).all()


def test_empty_mask_connected_zero(submission):
    x = torch.randn(1, 2, 3, requires_grad=True)
    y = submission.masked_distillation_kl(x, x, torch.zeros(1, 2, dtype=torch.bool))
    y.backward()
    assert y == 0 and x.grad.abs().sum() == 0
