import pytest
torch = pytest.importorskip("torch")


def test_decode_positions_and_padding(submission):
    out = submission.causal_padding_mask(torch.tensor([2, 3]), torch.arange(4),
        torch.tensor([[True, True]]), torch.tensor([[True, False, True, True]]))
    expected = torch.tensor([[[[True, False, True, False], [True, False, True, True]]]])
    torch.testing.assert_close(out, expected)
    assert out.dtype == torch.bool


def test_training_causality(submission):
    out = submission.causal_padding_mask(torch.arange(3), torch.arange(3),
        torch.ones(2, 3, dtype=torch.bool), torch.ones(2, 3, dtype=torch.bool))
    expected = torch.tensor([[1, 0, 0], [1, 1, 0], [1, 1, 1]], dtype=torch.bool)
    torch.testing.assert_close(out, expected.expand(2, 1, 3, 3))


def test_invalid_queries_and_all_padding(submission):
    out = submission.causal_padding_mask(torch.tensor([3, 4]), torch.arange(5),
        torch.tensor([[True, False], [True, True]]),
        torch.tensor([[True]*5, [False]*5]))
    assert not out[0, 0, 1].any() and not out[1].any()
    assert out[0, 0, 0].sum() == 4


def test_different_lengths_and_future_key(submission):
    out = submission.causal_padding_mask(torch.tensor([10]), torch.tensor([0, 9, 11]),
        torch.ones(1, 1, dtype=torch.bool), torch.ones(1, 3, dtype=torch.bool))
    torch.testing.assert_close(out, torch.tensor([[[[True, True, False]]]]))


def test_input_immutability(submission):
    args = [torch.arange(3), torch.arange(3), torch.ones(2, 3, dtype=torch.bool), torch.ones(2, 3, dtype=torch.bool)]
    copies = [a.clone() for a in args]
    out = submission.causal_padding_mask(*args)
    out.fill_(False)
    for actual, original in zip(args, copies):
        torch.testing.assert_close(actual, original)


@pytest.mark.parametrize("q,qvalid", [(torch.tensor([-1]), torch.ones(1, 1, dtype=torch.bool)),
    (torch.tensor([1.]), torch.ones(1, 1, dtype=torch.bool)),
    (torch.tensor([1]), torch.ones(1, 1)), (torch.tensor([1]), torch.ones(1, 2, dtype=torch.bool))])
def test_invalid_contract(submission, q, qvalid):
    with pytest.raises(ValueError):
        submission.causal_padding_mask(q, torch.arange(3), qvalid, torch.ones(1, 3, dtype=torch.bool))
