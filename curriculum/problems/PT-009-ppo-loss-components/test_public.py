import math
import pytest

torch = pytest.importorskip("torch")


def case(submission, new=0.0, adv=1.0, mask=None):
    mask = torch.tensor([[True]]) if mask is None else mask
    x = torch.tensor([[new]])
    z = torch.zeros(1, 1)
    return submission.ppo_loss(
        x, z, torch.full((1, 1), adv), z, torch.ones(1, 1), torch.zeros(1, 1, 3), mask
    )


def test_ratio_one(submission):
    assert case(submission)["policy"].item() == -1


def test_negative_advantage(submission):
    assert case(submission, math.log(1.5), -1.0)["policy"].item() == pytest.approx(1.5)


def test_entropy_uniform(submission):
    assert case(submission)["entropy"].item() == pytest.approx(math.log(3))


def test_value_and_total(submission):
    r = case(submission)
    assert r["value"].item() == 0.5
    torch.testing.assert_close(
        r["loss"], r["policy"] + 0.5 * r["value"] - 0.01 * r["entropy"]
    )


def test_empty_mask(submission):
    with pytest.raises(ValueError):
        case(submission, mask=torch.tensor([[False]]))


def test_padding_ignored(submission):
    x = torch.zeros(1, 2)
    a = torch.tensor([[1.0, 100.0]])
    r = submission.ppo_loss(
        x, x, a, x, a, torch.zeros(1, 2, 3), torch.tensor([[True, False]])
    )
    assert r["policy"].item() == -1 and r["value"].item() == 0.5


def test_masked_extreme_log_ratio_has_no_gradient(submission):
    new = torch.tensor([[0.0, 1000.0]], dtype=torch.float64, requires_grad=True)
    z = torch.zeros_like(new)
    result = submission.ppo_loss(
        new,
        z,
        torch.ones_like(new),
        z,
        z,
        torch.zeros(1, 2, 3, dtype=torch.float64),
        torch.tensor([[True, False]]),
    )
    result["loss"].backward()
    torch.testing.assert_close(
        new.grad, torch.tensor([[-1.0, 0.0]], dtype=torch.float64)
    )
