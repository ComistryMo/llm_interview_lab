"""Run exact public tests in a bounded subprocess for trusted local code."""

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
    submission_sha256: str
    exit_code: int
    status: str
    passed: int
    failed: int
    duration_ms: int
    output: str
    output_truncated: bool = False


def _count(summary: str, name: str) -> int:
    match = COUNT_PATTERNS[name].search(summary)
    return int(match.group(1)) if match else 0


def _safe_output(text: str, repo_root: Path, submissions_root: Path, limit_kb: int) -> tuple[str, bool]:
    result = text
    for value in sorted({str(repo_root.resolve()), str(submissions_root.resolve())}, key=len, reverse=True):
        result = result.replace(value, ".").replace(value.replace("\\", "/"), ".")
    raw = result.encode("utf-8", errors="replace")
    limit = limit_kb * 1024
    if len(raw) <= limit:
        return result.strip(), False
    clipped = raw[:limit].decode("utf-8", errors="ignore").rstrip()
    return f"{clipped}\n...[output truncated at {limit_kb} KiB]", True


def _status(exit_code: int, output: str) -> str:
    if exit_code == 0:
        return "passed"
    if exit_code == 1:
        return "failed"
    if "submission_error:" in output:
        return "import_error"
    if exit_code in {2, 4, 5}:
        return "collection_error"
    return "internal_error"


def run_public_tests(
    *,
    repo_root: Path,
    test_path: Path,
    submission_path: Path,
    submissions_root: Path,
    expected_symbol: str,
    time_limit_ms: int = 5000,
    output_limit_kb: int = 256,
) -> GraderResult:
    """Run one exact pytest path; this is a guardrail, not a security sandbox."""

    inspected = inspect_submission(submission_path, submissions_root)
    if not test_path.is_file() or test_path.suffix != ".py":
        raise GraderError("public test path is missing or invalid")
    try:
        test_path.resolve().relative_to(repo_root.resolve())
    except ValueError as error:
        raise GraderError("public test path must remain inside the repository") from error
    if type(time_limit_ms) is not int or time_limit_ms < 100:
        raise GraderError("time limit must be at least 100 ms")
    if type(output_limit_kb) is not int or output_limit_kb < 1:
        raise GraderError("output limit must be positive")
    environment = os.environ.copy()
    environment.update({
        ENV_SUBMISSION: str(inspected.path), ENV_SUBMISSIONS_ROOT: str(submissions_root.resolve()),
        ENV_SYMBOL: expected_symbol, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1",
    })
    grader_executable = os.environ.get("LLM_LAB_GRADER_EXECUTABLE")
    command = (
        [grader_executable, "--grader-worker"]
        if grader_executable
        else [sys.executable, "-m", "pytest"]
    )
    command.extend(
        [
            str(test_path.resolve()),
            "-q",
            "--tb=short",
            "--capture=no",
            "-p",
            "llm_interview_lab.pytest_plugin",
        ]
    )
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command, cwd=repo_root, env=environment, check=False,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace", timeout=time_limit_ms / 1000,
        )
    except subprocess.TimeoutExpired as error:
        duration = max(0, round((time.perf_counter() - started) * 1000))
        partial = error.stdout.decode("utf-8", errors="replace") if isinstance(error.stdout, bytes) else (error.stdout or "")
        output, truncated = _safe_output(partial, repo_root, submissions_root, output_limit_kb)
        return GraderResult(inspected.sha256, 124, "timed_out", 0, 0, duration, output, truncated)
    except OSError as error:
        duration = max(0, round((time.perf_counter() - started) * 1000))
        output, truncated = _safe_output(f"pytest process could not start: {error}", repo_root, submissions_root, output_limit_kb)
        return GraderResult(inspected.sha256, 125, "internal_error", 0, 0, duration, output, truncated)
    duration = max(0, round((time.perf_counter() - started) * 1000))
    exit_code = completed.returncode if completed.returncode >= 0 else 128 - completed.returncode
    output, truncated = _safe_output(completed.stdout, repo_root, submissions_root, output_limit_kb)
    return GraderResult(inspected.sha256, exit_code, _status(exit_code, output), _count(output, "passed"), _count(output, "failed"), duration, output, truncated)
