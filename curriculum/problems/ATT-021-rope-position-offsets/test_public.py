import math
import pytest

torch = pytest.importorskip("torch")


def test_position_zero_identity(submission):
    x = torch.randn(2, 3, 4, 6)
    torch.testing.assert_close(
        submission.rope_positions(x, torch.zeros(2, 4, dtype=torch.long)), x
    )


def test_pair_rotation(submission):
    x = torch.tensor([[[[1.0, 0.0]]]])
    got = submission.rope_positions(x, torch.tensor([[1]]))
    torch.testing.assert_close(got.flatten(), torch.tensor([math.cos(1), math.sin(1)]))


def test_norm_preserved(submission):
    x = torch.randn(2, 2, 4, 8)
    y = submission.rope_positions(x, torch.arange(4).expand(2, 4))
    torch.testing.assert_close(x.square().sum(-1), y.square().sum(-1))


def test_chunk_offset(submission):
    x = torch.randn(1, 2, 6, 4)
    p = torch.arange(6)[None]
    full = submission.rope_positions(x, p)
    torch.testing.assert_close(
        full[:, :, 4:], submission.rope_positions(x[:, :, 4:], p[:, 4:])
    )


def test_odd_dimension(submission):
    with pytest.raises(ValueError):
        submission.rope_positions(
            torch.ones(1, 1, 1, 3), torch.zeros(1, 1, dtype=torch.long)
        )
