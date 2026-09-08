import math
import pytest

torch = pytest.importorskip("torch")


def test_shift_and_mask(submission):
    logits = torch.log(torch.tensor([[[0.8, 0.2], [0.3, 0.7], [0.5, 0.5]]]))
    tokens = torch.tensor([[0, 1, 0]])
    mask = torch.tensor([[False, True, True]])
    assert submission.completion_logp(logits, tokens, mask).item() == pytest.approx(
        math.log(0.2 * 0.3)
    )


def test_padding_not_gathered(submission):
    x = torch.zeros(1, 3, 2)
    token = torch.tensor([[0, 1, -100]])
    mask = torch.tensor([[False, True, False]])
    assert submission.completion_logp(x, token, mask).item() == pytest.approx(
        -math.log(2)
    )


def test_empty_response_rejected(submission):
    with pytest.raises(ValueError):
        submission.completion_logp(
            torch.zeros(1, 2, 2),
            torch.zeros(1, 2, dtype=torch.long),
            torch.zeros(1, 2, dtype=torch.bool),
        )


def test_policy_equals_reference(submission):
    p = torch.tensor([[-2.0, -3.0]])
    assert submission.paired_dpo(p, p).item() == pytest.approx(math.log(2))


def test_better_chosen_lowers_loss(submission):
    r = torch.zeros(1, 2)
    assert submission.paired_dpo(torch.tensor([[2.0, 0.0]]), r) < submission.paired_dpo(
        r, r
    )


def test_reference_stopped(submission):
    p = torch.zeros(1, 2, requires_grad=True)
    r = torch.ones(1, 2, requires_grad=True)
    submission.paired_dpo(p, r).backward()
    assert r.grad is None
    assert p.grad is not None
