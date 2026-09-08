import math
import pytest

torch = pytest.importorskip("torch")


def test_crossing_item_included(submission):
    _, p = submission.sample_filtered(torch.log(torch.tensor([[0.5, 0.3, 0.2]])), p=0.6)
    torch.testing.assert_close(p, torch.tensor([[0.625, 0.375, 0.0]]))


def test_topk_tie(submission):
    token, p = submission.sample_filtered(torch.zeros(1, 4), k=1)
    assert token.item() == 0
    torch.testing.assert_close(p, torch.tensor([[1.0, 0, 0, 0]]))


def test_only_valid_token(submission):
    assert (
        submission.sample_filtered(torch.tensor([[float("-inf"), 0.0]]))[0].item() == 1
    )


def test_all_disabled_rejected(submission):
    with pytest.raises(ValueError):
        submission.sample_filtered(torch.full((1, 3), float("-inf")))


def test_generator_reproducible(submission):
    x = torch.zeros(12, 5)
    a = submission.sample_filtered(x, generator=torch.Generator().manual_seed(8))[0]
    b = submission.sample_filtered(x, generator=torch.Generator().manual_seed(8))[0]
    assert torch.equal(a, b)


def test_p_one_keeps_all(submission):
    assert (
        submission.sample_filtered(torch.tensor([[0.0, -5.0, -10.0]]), p=1)[1] > 0
    ).all()
