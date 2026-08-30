import pytest


def _scheduler(submission):
    return submission.ContinuousBatchScheduler(
        max_active_tokens=10,
        max_prefill_tokens=6,
        max_decode_tokens=2,
    )


def test_fifo_prefill_and_decode_are_separate_phases(submission):
    scheduler = _scheduler(submission)
    scheduler.submit("a", prompt_tokens=3, max_new_tokens=2)
    scheduler.submit("b", prompt_tokens=2, max_new_tokens=2)
    result = scheduler.step()
    assert result["admitted"] == ("a", "b")
    assert result["prefill_tokens"] == 5
    assert result["decoded"] == ()
    assert result["active_tokens"] == 5

    result = scheduler.step()
    assert result["decoded"] == ("a", "b")
    assert result["decode_tokens"] == 2
    assert result["active_tokens"] == 7


def test_prefill_budget_has_head_of_line_fifo_semantics(submission):
    scheduler = _scheduler(submission)
    scheduler.submit("large", prompt_tokens=5, max_new_tokens=1)
    scheduler.submit("small", prompt_tokens=1, max_new_tokens=1)
    result = scheduler.step(prefill_budget=4, decode_budget=0)
    assert result["admitted"] == ()
    assert result["queued"] == ("large", "small")
    result = scheduler.step(prefill_budget=6, decode_budget=0)
    assert result["admitted"] == ("large", "small")


def test_round_robin_persists_when_decode_budget_is_smaller_than_batch(submission):
    scheduler = _scheduler(submission)
    for request_id in ("a", "b", "c"):
        scheduler.submit(request_id, prompt_tokens=1, max_new_tokens=4)
    scheduler.step(decode_budget=0)
    assert scheduler.step(decode_budget=1)["decoded"] == ("a",)
    assert scheduler.step(decode_budget=1)["decoded"] == ("b",)
    assert scheduler.step(decode_budget=1)["decoded"] == ("c",)
    assert scheduler.step(decode_budget=1)["decoded"] == ("a",)


def test_completion_releases_kv_capacity_and_reports_terminal_id(submission):
    scheduler = submission.ContinuousBatchScheduler(6, 4, 2)
    scheduler.submit("a", prompt_tokens=2, max_new_tokens=1)
    scheduler.submit("b", prompt_tokens=2, max_new_tokens=1)
    scheduler.submit("c", prompt_tokens=2, max_new_tokens=1)
    assert scheduler.step()["admitted"] == ("a", "b")
    result = scheduler.step(prefill_budget=0, decode_budget=1)
    assert result["decoded"] == ("a",) and result["completed"] == ("a",)
    assert result["active_tokens"] == 2
    result = scheduler.step(prefill_budget=4, decode_budget=0)
    assert result["admitted"] == ("c",)
    assert result["active"] == ("b", "c")


def test_cancel_queued_and_active_releases_capacity(submission):
    scheduler = submission.ContinuousBatchScheduler(5, 5, 1)
    scheduler.submit("a", 2, 3)
    scheduler.submit("b", 2, 3)
    scheduler.submit("c", 2, 3)
    scheduler.step(decode_budget=0)
    assert scheduler.cancel("c") is True
    assert scheduler.cancel("a") is True
    assert scheduler.cancel("a") is False
    assert scheduler.active_tokens == 2
    assert scheduler.active_ids == ("b",)


def test_deadline_expires_before_work_after_the_inclusive_step(submission):
    scheduler = _scheduler(submission)
    scheduler.submit("soon", 2, 4, deadline_step=1)
    assert scheduler.step(decode_budget=0)["expired"] == ()
    result = scheduler.step(decode_budget=0)
    assert result["expired"] == ("soon",)
    assert result["active_tokens"] == 0
    assert scheduler.finish("soon") is False


def test_zero_budgets_are_valid_noops_and_snapshot_is_detached(submission):
    scheduler = _scheduler(submission)
    scheduler.submit("a", 2, 2)
    result = scheduler.step(prefill_budget=0, decode_budget=0)
    assert result["admitted"] == () and result["decoded"] == ()
    records = scheduler.snapshot()
    assert isinstance(records, tuple) and records[0]["request_id"] == "a"
    records[0]["state"] = "active"
    assert scheduler.pending_ids == ("a",)


@pytest.mark.parametrize(
    "args",
    [
        (0, 2, 1),
        (4, 0, 1),
        (4, 2, 0),
        (4, 2, True),
    ],
)
def test_invalid_scheduler_configuration_raises(submission, args):
    with pytest.raises(ValueError):
        submission.ContinuousBatchScheduler(*args)


@pytest.mark.parametrize(
    "operation",
    [
        lambda s: s.submit("", 1, 1),
        lambda s: s.submit("a", 10, 1),
        lambda s: s.submit("a", 1, 0),
        lambda s: s.submit("a", 1, True),
        lambda s: s.submit("a", 1, 1, deadline_step=-1),
        lambda s: s.step(prefill_budget=-1),
        lambda s: s.step(decode_budget=True),
        lambda s: s.step(prefill_budget=7),
        lambda s: s.step(decode_budget=3),
    ],
)
def test_invalid_requests_and_budgets_raise(submission, operation):
    scheduler = _scheduler(submission)
    with pytest.raises(ValueError):
        operation(scheduler)


def test_duplicate_ids_and_past_deadline_raise_without_partial_admission(submission):
    scheduler = _scheduler(submission)
    scheduler.submit("a", 1, 1)
    with pytest.raises(ValueError):
        scheduler.submit("a", 1, 1)
    scheduler.step(prefill_budget=0, decode_budget=0)
    with pytest.raises(ValueError):
        scheduler.submit("past", 1, 1, deadline_step=0)
    assert scheduler.pending_ids == ("a",)


def test_manual_finish_and_unknown_terminal_operations(submission):
    scheduler = _scheduler(submission)
    scheduler.submit("a", 2, 3)
    scheduler.step(decode_budget=0)
    assert scheduler.finish("a") is True
    assert scheduler.active_tokens == 0 and scheduler.completed_ids == ("a",)
    assert scheduler.cancel("missing") is False
    assert scheduler.finish("a") is False
    with pytest.raises(ValueError):
        scheduler.submit("a", 1, 1)
