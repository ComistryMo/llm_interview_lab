"""Check whether the local environment can run this training repository.

The core repository tooling only needs Python and pytest. PyTorch is optional
until a Tensor task is unlocked, so its absence is a warning unless
``--require-torch`` is supplied.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from importlib import metadata
import importlib
import json
from pathlib import Path
import re
import shutil
import sys
from typing import Mapping, Sequence


MIN_PYTHON = (3, 10)
MIN_PYTEST = (8, 0)
MAX_PYTEST = (9, 0)
MIN_TORCH = (2, 2)
REPO_ROOT = Path(__file__).resolve().parents[1]
_AUTO_DETECT = object()
_VERSION_PREFIX = re.compile(r"^\s*(\d+)\.(\d+)(?:\.(\d+))?")
_PRERELEASE = re.compile(r"(?:^|[.\d])(a|b|rc|dev)\d*", re.IGNORECASE)


@dataclass(frozen=True)
class EnvironmentCheck:
    """One environment check and whether it blocks execution."""

    name: str
    status: str
    detail: str
    required: bool

    @property
    def passed(self) -> bool:
        return self.status == "pass" or not self.required


def _numeric_version(value: str) -> tuple[int, ...]:
    """Return the leading numeric components of a package version."""

    match = _VERSION_PREFIX.match(value)
    if match is None:
        return ()
    return tuple(int(component) for component in match.groups(default="0"))


def _distribution_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for distribution in ("pytest", "torch"):
        try:
            versions[distribution] = metadata.version(distribution)
        except metadata.PackageNotFoundError:
            versions[distribution] = None
    return versions


def collect_checks(
    *,
    repo_root: Path = REPO_ROOT,
    require_torch: bool = False,
    python_version: Sequence[int] | None = None,
    distributions: Mapping[str, str | None] | None = None,
    git_executable: str | None | object = _AUTO_DETECT,
    in_virtualenv: bool | None = None,
    torch_importable: bool | None = None,
    verbose: bool = False,
) -> list[EnvironmentCheck]:
    """Collect deterministic environment checks.

    Optional arguments make the function testable without changing the real
    interpreter or installed packages.
    """

    actual_python = tuple(python_version or sys.version_info[:3])
    installed = dict(
        _distribution_versions() if distributions is None else distributions
    )
    git_path = (
        shutil.which("git")
        if git_executable is _AUTO_DETECT
        else git_executable
    )
    virtualenv_active = (
        in_virtualenv
        if in_virtualenv is not None
        else sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    )

    checks: list[EnvironmentCheck] = []

    python_ok = actual_python >= MIN_PYTHON
    checks.append(
        EnvironmentCheck(
            name="python",
            status="pass" if python_ok else "fail",
            detail=(
                f"found {'.'.join(map(str, actual_python))}; "
                f"requires >= {'.'.join(map(str, MIN_PYTHON))}"
            ),
            required=True,
        )
    )

    pytest_version = installed.get("pytest")
    parsed_pytest = _numeric_version(pytest_version or "")
    pytest_ok = bool(
        MIN_PYTEST <= parsed_pytest < MAX_PYTEST
        and _PRERELEASE.search(pytest_version or "") is None
    )
    checks.append(
        EnvironmentCheck(
            name="pytest",
            status="pass" if pytest_ok else "fail",
            detail=(
                f"found {pytest_version}; requires >=8,<9"
                if pytest_version
                else "not installed; install the test extra"
            ),
            required=True,
        )
    )

    torch_version = installed.get("torch")
    parsed_torch = _numeric_version(torch_version or "")
    torch_version_ok = bool(
        parsed_torch >= MIN_TORCH
        and _PRERELEASE.search(torch_version or "") is None
    )
    if torch_importable is None:
        if distributions is None and torch_version is not None:
            try:
                importlib.import_module("torch")
            except Exception:
                # A doctor command must treat DLL/ABI and import-time package
                # failures as an unusable installation without echoing local
                # paths from the exception into shareable output.
                actual_torch_importable = False
            else:
                actual_torch_importable = True
        else:
            actual_torch_importable = torch_version is not None
    else:
        actual_torch_importable = torch_importable
    torch_ok = torch_version_ok and actual_torch_importable
    checks.append(
        EnvironmentCheck(
            name="torch",
            status="pass" if torch_ok else ("fail" if require_torch else "warning"),
            detail=(
                f"found {torch_version} and import succeeded"
                if torch_ok
                else f"found {torch_version}, but requires >=2.2 and a working import"
                if torch_version
                else "not installed; needed only for unlocked Tensor tasks"
            ),
            required=require_torch,
        )
    )

    root_ok = all(
        (repo_root / marker).is_file()
        for marker in ("AGENTS.md", "pyproject.toml", "README.md")
    )
    checks.append(
        EnvironmentCheck(
            name="repository-root",
            status="pass" if root_ok else "fail",
            detail=(
                str(repo_root.resolve())
                if verbose
                else "required repository markers found"
                if root_ok
                else "required repository markers missing"
            ),
            required=True,
        )
    )

    checks.append(
        EnvironmentCheck(
            name="git",
            status="pass" if git_path else "warning",
            detail=(
                str(git_path)
                if verbose and git_path
                else "git found"
                if git_path
                else "git not found; training works, versioned reviews do not"
            ),
            required=False,
        )
    )
    checks.append(
        EnvironmentCheck(
            name="virtualenv",
            status="pass" if virtualenv_active else "warning",
            detail=(
                "virtual environment is active"
                if virtualenv_active
                else "no virtual environment detected"
            ),
            required=False,
        )
    )
    return checks


def checks_pass(checks: Sequence[EnvironmentCheck]) -> bool:
    """Return True when every required check passes."""

    return all(check.passed for check in checks)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-torch",
        action="store_true",
        help="fail when the optional PyTorch dependency is unavailable",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print machine-readable JSON",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="show local paths; do not paste verbose output into public reports",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    checks = collect_checks(require_torch=args.require_torch, verbose=args.verbose)

    if args.json:
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "ok": checks_pass(checks),
                    "checks": [asdict(check) for check in checks],
                },
                indent=2,
            )
        )
    else:
        for check in checks:
            print(f"[{check.status.upper():7}] {check.name}: {check.detail}")

    return 0 if checks_pass(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
