import pytest

torch = pytest.importorskip("torch")


def _reference(rewards, valid, eps):
    work = rewards.detach().to(torch.float64)
    out = torch.zeros_like(work)
    for row in range(work.shape[0]):
        keep = valid[row]
        n = int(keep.sum())
        if n == 0:
            continue
        values = work[row][keep]
        if not torch.isfinite(values).all():
            raise ValueError
        mean = values.mean()
        std = values.std(unbiased=False)
        if n >= 2 and std > eps:
            out[row][keep] = (values - mean) / std
    return out.to(rewards.dtype), valid.clone()


def test_excludes_invalid_rewards_from_group_statistics(submission):
    rewards = torch.tensor([[1.0, 3.0, 1000.0], [2.0, 2.0, -99.0]], dtype=torch.float64)
    valid = torch.tensor([[1, 1, 0], [1, 1, 0]], dtype=torch.bool)
    advantages, kept = submission.normalize_valid_group_rewards(rewards, valid)
    expected, expected_mask = _reference(rewards, valid, 1e-6)
    assert torch.allclose(advantages, expected, atol=1e-12)
    assert torch.equal(kept, expected_mask)
    assert advantages[0, 2] == 0 and advantages[1, 2] == 0


def test_invalid_nan_sentinel_is_ignored_and_inputs_are_not_mutated(submission):
    rewards = torch.tensor([[1.0, float("nan"), 5.0]], dtype=torch.float32)
    valid = torch.tensor([[1, 0, 1]], dtype=torch.bool)
    rewards_before, valid_before = rewards.clone(), valid.clone()
    advantages, kept = submission.normalize_valid_group_rewards(rewards, valid)
    assert torch.isfinite(advantages).all()
    assert torch.allclose(advantages[0, [0, 2]], torch.tensor([-1.0, 1.0]), atol=1e-6)
    assert torch.equal(kept, valid)
    assert torch.equal(valid, valid_before)
    assert torch.equal(torch.nan_to_num(rewards), torch.nan_to_num(rewards_before))


@pytest.mark.parametrize(
    "rewards",
    [
        torch.tensor([[4.0]], dtype=torch.float64),
        torch.tensor([[2.0, 2.0, 2.0]], dtype=torch.float64),
        torch.tensor([[1.0, 1.0]], dtype=torch.float64),
    ],
)
def test_singleton_and_zero_variance_are_finite_zero(submission, rewards):
    valid = torch.ones_like(rewards, dtype=torch.bool)
    advantages, kept = submission.normalize_valid_group_rewards(rewards, valid)
    assert torch.equal(advantages, torch.zeros_like(rewards))
    assert torch.equal(kept, valid)


def test_empty_group_is_reported_by_mask_but_does_not_poison_other_rows(submission):
    rewards = torch.tensor([[1.0, 3.0], [float("nan"), float("inf")]], dtype=torch.float64)
    valid = torch.tensor([[1, 1], [0, 0]], dtype=torch.bool)
    advantages, kept = submission.normalize_valid_group_rewards(rewards, valid)
    assert torch.allclose(advantages[0], torch.tensor([-1.0, 1.0], dtype=torch.float64))
    assert not kept[1].any() and torch.equal(advantages[1], torch.zeros(2, dtype=torch.float64))


def test_all_invalid_batch_raises(submission):
    rewards = torch.zeros(2, 3)
    valid = torch.zeros(2, 3, dtype=torch.bool)
    with pytest.raises(ValueError):
        submission.normalize_valid_group_rewards(rewards, valid)


def test_output_preserves_dtype_device_and_detaches_rewards(submission):
    rewards = torch.tensor([[0.0, 2.0, 4.0]], dtype=torch.float32, requires_grad=True)
    valid = torch.ones(1, 3, dtype=torch.bool)
    advantages, kept = submission.normalize_valid_group_rewards(rewards, valid)
    assert advantages.dtype == rewards.dtype and advantages.device == rewards.device
    assert kept.dtype == torch.bool and kept.device == rewards.device
    assert not advantages.requires_grad and not kept.requires_grad


@pytest.mark.parametrize(
    "rewards,valid,eps",
    [
        (torch.zeros(2, 3, 1), torch.ones(2, 3, dtype=torch.bool), 1e-6),
        (torch.zeros(2, 3), torch.ones(2, 2, dtype=torch.bool), 1e-6),
        (torch.zeros(2, 3), torch.ones(2, 3, dtype=torch.int64), 1e-6),
        (torch.zeros(2, 3), torch.ones(2, 3, dtype=torch.bool), 0),
        (torch.zeros(2, 3), torch.ones(2, 3, dtype=torch.bool), True),
    ],
)
def test_invalid_shape_mask_or_eps_raises(submission, rewards, valid, eps):
    with pytest.raises(ValueError):
        submission.normalize_valid_group_rewards(rewards, valid, eps)


def test_valid_nonfinite_reward_raises(submission):
    rewards = torch.tensor([[1.0, float("nan"), 2.0]])
    valid = torch.tensor([[1, 1, 0]], dtype=torch.bool)
    with pytest.raises(ValueError):
        submission.normalize_valid_group_rewards(rewards, valid)
