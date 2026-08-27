"""Run one problem's exact public tests in an isolated Python subprocess."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from .pytest_plugin import ENV_SUBMISSION, ENV_SUBMISSIONS_ROOT, ENV_SYMBOL
from .submissions import inspect_submission


COUNT_PATTERNS = {
    "passed": re.compile(r"(?:^|\s)(\d+) passed(?:,|\s|$)"),
    "failed": re.compile(r"(?:^|\s)(\d+) failed(?:,|\s|$)"),
}


class GraderError(RuntimeError):
    """Raised before pytest starts when the grading contract is invalid."""


@dataclass(frozen=True)
class GraderResult:
    """Stable evidence returned by a public-test subprocess."""

    submission_sha256: str
    exit_code: int
    status: str
    passed: int
    failed: int
    duration_ms: int
    output: str


def _count(summary: str, name: str) -> int:
    match = COUNT_PATTERNS[name].search(summary)
    return int(match.group(1)) if match else 0


def _display_safe_output(text: str, repo_root: Path, submissions_root: Path) -> str:
    replacements = sorted(
        {str(repo_root.resolve()), str(submissions_root.resolve())},
        key=len,
        reverse=True,
    )
    result = text
    for value in replacements:
        result = result.replace(value, ".")
        result = result.replace(value.replace("\\", "/"), ".")
    return result.strip()


def run_public_tests(
    *,
    repo_root: Path,
    test_path: Path,
    submission_path: Path,
    submissions_root: Path,
    expected_symbol: str,
    timeout_seconds: int = 30,
) -> GraderResult:
    """Run an exact pytest path; no starter fallback or test discovery occurs."""

    inspected = inspect_submission(submission_path, submissions_root)
    if not test_path.is_file() or test_path.suffix != ".py":
        raise GraderError("public test path is missing or invalid")
    try:
        test_path.resolve().relative_to(repo_root.resolve())
    except ValueError as error:
        raise GraderError("public test path must remain inside the repository") from error

    environment = os.environ.copy()
    environment.update(
        {
            ENV_SUBMISSION: str(inspected.path),
            ENV_SUBMISSIONS_ROOT: str(submissions_root.resolve()),
            ENV_SYMBOL: expected_symbol,
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    command = [
        sys.executable,
        "-m",
        "pytest",
        str(test_path.resolve()),
        "-q",
        "--tb=short",
        "-p",
        "llm_interview_lab.pytest_plugin",
    ]
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            env=environment,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        duration_ms = max(0, round((time.perf_counter() - started) * 1000))
        partial = error.stdout if isinstance(error.stdout, str) else ""
        return GraderResult(
            submission_sha256=inspected.sha256,
            exit_code=124,
            status="timeout",
            passed=0,
            failed=0,
            duration_ms=duration_ms,
            output=_display_safe_output(partial, repo_root, submissions_root),
        )

    duration_ms = max(0, round((time.perf_counter() - started) * 1000))
    output = _display_safe_output(completed.stdout, repo_root, submissions_root)
    exit_code = completed.returncode if completed.returncode >= 0 else 128 - completed.returncode
    if exit_code == 0:
        status = "passed"
    elif exit_code == 1:
        status = "failed"
    else:
        status = "error"
    return GraderResult(
        submission_sha256=inspected.sha256,
        exit_code=exit_code,
        status=status,
        passed=_count(output, "passed"),
        failed=_count(output, "failed"),
        duration_ms=duration_ms,
        output=output,
    )
