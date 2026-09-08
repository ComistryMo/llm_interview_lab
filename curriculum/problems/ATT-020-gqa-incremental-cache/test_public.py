import math
import pytest

torch = pytest.importorskip("torch")


@pytest.mark.parametrize("chunks", [[7], [1] * 7, [3, 1, 3]])
def test_full_and_chunks(submission, chunks):
    torch.manual_seed(1)
    q = torch.randn(1, 8, 7, 2)
    k = torch.randn(1, 2, 7, 2)
    v = torch.randn(1, 2, 7, 2)
    full, _ = submission.cached_gqa(q, k, v)
    cache = None
    out = []
    start = 0
    for n in chunks:
        y, cache = submission.cached_gqa(
            q[:, :, start : start + n],
            k[:, :, start : start + n],
            v[:, :, start : start + n],
            cache,
        )
        out.append(y)
        start += n
        assert cache[0].shape == (1, 2, start, 2)
    torch.testing.assert_close(torch.cat(out, 2), full)


def test_decode_can_see_history(submission):
    q = torch.zeros(1, 2, 1, 1)
    k = torch.zeros(1, 1, 1, 1)
    y, _ = submission.cached_gqa(
        q, k, torch.tensor([[[[4.0]]]]), (k, torch.tensor([[[[2.0]]]]))
    )
    torch.testing.assert_close(y, torch.full_like(y, 3))


def test_group_contiguity(submission):
    q = torch.zeros(1, 4, 1, 1)
    k = torch.zeros(1, 2, 1, 1)
    v = torch.tensor([[[[2.0]], [[7.0]]]])
    y, _ = submission.cached_gqa(q, k, v)
    torch.testing.assert_close(y.flatten(), torch.tensor([2.0, 2.0, 7.0, 7.0]))


def test_old_cache_unchanged(submission):
    cache = (torch.ones(1, 1, 2, 1), torch.ones(1, 1, 2, 1))
    submission.cached_gqa(
        torch.ones(1, 2, 1, 1), torch.zeros(1, 1, 1, 1), torch.zeros(1, 1, 1, 1), cache
    )
    assert cache[0].shape[2] == 2 and cache[0].sum() == 2


def test_bad_heads(submission):
    with pytest.raises(ValueError):
        submission.cached_gqa(
            torch.zeros(1, 3, 1, 2), torch.zeros(1, 2, 1, 2), torch.zeros(1, 2, 1, 2)
        )
