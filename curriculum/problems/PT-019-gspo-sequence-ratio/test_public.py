import math
import pytest
torch = pytest.importorskip("torch")


def test_equal_policies_closed_form(submission):
    x = torch.full((1, 2, 2), -2., dtype=torch.float64)
    out = submission.gspo_sequence_loss(x, x.clone(), torch.tensor([[2., -1.]], dtype=x.dtype), torch.ones_like(x, dtype=torch.bool))
    torch.testing.assert_close(out, torch.tensor(-.5, dtype=x.dtype))


def test_geometric_not_arithmetic_ratio(submission):
    old = torch.full((1, 1, 2), -4., dtype=torch.float64)
    cur = old + torch.tensor([[[math.log(4), -math.log(4)]]])
    out = submission.gspo_sequence_loss(cur, old, torch.ones(1, 1, dtype=old.dtype), torch.ones_like(old, dtype=torch.bool))
    torch.testing.assert_close(out, torch.tensor(-1., dtype=old.dtype))


def test_signed_clipping_and_sequence_weighting(submission):
    old = torch.full((1, 2, 3), -3., dtype=torch.float64)
    cur = old + math.log(2)
    mask = torch.tensor([[[True, False, False], [True, True, True]]])
    advantages = torch.tensor([[1., -1.]], dtype=old.dtype)
    # positive surrogate clips to 1.2, negative surrogate stays -2
    out = submission.gspo_sequence_loss(cur, old, advantages, mask, .2)
    torch.testing.assert_close(out, torch.tensor(.4, dtype=old.dtype))


def test_gradients_only_current_valid_tokens(submission):
    old = torch.full((1, 2, 3), -3., dtype=torch.float64, requires_grad=True)
    cur = torch.full((1, 2, 3), -2.98, dtype=torch.float64, requires_grad=True)
    adv = torch.tensor([[1., -2.]], dtype=torch.float64, requires_grad=True)
    mask = torch.tensor([[[True, False, False], [True, True, True]]])
    result = submission.gspo_sequence_loss(cur, old, adv, mask)
    result.backward()
    assert old.grad is None and adv.grad is None
    assert cur.grad[mask].abs().sum() > 0 and cur.grad[~mask].abs().sum() == 0


def test_padding_values_and_inputs_not_mutated(submission):
    old = torch.full((1, 1, 2), -3.)
    cur = torch.tensor([[[-2.99, -20.]]])
    mask = torch.tensor([[[True, False]]])
    adv = torch.ones(1, 1)
    saved = [x.clone() for x in (cur, old, adv, mask)]
    a = submission.gspo_sequence_loss(cur, old, adv, mask)
    changed = cur.clone()
    changed[~mask] = -200
    b = submission.gspo_sequence_loss(changed, old, adv, mask)
    torch.testing.assert_close(a, b)
    for x, before in zip((cur, old, adv, mask), saved):
        torch.testing.assert_close(x, before)
    assert a.dtype == cur.dtype and a.device == cur.device


@pytest.mark.parametrize("case", ["empty_sequence", "dtype", "adv_shape", "eps", "nan"])
def test_invalid_contract(submission, case):
    cur = torch.full((1, 2, 3), -2.)
    old, adv, mask, eps = cur.clone(), torch.ones(1, 2), torch.ones_like(cur, dtype=torch.bool), .2
    if case == "empty_sequence": mask[0, 1] = False
    if case == "dtype": old = old.double()
    if case == "adv_shape": adv = torch.ones(1, 2, 1)
    if case == "eps": eps = 0.
    if case == "nan": cur[0, 0, 0] = float("nan")
    with pytest.raises(ValueError):
        submission.gspo_sequence_loss(cur, old, adv, mask, eps)
