import math
import pytest

torch = pytest.importorskip("torch")


def test_zero_query_means_values(submission):
    eye = torch.eye(4)
    q = torch.zeros(1, 2, 4)
    c = torch.arange(12.0).reshape(1, 3, 4)
    y = submission.projected_mha(q, c, eye, eye, eye, eye, 2)
    torch.testing.assert_close(y, c.mean(1, keepdim=True).expand(1, 2, 4))


def test_all_masked_zero(submission):
    eye = torch.eye(2)
    x = torch.ones(1, 2, 2)
    y = submission.projected_mha(
        x, x, eye, eye, eye, eye, 1, torch.zeros(2, 2, dtype=torch.bool)
    )
    assert torch.equal(y, torch.zeros_like(y))


def test_all_masked_backward_has_zero_finite_gradients(submission):
    x = torch.randn(1, 2, 4, dtype=torch.float64, requires_grad=True)
    weights = [torch.eye(4, dtype=torch.float64, requires_grad=True) for _ in range(4)]
    y = submission.projected_mha(x, x, *weights, 2, torch.zeros(2, 2, dtype=torch.bool))
    y.sum().backward()
    for tensor in [x, *weights]:
        assert tensor.grad is not None
        assert torch.equal(tensor.grad, torch.zeros_like(tensor))


def test_masked_values_ignored(submission):
    eye = torch.eye(2)
    q = torch.zeros(1, 1, 2)
    c = torch.tensor([[[2.0, 4.0], [800.0, 900.0]]])
    y = submission.projected_mha(
        q, c, eye, eye, eye, eye, 1, torch.tensor([[True, False]])
    )
    torch.testing.assert_close(y, c[:, :1])


def test_output_projection(submission):
    eye = torch.eye(2)
    x = torch.ones(1, 1, 2)
    y = submission.projected_mha(x, x, eye, eye, eye, eye * 3, 1)
    torch.testing.assert_close(y, x * 3)


def test_invalid_heads(submission):
    eye = torch.eye(3)
    x = torch.ones(1, 1, 3)
    with pytest.raises(ValueError):
        submission.projected_mha(x, x, eye, eye, eye, eye, 2)
