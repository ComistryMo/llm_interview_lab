import pytest
torch = pytest.importorskip("torch")


def test_uniform_logits(submission):
    x = torch.zeros(2, 3, dtype=torch.float64, requires_grad=True)
    out = submission.label_smoothed_cross_entropy(x, torch.tensor([2, -100]), .1)
    torch.testing.assert_close(out, torch.log(torch.tensor(3., dtype=x.dtype)))
    out.backward()
    torch.testing.assert_close(x.grad[1], torch.zeros(3, dtype=x.dtype))


@pytest.mark.parametrize("smoothing", [0., .15, 1.])
def test_reference_and_gradient(submission, smoothing):
    x = torch.tensor([[1., 3., -2.], [.2, -.4, .1], [2., 5., 1.]], dtype=torch.float64, requires_grad=True)
    target = torch.tensor([2, -7, 1])
    out = submission.label_smoothed_cross_entropy(x, target, smoothing, -7)
    ref = torch.nn.functional.cross_entropy(x, target, label_smoothing=smoothing, ignore_index=-7)
    torch.testing.assert_close(out, ref)
    torch.testing.assert_close(torch.autograd.grad(out, x)[0], torch.autograd.grad(ref, x)[0])


def test_all_ignored_is_differentiable_zero(submission):
    x = torch.randn(2, 3, requires_grad=True)
    out = submission.label_smoothed_cross_entropy(x, torch.full((2,), -100), .2)
    assert out.shape == () and out.item() == 0 and out.requires_grad
    out.backward()
    torch.testing.assert_close(x.grad, torch.zeros_like(x))


def test_large_logit_shift_and_no_mutation(submission):
    x = torch.tensor([[10001., 10000., 9998.], [-9999., -10000., -9998.]], dtype=torch.float64)
    target = torch.tensor([1, 2])
    before = x.clone()
    a = submission.label_smoothed_cross_entropy(x, target, .2)
    b = submission.label_smoothed_cross_entropy(x - x[:, :1], target, .2)
    assert torch.isfinite(a)
    torch.testing.assert_close(a, b)
    torch.testing.assert_close(x, before)
    assert a.dtype == x.dtype and a.device == x.device


@pytest.mark.parametrize("target,smoothing", [(torch.tensor([3, 0]), .1), (torch.tensor([0., 1.]), .1), (torch.tensor([0, 1]), -1.), (torch.tensor([0, 1]), float("nan"))])
def test_invalid_inputs(submission, target, smoothing):
    with pytest.raises(ValueError):
        submission.label_smoothed_cross_entropy(torch.zeros(2, 3), target, smoothing)
