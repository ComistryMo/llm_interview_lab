from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from llm_interview_lab.grader import run_public_tests
from llm_interview_lab.submissions import (
    SubmissionError,
    inspect_submission,
    load_submission,
)


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "grader" / "add_one"
SUBMISSIONS = FIXTURE_ROOT / "submissions"
PUBLIC_TEST = FIXTURE_ROOT / "test_public.py"


def _grade(name: str):
    return run_public_tests(
        repo_root=REPO_ROOT,
        test_path=PUBLIC_TEST,
        submission_path=SUBMISSIONS / name,
        submissions_root=SUBMISSIONS,
        expected_symbol="add_one",
    )


def test_valid_infrastructure_submission_passes_in_subprocess() -> None:
    result = _grade("valid.py")

    assert result.exit_code == 0
    assert result.status == "passed"
    assert result.passed == 2
    assert result.failed == 0


@pytest.mark.parametrize(
    ("name", "code"),
    [
        ("missing_symbol.py", "missing_symbol"),
        ("syntax_error.py", "syntax_error"),
        ("import_error.py", "import_error"),
    ],
)
def test_loader_failures_are_reported_without_fallback(name: str, code: str) -> None:
    result = _grade(name)

    assert result.status == "import_error"
    assert result.exit_code == 4
    assert f"submission_error:{code}" in result.output
    assert "starter.py" not in result.output


def test_runtime_error_is_a_failed_public_test() -> None:
    result = _grade("runtime_error.py")

    assert result.status == "failed"
    assert result.exit_code == 1
    assert result.failed == 2


def test_timeout_is_classified_and_bounded() -> None:
    result = run_public_tests(
        repo_root=REPO_ROOT,
        test_path=PUBLIC_TEST,
        submission_path=SUBMISSIONS / "infinite_loop.py",
        submissions_root=SUBMISSIONS,
        expected_symbol="add_one",
        time_limit_ms=200,
    )

    assert result.status == "timed_out"
    assert result.exit_code == 124


def test_output_is_truncated_at_catalog_limit() -> None:
    result = run_public_tests(
        repo_root=REPO_ROOT,
        test_path=PUBLIC_TEST,
        submission_path=SUBMISSIONS / "noisy.py",
        submissions_root=SUBMISSIONS,
        expected_symbol="add_one",
        output_limit_kb=1,
    )

    assert result.status == "passed"
    assert result.output_truncated
    assert "output truncated" in result.output


def test_invalid_test_module_is_collection_error(tmp_path: Path) -> None:
    broken = tmp_path / "test_broken.py"
    broken.write_text("def test_(\n", encoding="utf-8")
    result = run_public_tests(
        repo_root=tmp_path,
        test_path=broken,
        submission_path=SUBMISSIONS / "valid.py",
        submissions_root=SUBMISSIONS,
        expected_symbol="add_one",
    )

    assert result.status == "collection_error"


def test_wrong_path_and_directory_are_rejected(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()

    with pytest.raises(SubmissionError) as outside:
        inspect_submission(SUBMISSIONS / "valid.py", allowed)
    assert outside.value.code == "wrong_path"

    with pytest.raises(SubmissionError) as directory:
        inspect_submission(SUBMISSIONS, SUBMISSIONS)
    assert directory.value.code == "not_file"


def test_module_identity_prevents_cache_pollution() -> None:
    first = load_submission(SUBMISSIONS / "cache_a.py", SUBMISSIONS, "add_one")
    second = load_submission(SUBMISSIONS / "cache_b.py", SUBMISSIONS, "add_one")

    assert first.target(5) == ("a", 5)
    assert second.target(5) == ("b", 5)
    assert first.inspected.module_name != second.inspected.module_name


def test_submission_sha256_uses_exact_file_bytes() -> None:
    path = SUBMISSIONS / "valid.py"
    inspected = inspect_submission(path, SUBMISSIONS)

    assert inspected.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()


def test_symlink_is_rejected_when_platform_allows_it(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    link = allowed / "linked.py"
    try:
        link.symlink_to(SUBMISSIONS / "valid.py")
    except OSError as error:
        pytest.skip(f"symlink creation unavailable: {error}")

    with pytest.raises(SubmissionError) as linked:
        inspect_submission(link, allowed)
    assert linked.value.code == "linked_path"
