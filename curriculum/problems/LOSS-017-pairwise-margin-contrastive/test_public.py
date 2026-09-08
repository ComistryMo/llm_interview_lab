import pytest

torch = pytest.importorskip("torch")


def test_positive_pair_uses_squared_distance(submission):
    a = torch.tensor([[3., 4.]], dtype=torch.float64)
    result = submission.pairwise_contrastive(a, torch.zeros_like(a), torch.tensor([True]))
    assert result.item() == pytest.approx(12.5)


def test_negative_pair_margin_hinge(submission):
    a = torch.tensor([[.25], [2.]], dtype=torch.float64)
    result = submission.pairwise_contrastive(a, torch.zeros_like(a), torch.tensor([False, False]), reduction="none")
    torch.testing.assert_close(result, torch.tensor([.28125, 0.], dtype=a.dtype))


def test_reduction_and_label_direction(submission):
    a = torch.tensor([[1.], [0.]], dtype=torch.float64)
    b = torch.zeros_like(a)
    same = torch.tensor([True, False])
    values = submission.pairwise_contrastive(a, b, same, margin=2., reduction="none")
    torch.testing.assert_close(values, torch.tensor([.5, 2.], dtype=a.dtype))
    assert submission.pairwise_contrastive(a, b, same, 2., "sum").item() == pytest.approx(2.5)
    assert submission.pairwise_contrastive(a, b, same, 2., "mean").item() == pytest.approx(1.25)


def test_zero_distance_negative_pair_has_finite_zero_gradient(submission):
    a = torch.zeros(1, 2, dtype=torch.float64, requires_grad=True)
    b = torch.zeros(1, 2, dtype=torch.float64, requires_grad=True)
    loss = submission.pairwise_contrastive(a, b, torch.tensor([False]))
    assert loss.item() == pytest.approx(.5)
    loss.backward()
    torch.testing.assert_close(a.grad, torch.zeros_like(a))
    torch.testing.assert_close(b.grad, torch.zeros_like(b))


def test_signed_gradient_and_nonmutation(submission):
    a = torch.tensor([[.25]], dtype=torch.float64, requires_grad=True)
    b = torch.zeros_like(a, requires_grad=True)
    submission.pairwise_contrastive(a, b, torch.tensor([False])).backward()
    assert a.grad.item() == pytest.approx(-.75) and b.grad.item() == pytest.approx(.75)
    assert a.item() == .25 and b.item() == 0


@pytest.mark.parametrize("kwargs", [{"margin":0.}, {"margin":float("inf")}, {"reduction":"batchmean"}])
def test_invalid_parameters(submission, kwargs):
    with pytest.raises(ValueError):
        submission.pairwise_contrastive(torch.ones(2, 3), torch.ones(2, 3), torch.tensor([True, False]), **kwargs)


def test_invalid_labels_and_shapes(submission):
    with pytest.raises(ValueError):
        submission.pairwise_contrastive(torch.ones(2, 3), torch.ones(2, 3), torch.ones(2))
    with pytest.raises(ValueError):
        submission.pairwise_contrastive(torch.ones(2, 3), torch.ones(1, 3), torch.tensor([True, False]))
