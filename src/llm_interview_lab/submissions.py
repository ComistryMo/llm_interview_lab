"""The single loader for trusted local learner submissions."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import stat
import sys
from types import ModuleType
from typing import Callable, Any


SYMBOL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class SubmissionError(RuntimeError):
    """A stable, path-safe error raised while inspecting or loading code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class InspectedSubmission:
    """A path-checked submission and its content identity."""

    path: Path
    sha256: str
    module_name: str


@dataclass(frozen=True)
class LoadedSubmission:
    """A loaded module and the callable required by the problem contract."""

    inspected: InspectedSubmission
    module: ModuleType
    target: Callable[..., Any]


def _is_obvious_link(path: Path) -> bool:
    try:
        file_stat = os.lstat(path)
    except OSError:
        return False
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    attributes = getattr(file_stat, "st_file_attributes", 0)
    return stat.S_ISLNK(file_stat.st_mode) or bool(attributes & reparse_flag)


def _reject_linked_path(candidate: Path, submissions_root: Path) -> None:
    current = candidate
    boundary = submissions_root.resolve()
    while True:
        if current.exists() and _is_obvious_link(current):
            raise SubmissionError("linked_path", "submission path must not use a link")
        if current.resolve() == boundary:
            return
        if current.parent == current:
            return
        current = current.parent


def inspect_submission(
    submission_path: Path,
    submissions_root: Path,
) -> InspectedSubmission:
    """Validate containment and file shape without executing learner code."""

    try:
        root = submissions_root.resolve(strict=True)
    except OSError as error:
        raise SubmissionError("missing_root", "profile submissions root is missing") from error
    _reject_linked_path(submission_path, submissions_root)
    try:
        resolved = submission_path.resolve(strict=True)
    except OSError as error:
        raise SubmissionError("missing_file", "submission file is missing") from error
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise SubmissionError(
            "wrong_path",
            "submission must be inside the current Profile submissions directory",
        ) from error
    if not resolved.is_file():
        raise SubmissionError("not_file", "submission must be a regular file")
    if resolved.suffix != ".py":
        raise SubmissionError("wrong_suffix", "submission must be a .py file")
    try:
        content = resolved.read_bytes()
    except OSError as error:
        raise SubmissionError("unreadable", "submission file cannot be read") from error
    digest = hashlib.sha256(content).hexdigest()
    identity = hashlib.sha256(
        (str(resolved) + "\0" + digest).encode("utf-8")
    ).hexdigest()[:24]
    return InspectedSubmission(
        path=resolved,
        sha256=digest,
        module_name=f"llm_lab_submission_{identity}",
    )


def load_submission(
    submission_path: Path,
    submissions_root: Path,
    expected_symbol: str,
) -> LoadedSubmission:
    """Load one trusted local module and require its Catalog symbol."""

    if SYMBOL_RE.fullmatch(expected_symbol) is None:
        raise SubmissionError("invalid_symbol", "Catalog submission symbol is invalid")
    inspected = inspect_submission(submission_path, submissions_root)
    spec = importlib.util.spec_from_file_location(
        inspected.module_name,
        inspected.path,
    )
    if spec is None or spec.loader is None:
        raise SubmissionError("load_error", "submission module cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules.pop(inspected.module_name, None)
    sys.modules[inspected.module_name] = module
    try:
        spec.loader.exec_module(module)
    except SyntaxError as error:
        sys.modules.pop(inspected.module_name, None)
        raise SubmissionError("syntax_error", "submission contains a syntax error") from error
    except ImportError as error:
        sys.modules.pop(inspected.module_name, None)
        raise SubmissionError("import_error", "submission import failed") from error
    except Exception as error:
        sys.modules.pop(inspected.module_name, None)
        raise SubmissionError("import_error", "submission failed during import") from error

    target = getattr(module, expected_symbol, None)
    if not callable(target):
        sys.modules.pop(inspected.module_name, None)
        raise SubmissionError(
            "missing_symbol",
            f"submission must define callable {expected_symbol}",
        )
    return LoadedSubmission(inspected=inspected, module=module, target=target)
