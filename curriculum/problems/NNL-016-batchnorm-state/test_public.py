import math
import pytest

torch = pytest.importorskip("torch")


def test_variance_estimators(submission):
    x = torch.tensor([[[[0.0, 2.0]]]])
    y, m, v = submission.batch_norm(
        x, torch.ones(1), torch.zeros(1), torch.zeros(1), torch.ones(1), momentum=0.5
    )
    torch.testing.assert_close(y, torch.tensor([[[[-1.0, 1.0]]]]) / math.sqrt(1 + 1e-5))
    assert m.item() == 0.5 and v.item() == 1.5


def test_bn1d_constant(submission):
    x = torch.ones(3, 2) * 4
    y, _, _ = submission.batch_norm(
        x, torch.ones(2), torch.tensor([2.0, 3.0]), torch.zeros(2), torch.ones(2)
    )
    torch.testing.assert_close(y, torch.tensor([[2.0, 3.0]]).expand(3, 2))


def test_eval_uses_running_statistics(submission):
    x = torch.tensor([[4.0, 7.0]])
    y, m, v = submission.batch_norm(
        x,
        torch.ones(2),
        torch.zeros(2),
        torch.tensor([2.0, 3.0]),
        torch.tensor([4.0, 4.0]),
        False,
    )
    torch.testing.assert_close(y, torch.tensor([[2.0, 4.0]]) / math.sqrt(4 + 1e-5))
    torch.testing.assert_close(m, torch.tensor([2.0, 3.0]))


def test_running_input_not_mutated(submission):
    m = torch.zeros(2)
    v = torch.ones(2)
    submission.batch_norm(torch.randn(3, 2), torch.ones(2), torch.zeros(2), m, v)
    torch.testing.assert_close(m, torch.zeros(2))
    torch.testing.assert_close(v, torch.ones(2))


def test_single_training_value_rejected(submission):
    with pytest.raises(ValueError):
        submission.batch_norm(
            torch.ones(1, 1),
            torch.ones(1),
            torch.zeros(1),
            torch.zeros(1),
            torch.ones(1),
        )
