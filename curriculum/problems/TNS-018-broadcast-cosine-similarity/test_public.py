import pytest

torch = pytest.importorskip("torch")


def test_parallel_orthogonal_and_opposite(submission):
    a = torch.tensor([[1., 0.], [1., 0.], [1., 0.]], dtype=torch.float64)
    b = torch.tensor([[2., 0.], [0., 3.], [-1., 0.]], dtype=torch.float64)
    torch.testing.assert_close(submission.cosine_similarity(a, b), torch.tensor([1., 0., -1.], dtype=a.dtype))


def test_broadcast_and_explicit_axis(submission):
    a = torch.tensor([[[1., 0., 0.]], [[0., 1., 0.]]])
    b = torch.eye(3)[None]
    result = submission.cosine_similarity(a, b, dim=2)
    torch.testing.assert_close(result, torch.tensor([[1., 0., 0.], [0., 1., 0.]]))


def test_zero_and_separately_clipped_norms(submission):
    a = torch.tensor([[0., 0.], [.01, 0.]], dtype=torch.float64)
    b = torch.tensor([[2., 0.], [.01, 0.]], dtype=torch.float64)
    torch.testing.assert_close(submission.cosine_similarity(a, b, eps=.1), torch.tensor([0., .01], dtype=a.dtype))


def test_noncontiguous_input_and_empty_output(submission):
    a = torch.arange(1., 13., dtype=torch.float64).reshape(3, 4).T
    before = a.clone()
    result = submission.cosine_similarity(a, a, dim=0)
    assert result.shape == (3,) and result.device == a.device and result.dtype == a.dtype
    torch.testing.assert_close(result, torch.ones(3, dtype=a.dtype))
    torch.testing.assert_close(a, before)
    assert submission.cosine_similarity(torch.empty(0, 2), torch.ones(1, 2)).shape == (0,)


def test_gradients_through_broadcast(submission):
    a = torch.tensor([[1., 0.], [1., 0.]], dtype=torch.float64, requires_grad=True)
    b = torch.tensor([0., 1.], dtype=torch.float64, requires_grad=True)
    submission.cosine_similarity(a, b).sum().backward()
    torch.testing.assert_close(a.grad, torch.tensor([[0., 1.], [0., 1.]], dtype=a.dtype))
    torch.testing.assert_close(b.grad, torch.tensor([2., 0.], dtype=a.dtype))


@pytest.mark.parametrize("kwargs", [{"eps":0}, {"eps":float("nan")}, {"dim":2}])
def test_invalid_parameters(submission, kwargs):
    with pytest.raises(ValueError):
        submission.cosine_similarity(torch.ones(2, 3), torch.ones(2, 3), **kwargs)


def test_bad_broadcast_and_empty_reduction(submission):
    with pytest.raises(ValueError):
        submission.cosine_similarity(torch.ones(2, 3), torch.ones(4, 3))
    with pytest.raises(ValueError):
        submission.cosine_similarity(torch.empty(2, 0), torch.empty(2, 0))
