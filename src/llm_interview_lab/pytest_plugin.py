"""Pytest bridge that injects exactly one explicitly selected submission."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from .submissions import LoadedSubmission, SubmissionError, load_submission


ENV_SUBMISSION = "LLM_LAB_SUBMISSION_PATH"
ENV_SUBMISSIONS_ROOT = "LLM_LAB_SUBMISSIONS_ROOT"
ENV_SYMBOL = "LLM_LAB_SUBMISSION_SYMBOL"

_loaded: LoadedSubmission | None = None


def pytest_configure(config: pytest.Config) -> None:
    """Load the explicit submission before public tests are collected."""

    del config
    global _loaded
    values = {
        ENV_SUBMISSION: os.environ.get(ENV_SUBMISSION),
        ENV_SUBMISSIONS_ROOT: os.environ.get(ENV_SUBMISSIONS_ROOT),
        ENV_SYMBOL: os.environ.get(ENV_SYMBOL),
    }
    missing = sorted(name for name, value in values.items() if not value)
    if missing:
        raise pytest.UsageError("grader did not provide a complete submission contract")
    try:
        _loaded = load_submission(
            Path(values[ENV_SUBMISSION] or ""),
            Path(values[ENV_SUBMISSIONS_ROOT] or ""),
            values[ENV_SYMBOL] or "",
        )
    except SubmissionError as error:
        raise pytest.UsageError(f"submission_error:{error.code}: {error}") from error


@pytest.fixture(scope="session")
def submission() -> object:
    """Return the selected module without exposing loader details to a problem."""

    if _loaded is None:
        raise pytest.UsageError("submission was not loaded")
    return _loaded.module
