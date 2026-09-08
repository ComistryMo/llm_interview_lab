import math
import pytest

torch = pytest.importorskip("torch")


def test_huge_common_offset(submission):
    assert submission.token_cross_entropy(
        torch.tensor([[[1e20, 1e20]]]), torch.tensor([[0]])
    ).item() == pytest.approx(math.log(2))


def test_valid_token_mean(submission):
    x = torch.tensor([[[0.0, 0.0], [4.0, 0.0]], [[0.0, 0.0], [0.0, 0.0]]])
    y = torch.tensor([[0, -100], [1, -100]])
    assert submission.token_cross_entropy(x, y).item() == pytest.approx(math.log(2))


def test_empty_supervision_gradient_zero(submission):
    x = torch.randn(2, 3, 4, requires_grad=True)
    loss = submission.token_cross_entropy(x, torch.full((2, 3), -100))
    loss.backward()
    assert loss.item() == 0
    assert torch.equal(x.grad, torch.zeros_like(x))


def test_framework_values_and_gradients(submission):
    torch.manual_seed(5)
    x = torch.randn(2, 3, 4, dtype=torch.float64, requires_grad=True)
    y = torch.tensor([[1, 0, -100], [2, 3, 0]])
    a = submission.token_cross_entropy(x, y)
    b = torch.nn.functional.cross_entropy(x.reshape(-1, 4), y.flatten())
    torch.testing.assert_close(a, b)
    torch.testing.assert_close(
        torch.autograd.grad(a, x, retain_graph=True)[0], torch.autograd.grad(b, x)[0]
    )


def test_bad_target(submission):
    with pytest.raises(ValueError):
        submission.token_cross_entropy(torch.zeros(1, 1, 2), torch.tensor([[2]]))
