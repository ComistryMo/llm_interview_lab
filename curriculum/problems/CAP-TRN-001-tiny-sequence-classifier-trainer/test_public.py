import math
import pytest

torch = pytest.importorskip("torch")


def _toy():
    ids = torch.tensor([[1, 0, 0], [1, 1, 0], [2, 0, 0], [2, 2, 0]])
    mask = ids.ne(0)
    targets = torch.tensor([0, 0, 1, 1])
    return ids, mask, targets


def _run(submission, **overrides):
    ids, mask, targets = _toy()
    options = dict(vocab_size=4, num_classes=2, embedding_dim=5, batch_size=4,
                   epochs=18, lr=0.08, weight_decay=0.01, seed=17, dtype=torch.float64)
    options.update(overrides)
    return submission.train_tiny_sequence_classifier(ids, mask, targets, **options)


def test_return_contract_shapes_state_and_gradient_evidence(submission):
    result = _run(submission, epochs=2, batch_size=2)
    assert set(result) == {"loss_history", "embedding_weight", "classifier_weight", "classifier_bias", "optimizer_state", "last_gradient_norms"}
    assert result["embedding_weight"].shape == (4, 5)
    assert result["classifier_weight"].shape == (2, 5) and result["classifier_bias"].shape == (2,)
    assert len(result["loss_history"]) == 4
    for name in ("embedding", "weight", "bias"):
        state = result["optimizer_state"][name]
        assert state["step"] == 4 and not state["m"].requires_grad and not state["v"].requires_grad
        assert math.isfinite(result["last_gradient_norms"][name]) and result["last_gradient_norms"][name] > 0


def test_fixed_seed_is_reproducible_without_changing_global_rng(submission):
    torch.manual_seed(991)
    before = torch.random.get_rng_state().clone()
    first = _run(submission, epochs=3)
    assert torch.equal(torch.random.get_rng_state(), before)
    second = _run(submission, epochs=3)
    assert first["loss_history"] == second["loss_history"]
    for key in ("embedding_weight", "classifier_weight", "classifier_bias"):
        assert torch.equal(first[key], second[key])


def test_loss_decreases_on_separable_toy_data(submission):
    history = _run(submission, epochs=30, weight_decay=0.0)["loss_history"]
    assert len(history) == 30 and history[-1] < history[0] * 0.35


@pytest.mark.parametrize("batch_size", [1, 3, 8])
def test_padding_and_different_batch_sizes(submission, batch_size):
    result = _run(submission, epochs=3, batch_size=batch_size)
    expected_steps = 3 * math.ceil(4 / batch_size)
    assert len(result["loss_history"]) == expected_steps
    assert result["optimizer_state"]["embedding"]["step"] == expected_steps
    assert torch.isfinite(torch.tensor(result["loss_history"])).all()


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_cpu_and_dtype_contract(submission, dtype):
    result = _run(submission, epochs=2, dtype=dtype)
    for key in ("embedding_weight", "classifier_weight", "classifier_bias"):
        assert result[key].dtype == dtype and result[key].device.type == "cpu"
    assert all(isinstance(value, float) for value in result["loss_history"])


def test_inputs_are_not_mutated(submission):
    ids, mask, targets = _toy()
    before = (ids.clone(), mask.clone(), targets.clone())
    submission.train_tiny_sequence_classifier(
        ids, mask, targets, vocab_size=4, num_classes=2, epochs=2, batch_size=3
    )
    assert all(torch.equal(value, original) for value, original in zip((ids, mask, targets), before))


@pytest.mark.parametrize(
    "change",
    [
        {"input_ids": torch.tensor([[1.0]])},
        {"attention_mask": torch.tensor([[1]])},
        {"attention_mask": torch.tensor([[False, False, False]]).expand(4, -1)},
        {"targets": torch.tensor([0, 0, 1, 2])},
        {"vocab_size": True},
        {"batch_size": 0},
        {"lr": float("inf")},
        {"weight_decay": -0.1},
        {"dtype": torch.int64},
    ],
)
def test_invalid_contract_raises_before_training(submission, change):
    ids, mask, targets = _toy()
    arguments = dict(input_ids=ids, attention_mask=mask, targets=targets,
                     vocab_size=4, num_classes=2, epochs=1)
    arguments.update(change)
    with pytest.raises(ValueError):
        submission.train_tiny_sequence_classifier(**arguments)
