import math
import pytest

torch = pytest.importorskip("torch")


def weights():
    torch.manual_seed(36)
    return {
        **{
            k: torch.randn(4, 4, dtype=torch.float64) * 0.2
            for k in ["wq", "wk", "wv", "wo"]
        },
        **{k: torch.ones(4, dtype=torch.float64) for k in ["norm1", "norm2"]},
        "w_gate": torch.randn(6, 4, dtype=torch.float64) * 0.2,
        "w_up": torch.randn(6, 4, dtype=torch.float64) * 0.2,
        "w_down": torch.randn(4, 6, dtype=torch.float64) * 0.2,
    }


def test_zero_branches_identity(submission):
    w = weights()
    w["wo"].zero_()
    w["w_down"].zero_()
    x = torch.randn(1, 3, 4, dtype=torch.float64)
    y, _ = submission.decoder_block(x, w, 2, torch.arange(3)[None])
    torch.testing.assert_close(y, x)


def test_future_cannot_change_past(submission):
    w = weights()
    x = torch.randn(1, 4, 4, dtype=torch.float64)
    y, _ = submission.decoder_block(x, w, 2, torch.arange(4)[None])
    changed = x.clone()
    changed[:, 2:] += 10
    z, _ = submission.decoder_block(changed, w, 2, torch.arange(4)[None])
    torch.testing.assert_close(y[:, :2], z[:, :2])


def test_incremental_matches_full(submission):
    w = weights()
    x = torch.randn(1, 5, 4, dtype=torch.float64)
    y, _ = submission.decoder_block(x, w, 2, torch.arange(5)[None])
    cache = None
    out = []
    for i in range(5):
        z, cache = submission.decoder_block(
            x[:, i : i + 1], w, 2, torch.tensor([[i]]), cache
        )
        out.append(z)
    torch.testing.assert_close(torch.cat(out, 1), y)
    assert cache[0].shape == (1, 2, 5, 2)


def test_norm_parameters_independent(submission):
    w = weights()
    x = torch.randn(1, 2, 4, dtype=torch.float64)
    y, _ = submission.decoder_block(x, w, 2, torch.arange(2)[None])
    w["norm2"] = w["norm2"] * 2
    z, _ = submission.decoder_block(x, w, 2, torch.arange(2)[None])
    assert not torch.allclose(y, z)


def test_backward_connected(submission):
    w = weights()
    x = torch.randn(1, 2, 4, dtype=torch.float64, requires_grad=True)
    y, _ = submission.decoder_block(x, w, 2, torch.arange(2)[None])
    y.square().sum().backward()
    assert torch.isfinite(x.grad).all() and x.grad.abs().sum() > 0
