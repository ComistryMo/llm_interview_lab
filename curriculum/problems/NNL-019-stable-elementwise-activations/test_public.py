import pytest

torch = pytest.importorskip("torch")


def test_relu_values_and_zero_derivative(submission):
    x = torch.tensor([-2., 0., 3.], dtype=torch.float64, requires_grad=True)
    y = submission.manual_relu(x)
    torch.testing.assert_close(y, torch.tensor([0., 0., 3.], dtype=x.dtype))
    y.sum().backward()
    torch.testing.assert_close(x.grad, torch.tensor([0., 0., 1.], dtype=x.dtype))


def test_sigmoid_extremes_backward_and_origin(submission):
    x = torch.tensor([-1000., 0., 1000.], dtype=torch.float64, requires_grad=True)
    y = submission.stable_sigmoid(x)
    torch.testing.assert_close(y, torch.tensor([0., .5, 1.], dtype=x.dtype))
    y.sum().backward()
    torch.testing.assert_close(x.grad, torch.tensor([0., .25, 0.], dtype=x.dtype))


def test_sigmoid_symmetry(submission):
    x = torch.tensor([-3., -.4, .2, 5.])
    torch.testing.assert_close(submission.stable_sigmoid(x) + submission.stable_sigmoid(-x), torch.ones_like(x))


def test_swiglu_gate_is_not_interchangeable(submission):
    gate = torch.tensor([0., 2.], dtype=torch.float64, requires_grad=True)
    up = torch.tensor([3., 0.], dtype=torch.float64, requires_grad=True)
    y = submission.swiglu_activation(gate, up)
    torch.testing.assert_close(y, torch.zeros_like(y))
    y.sum().backward()
    assert gate.grad[0].item() == pytest.approx(1.5)
    assert up.grad[1].item() == pytest.approx(2 / (1 + __import__("math").exp(-2)))


def test_shapes_dtype_nonmutation_and_empty(submission):
    x = torch.arange(-6., 6., dtype=torch.float64).reshape(3, 4).T
    before = x.clone()
    for fn in (submission.manual_relu, submission.stable_sigmoid):
        y = fn(x)
        assert y.shape == x.shape and y.dtype == x.dtype and y.device == x.device
        assert fn(torch.empty(0, 3)).shape == (0, 3)
    assert submission.stable_sigmoid(torch.tensor(0.)).shape == ()
    torch.testing.assert_close(x, before)
    with pytest.raises(ValueError):
        submission.swiglu_activation(torch.ones(2, 3), torch.ones(1, 3))
