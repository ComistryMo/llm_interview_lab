import pytest

torch = pytest.importorskip("torch")


def test_biases_only_the_head_axis(submission):
    scores = torch.zeros(2, 3, 2, 4)
    head_bias = torch.tensor([10.0, 20.0, 30.0])
    actual = submission.add_head_bias(scores, head_bias)
    expected = head_bias.reshape(1, 3, 1, 1).expand_as(scores)
    assert actual.shape == scores.shape
    assert torch.equal(actual, expected)


def test_matches_reference_on_nonzero_scores(submission):
    scores = torch.randn(2, 4, 3, 5)
    head_bias = torch.randn(4)
    expected = scores + head_bias[None, :, None, None]
    assert torch.allclose(submission.add_head_bias(scores, head_bias), expected)


def test_supports_non_contiguous_scores_and_gradients(submission):
    base = torch.randn(2, 3, 4, 5, dtype=torch.float64)
    scores = base.transpose(-1, -2).detach().requires_grad_()
    head_bias = torch.randn(3, dtype=torch.float64, requires_grad=True)
    actual = submission.add_head_bias(scores, head_bias)
    actual.sum().backward()
    assert torch.equal(scores.grad, torch.ones_like(scores))
    expected_count = scores.shape[0] * scores.shape[2] * scores.shape[3]
    assert torch.equal(head_bias.grad, torch.full_like(head_bias, expected_count))


@pytest.mark.parametrize(
    "scores,bias",
    [
        (torch.zeros(2, 3, 4), torch.zeros(3)),
        (torch.zeros(2, 3, 4, 5), torch.zeros(4)),
        (torch.zeros(2, 3, 4, 5), torch.zeros(1, 3)),
        (torch.zeros(2, 3, 4, 5), torch.zeros(3, dtype=torch.float64)),
    ],
)
def test_rejects_invalid_contract(submission, scores, bias):
    with pytest.raises(ValueError):
        submission.add_head_bias(scores, bias)


def test_preserves_device_dtype_and_inputs(submission):
    scores = torch.randn(1, 2, 3, 4, dtype=torch.float64)
    bias = torch.randn(2, dtype=torch.float64)
    before_scores, before_bias = scores.clone(), bias.clone()
    actual = submission.add_head_bias(scores, bias)
    assert actual.dtype == scores.dtype and actual.device == scores.device
    assert torch.equal(scores, before_scores)
    assert torch.equal(bias, before_bias)
