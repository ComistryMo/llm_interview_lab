from __future__ import annotations

from pathlib import Path

import pytest

from scripts.check_environment import (
    EnvironmentCheck,
    _numeric_version,
    checks_pass,
    collect_checks,
    main,
)


pytestmark = [pytest.mark.infrastructure]


def _versions(*, torch: str | None = "2.2.0") -> dict[str, str | None]:
    return {"pytest": "8.4.2", "torch": torch}


def test_supported_environment_passes(tmp_path: Path) -> None:
    for marker in ("AGENTS.md", "pyproject.toml", "README.md"):
        (tmp_path / marker).write_text("placeholder", encoding="utf-8")

    checks = collect_checks(
        repo_root=tmp_path,
        python_version=(3, 10, 0),
        distributions=_versions(),
        git_executable="git",
        in_virtualenv=True,
    )

    assert checks_pass(checks)


def test_old_python_is_a_required_failure(tmp_path: Path) -> None:
    for marker in ("AGENTS.md", "pyproject.toml", "README.md"):
        (tmp_path / marker).write_text("placeholder", encoding="utf-8")

    checks = collect_checks(
        repo_root=tmp_path,
        python_version=(3, 9, 2),
        distributions=_versions(),
        git_executable="git",
        in_virtualenv=True,
    )

    assert not checks_pass(checks)
    assert next(check for check in checks if check.name == "python").status == "fail"


def test_torch_is_optional_until_requested(tmp_path: Path) -> None:
    for marker in ("AGENTS.md", "pyproject.toml", "README.md"):
        (tmp_path / marker).write_text("placeholder", encoding="utf-8")

    optional = collect_checks(
        repo_root=tmp_path,
        python_version=(3, 11, 0),
        distributions=_versions(torch=None),
        git_executable="git",
        in_virtualenv=True,
    )
    required = collect_checks(
        repo_root=tmp_path,
        require_torch=True,
        python_version=(3, 11, 0),
        distributions=_versions(torch=None),
        git_executable="git",
        in_virtualenv=True,
    )

    assert checks_pass(optional)
    assert not checks_pass(required)


def test_missing_repository_markers_fail(tmp_path: Path) -> None:
    checks = collect_checks(
        repo_root=tmp_path,
        python_version=(3, 12, 0),
        distributions=_versions(),
        git_executable="git",
        in_virtualenv=True,
    )

    assert not checks_pass(checks)
    assert next(
        check for check in checks if check.name == "repository-root"
    ).status == "fail"


def test_pytest_major_version_must_match_supported_range(tmp_path: Path) -> None:
    for marker in ("AGENTS.md", "pyproject.toml", "README.md"):
        (tmp_path / marker).write_text("placeholder", encoding="utf-8")

    for unsupported in ("7.4.4", "9.0.0"):
        checks = collect_checks(
            repo_root=tmp_path,
            python_version=(3, 11, 0),
            distributions={"pytest": unsupported, "torch": "2.2.0"},
            git_executable="git",
            in_virtualenv=True,
        )
        assert not checks_pass(checks)


def test_torch_version_and_import_are_both_checked(tmp_path: Path) -> None:
    for marker in ("AGENTS.md", "pyproject.toml", "README.md"):
        (tmp_path / marker).write_text("placeholder", encoding="utf-8")

    too_old = collect_checks(
        repo_root=tmp_path,
        require_torch=True,
        python_version=(3, 11, 0),
        distributions={"pytest": "8.4.2", "torch": "2.1.0"},
        git_executable="git",
        in_virtualenv=True,
        torch_importable=True,
    )
    broken_import = collect_checks(
        repo_root=tmp_path,
        require_torch=True,
        python_version=(3, 11, 0),
        distributions={"pytest": "8.4.2", "torch": "2.2.0"},
        git_executable="git",
        in_virtualenv=True,
        torch_importable=False,
    )

    assert not checks_pass(too_old)
    assert not checks_pass(broken_import)


def test_version_parser_handles_prerelease_suffixes() -> None:
    assert _numeric_version("8.0rc1") == (8, 0, 0)
    assert _numeric_version("2.2.1+cpu") == (2, 2, 1)
    assert _numeric_version("not-a-version") == ()


def test_prerelease_does_not_satisfy_minimum_package_version(tmp_path: Path) -> None:
    for marker in ("AGENTS.md", "pyproject.toml", "README.md"):
        (tmp_path / marker).write_text("placeholder", encoding="utf-8")

    checks = collect_checks(
        repo_root=tmp_path,
        require_torch=True,
        python_version=(3, 11, 0),
        distributions={"pytest": "8.0.0rc1", "torch": "2.2.0a0+cpu"},
        git_executable="git",
        in_virtualenv=True,
        torch_importable=True,
    )

    assert not checks_pass(checks)
    assert next(check for check in checks if check.name == "pytest").status == "fail"
    assert next(check for check in checks if check.name == "torch").status == "fail"


def test_missing_git_can_be_injected_as_a_warning(tmp_path: Path) -> None:
    for marker in ("AGENTS.md", "pyproject.toml", "README.md"):
        (tmp_path / marker).write_text("placeholder", encoding="utf-8")

    checks = collect_checks(
        repo_root=tmp_path,
        python_version=(3, 11, 0),
        distributions=_versions(),
        git_executable=None,
        in_virtualenv=True,
    )

    assert checks_pass(checks)
    assert next(check for check in checks if check.name == "git").status == "warning"


def test_main_json_output_and_exit_code(monkeypatch, capsys) -> None:
    fake_checks = [
        EnvironmentCheck("python", "pass", "found 3.11.0", True),
        EnvironmentCheck("torch", "warning", "not installed", False),
    ]
    monkeypatch.setattr(
        "scripts.check_environment.collect_checks",
        lambda **_: fake_checks,
    )

    exit_code = main(["--json"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert '"schema_version": 1' in output
    assert '"ok": true' in output
    assert '"name": "python"' in output


def test_default_details_do_not_expose_local_paths(tmp_path: Path) -> None:
    for marker in ("AGENTS.md", "pyproject.toml", "README.md"):
        (tmp_path / marker).write_text("placeholder", encoding="utf-8")

    checks = collect_checks(
        repo_root=tmp_path,
        python_version=(3, 11, 0),
        distributions=_versions(),
        git_executable=str(tmp_path / "private" / "git.exe"),
        in_virtualenv=True,
    )
    details = "\n".join(check.detail for check in checks)

    assert str(tmp_path) not in details
    assert "git.exe" not in details


def test_empty_distribution_mapping_is_not_replaced(tmp_path: Path) -> None:
    for marker in ("AGENTS.md", "pyproject.toml", "README.md"):
        (tmp_path / marker).write_text("placeholder", encoding="utf-8")

    checks = collect_checks(
        repo_root=tmp_path,
        python_version=(3, 11, 0),
        distributions={},
        git_executable="git",
        in_virtualenv=True,
    )

    assert not checks_pass(checks)
    assert next(check for check in checks if check.name == "pytest").status == "fail"


def test_declared_python_and_pytest_ranges_match_pyproject() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'requires-python = ">=3.10"' in pyproject
    assert '"pytest>=8.0,<9"' in pyproject
