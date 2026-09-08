import math
import pytest

torch = pytest.importorskip("torch")


def test_unequal_counts(submission):
    w = torch.tensor(1.0, requires_grad=True)
    value = submission.accumulate_token_gradients(
        [lambda: w * 1, lambda: w * 9], [1, 3]
    )
    assert value == 2.5
    assert w.grad.item() == 2.5


def test_zero_window_no_calls(submission):
    def forbidden():
        raise AssertionError("empty window must not call model")

    assert submission.accumulate_token_gradients([forbidden], [0]) == 0


def test_backward_before_next_microbatch(submission):
    w = torch.tensor(1.0, requires_grad=True)

    def second():
        assert w.grad is not None
        return w * 3

    submission.accumulate_token_gradients([lambda: w, second], [1, 1])
    assert w.grad.item() == 2


def test_preserve_existing_gradient(submission):
    w = torch.tensor(1.0, requires_grad=True)
    w.grad = torch.tensor(2.0)
    submission.accumulate_token_gradients([lambda: w], [1])
    assert w.grad.item() == 3


def test_invalid_counts(submission):
    with pytest.raises(ValueError):
        submission.accumulate_token_gradients([], [-1])


def test_ddp_mean_compensation(submission):
    w = torch.tensor(1.0, requires_grad=True)
    value = submission.accumulate_token_gradients(
        [lambda: w * 6], [2], global_token_count=6, world_size=3
    )
    assert value == 1
    assert w.grad.item() == 3
