import math
import pytest

torch = pytest.importorskip("torch")


def test_two_blocks(submission):
    a, m = submission.packing_masks(
        torch.tensor([0, 0, 1, 1, 1]),
        torch.tensor([0, 1, 0, 1, 2]),
        torch.ones(5, dtype=torch.bool),
    )
    want = torch.block_diag(
        torch.ones(2, 2, dtype=torch.bool).tril(),
        torch.ones(3, 3, dtype=torch.bool).tril(),
    )
    assert torch.equal(a, want)
    assert m.tolist() == [True, False, True, True, False]


def test_target_not_source_supervision(submission):
    _, m = submission.packing_masks(
        torch.tensor([0, 0, 0]), torch.arange(3), torch.tensor([False, False, True])
    )
    assert m.tolist() == [False, True, False]


def test_padding_excluded(submission):
    a, m = submission.packing_masks(
        torch.tensor([0, -1]), torch.tensor([0, 0]), torch.ones(2, dtype=torch.bool)
    )
    assert a.tolist() == [[True, False], [False, False]]
    assert not m.any()


def test_single_token(submission):
    a, m = submission.packing_masks(
        torch.tensor([0]), torch.tensor([0]), torch.tensor([True])
    )
    assert a.item() and not m.item()


def test_empty(submission):
    a, m = submission.packing_masks(
        torch.empty(0, dtype=torch.long),
        torch.empty(0, dtype=torch.long),
        torch.empty(0, dtype=torch.bool),
    )
    assert a.shape == (0, 0) and m.shape == (0,)
