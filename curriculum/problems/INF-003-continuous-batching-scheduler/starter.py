from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass
class _Request:
    request_id: str
    prompt_tokens: int
    max_new_tokens: int
    deadline_step: int | None
    generated_tokens: int = 0
    state: str = "queued"


class ContinuousBatchScheduler:
    """Schedule deterministic prefill/decode work under token budgets."""

    def __init__(
        self,
        max_active_tokens: int,
        max_prefill_tokens: int,
        max_decode_tokens: int = 1,
    ) -> None:
        raise NotImplementedError

    def submit(
        self,
        request_id: str,
        prompt_tokens: int,
        max_new_tokens: int,
        deadline_step: int | None = None,
    ) -> None:
        raise NotImplementedError

    def step(
        self,
        *,
        prefill_budget: int | None = None,
        decode_budget: int | None = None,
    ) -> dict[str, object]:
        raise NotImplementedError

    def cancel(self, request_id: str) -> bool:
        raise NotImplementedError

    def finish(self, request_id: str) -> bool:
        raise NotImplementedError

    def snapshot(self) -> tuple[dict[str, object], ...]:
        raise NotImplementedError

    @property
    def pending_ids(self) -> tuple[str, ...]:
        raise NotImplementedError

    @property
    def active_ids(self) -> tuple[str, ...]:
        raise NotImplementedError

    @property
    def completed_ids(self) -> tuple[str, ...]:
        raise NotImplementedError

    @property
    def active_tokens(self) -> int:
        raise NotImplementedError
