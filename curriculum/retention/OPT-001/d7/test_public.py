import math
import pytest

torch = pytest.importorskip("torch")


def test_below_threshold_matches_plain_sgd(submission):
    p = torch.tensor([1.0, -1.0], requires_grad=True)
    p.grad = torch.tensor([0.3, 0.4])
    norm = submission.clipped_sgd_step([p], 0.2, 1.0)
    assert norm == pytest.approx(0.5)
    assert torch.allclose(p, torch.tensor([0.94, -1.08]))


def test_global_norm_scales_all_gradients_together(submission):
    a = torch.tensor([1.0], requires_grad=True)
    b = torch.tensor([2.0], requires_grad=True)
    a.grad, b.grad = torch.tensor([3.0]), torch.tensor([4.0])
    norm = submission.clipped_sgd_step([a, b], 0.1, 2.5)
    assert norm == pytest.approx(5.0)
    assert torch.allclose(a, torch.tensor([0.85]))
    assert torch.allclose(b, torch.tensor([1.8]))


def test_missing_gradients_are_skipped(submission):
    a = torch.tensor([1.0], requires_grad=True)
    b = torch.tensor([2.0], requires_grad=True)
    b.grad = torch.tensor([2.0])
    assert submission.clipped_sgd_step([a, b], 0.25, 10.0) == pytest.approx(2.0)
    assert a.item() == 1.0 and b.item() == pytest.approx(1.5)


def test_zero_or_absent_gradients_return_zero_norm(submission):
    a = torch.tensor([1.0], requires_grad=True)
    b = torch.tensor([2.0], requires_grad=True)
    b.grad = torch.zeros(1)
    assert submission.clipped_sgd_step([a, b], 0.1, 1.0) == 0.0
    assert a.item() == 1.0 and b.item() == 2.0


def test_gradient_tensors_are_not_mutated(submission):
    p = torch.tensor([1.0, 2.0], requires_grad=True)
    p.grad = torch.tensor([30.0, 40.0])
    before = p.grad.clone()
    submission.clipped_sgd_step([p], 0.1, 1.0)
    assert torch.equal(p.grad, before)


def test_matches_torch_clip_then_sgd_reference(submission):
    actual = torch.tensor([1.0, -2.0], dtype=torch.float64, requires_grad=True)
    expected = torch.nn.Parameter(actual.detach().clone())
    gradient = torch.tensor([6.0, 8.0], dtype=torch.float64)
    actual.grad = gradient.clone(); expected.grad = gradient.clone()
    submission.clipped_sgd_step([actual], 0.03, 2.0)
    torch.nn.utils.clip_grad_norm_([expected], 2.0)
    torch.optim.SGD([expected], lr=0.03).step()
    assert torch.allclose(actual, expected, atol=1e-8)


@pytest.mark.parametrize("parameters,lr,max_norm", [([], 0.1, 1.0), ([torch.ones(1)], 0.0, 1.0), ([torch.ones(1)], 0.1, 0.0), ([torch.ones(1)], True, 1.0)])
def test_invalid_contract_raises_before_any_update(submission, parameters, lr, max_norm):
    with pytest.raises(ValueError):
        submission.clipped_sgd_step(parameters, lr, max_norm)
