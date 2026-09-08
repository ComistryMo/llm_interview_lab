import math
import pytest

torch = pytest.importorskip("torch")


@pytest.mark.parametrize("block", [1, 3, 50])
def test_dense_equivalence(submission, block):
    torch.manual_seed(2)
    q = torch.randn(4, 3, dtype=torch.float64)
    k = torch.randn(7, 3, dtype=torch.float64)
    v = torch.randn(7, 2, dtype=torch.float64)
    torch.testing.assert_close(
        submission.streaming_attention(q, k, v, block),
        (q @ k.T / math.sqrt(3)).softmax(-1) @ v,
    )


def test_zero_query_mean(submission):
    q = torch.zeros(2, 3)
    k = torch.randn(5, 3)
    v = torch.arange(10.0).reshape(5, 2)
    torch.testing.assert_close(
        submission.streaming_attention(q, k, v, 2), v.mean(0).expand(2, 2)
    )


def test_no_autograd_graph(submission):
    q = torch.randn(2, 3, requires_grad=True)
    y = submission.streaming_attention(q, q, q, 1)
    assert not y.requires_grad


def test_large_scores(submission):
    q = torch.tensor([[100.0, 100.0]])
    k = torch.tensor([[100.0, 100.0], [-100.0, -100.0]])
    v = torch.tensor([[2.0], [8.0]])
    torch.testing.assert_close(
        submission.streaming_attention(q, k, v, 1), torch.tensor([[2.0]])
    )


def test_bad_block(submission):
    with pytest.raises(ValueError):
        submission.streaming_attention(
            torch.ones(1, 1), torch.ones(1, 1), torch.ones(1, 1), 0
        )
