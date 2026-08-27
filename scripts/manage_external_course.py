"""Install and inspect audited external course checkouts without vendoring them.

This command never executes third-party Python or test code. Users explicitly run
the printed upstream commands after reviewing the checkout and its dependencies.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit
import uuid

try:
    from scripts.validate_external_courses import (
        REFERENCE_RELATIVE,
        REPO_ROOT,
        CurriculumValidationError,
        load_json,
        validate_external_courses,
    )
except ModuleNotFoundError:  # Direct execution: python scripts/manage_external_course.py
    from validate_external_courses import (  # type: ignore[no-redef]
        REFERENCE_RELATIVE,
        REPO_ROOT,
        CurriculumValidationError,
        load_json,
        validate_external_courses,
    )


UPSTREAM_REF = "refs/llm-interview-lab/upstream"
UPSTREAM_CONFIG = "llmInterviewLab.upstreamRevision"
AUDITED_REMOTE_REF = "refs/remotes/origin/audited"
LEARNER_BRANCH = "learner-work"
UNTRUSTED_GIT_ENVIRONMENT_KEYS = {
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_ASKPASS",
    "GIT_CEILING_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_CONFIG_COUNT",
    "GIT_CONFIG_SYSTEM",
    "GIT_DIR",
    "GIT_DISCOVERY_ACROSS_FILESYSTEM",
    "GIT_EXEC_PATH",
    "GIT_EXTERNAL_DIFF",
    "GIT_INDEX_FILE",
    "GIT_INTERNAL_SUPER_PREFIX",
    "GIT_NAMESPACE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_PREFIX",
    "GIT_PROXY_COMMAND",
    "GIT_SSH",
    "GIT_SSH_COMMAND",
    "GIT_TEMPLATE_DIR",
    "GIT_WORK_TREE",
    "SSH_ASKPASS",
}


class ExternalCourseError(RuntimeError):
    """Raised when an external checkout cannot be installed or verified safely."""


@dataclass(frozen=True)
class AssignmentSource:
    pack: Mapping[str, Any]
    assignment: Mapping[str, Any]
    reference: Mapping[str, Any]

    @property
    def id(self) -> str:
        return str(self.assignment["id"])

    @property
    def revision(self) -> str:
        return str(self.reference["pinned_revision"])

    @property
    def repository_url(self) -> str:
        return str(self.reference["repository_url"])


@dataclass(frozen=True)
class GroupSource:
    assignment_source: AssignmentSource
    group: Mapping[str, Any]

    @property
    def id(self) -> str:
        return f"{self.assignment_source.id}-{self.group['id']}"


@dataclass(frozen=True)
class CheckoutStatus:
    installed: bool
    source_valid: bool
    target: Path
    expected_revision: str
    base_revision: str | None = None
    head_revision: str | None = None
    branch: str | None = None
    dirty: bool | None = None
    fetch_url: str | None = None
    push_url: str | None = None
    message: str = ""


def load_assignment_sources(*, repo_root: Path = REPO_ROOT) -> dict[str, AssignmentSource]:
    _, manifests, _ = validate_external_courses(repo_root=repo_root, check_navigation=True)
    registry = load_json(repo_root / REFERENCE_RELATIVE)
    references = {record["id"]: record for record in registry["references"]}
    sources: dict[str, AssignmentSource] = {}
    for manifest in manifests:
        for assignment in manifest["assignments"]:
            source = AssignmentSource(
                pack=manifest,
                assignment=assignment,
                reference=references[assignment["reference_id"]],
            )
            if source.id in sources:
                raise ExternalCourseError(f"duplicate assignment id: {source.id}")
            sources[source.id] = source
    return sources


def load_group_sources(
    sources: Mapping[str, AssignmentSource],
) -> dict[str, GroupSource]:
    groups: dict[str, GroupSource] = {}
    for source in sources.values():
        for group in source.assignment["problem_groups"]:
            item = GroupSource(assignment_source=source, group=group)
            if item.id in groups:
                raise ExternalCourseError(f"duplicate canonical problem-group id: {item.id}")
            groups[item.id] = item
    return groups


def _normalize_git_url(value: str) -> str:
    normalized = value.strip().rstrip("/")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    try:
        parsed = urlsplit(normalized)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        return normalized
    if parsed.scheme and parsed.netloc and hostname and not parsed.username and not parsed.password:
        safe_hostname = hostname.casefold()
        if ":" in safe_hostname and not safe_hostname.startswith("["):
            safe_hostname = f"[{safe_hostname}]"
        netloc = safe_hostname + (f":{port}" if port is not None else "")
        return urlunsplit(
            (parsed.scheme.casefold(), netloc, parsed.path, parsed.query, parsed.fragment)
        )
    return os.path.normcase(normalized) if os.name == "nt" else normalized


def _redact_git_location(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return "<redacted-git-location>" if "://" in value or "@" in value else value
    if parsed.scheme and parsed.netloc:
        try:
            hostname = parsed.hostname or "redacted-host"
            parsed_port = parsed.port
        except ValueError:
            return urlunsplit((parsed.scheme, "redacted-host", parsed.path, "", ""))
        if ":" in hostname and not hostname.startswith("["):
            hostname = f"[{hostname}]"
        port = f":{parsed_port}" if parsed_port is not None else ""
        return urlunsplit((parsed.scheme, hostname + port, parsed.path, "", ""))
    if "@" in value and ":" in value.partition("@")[2]:
        return "<redacted-user>@" + value.partition("@")[2]
    return value


def _redact_git_output(value: str, arguments: Sequence[str]) -> str:
    redacted = value
    for argument in arguments:
        safe = _redact_git_location(argument)
        if safe != argument:
            redacted = redacted.replace(argument, safe)
    return redacted


def _audited_fetch_spec(revision: str) -> str:
    return f"+{revision}:{AUDITED_REMOTE_REF}"


def _git_environment() -> dict[str, str]:
    """Return a non-interactive Git environment without inherited config injection."""

    environment = os.environ.copy()
    for key in tuple(environment):
        if (
            key in UNTRUSTED_GIT_ENVIRONMENT_KEYS
            or key.startswith("GIT_CONFIG_")
            or key.startswith("GIT_TRACE")
        ):
            environment.pop(key, None)
    environment["GIT_TERMINAL_PROMPT"] = "0"
    environment["GIT_CONFIG_NOSYSTEM"] = "1"
    environment["GIT_CONFIG_GLOBAL"] = os.devnull
    environment["GIT_ATTR_NOSYSTEM"] = "1"
    environment["GIT_LFS_SKIP_SMUDGE"] = "1"
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    return environment


def _run_git(
    arguments: Sequence[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *arguments],
            cwd=cwd,
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_git_environment(),
            timeout=600,
        )
    except FileNotFoundError as error:
        raise ExternalCourseError("Git is required but was not found on PATH") from error
    except subprocess.CalledProcessError as error:
        command = "git " + " ".join(_redact_git_location(item) for item in arguments)
        detail = _redact_git_output(
            (error.stderr or error.stdout or "unknown Git error").strip(),
            arguments,
        )
        raise ExternalCourseError(f"{command} failed: {detail}") from error
    except subprocess.TimeoutExpired as error:
        command = "git " + " ".join(_redact_git_location(item) for item in arguments)
        raise ExternalCourseError(f"{command} timed out after 600 seconds") from error
    except (OSError, UnicodeError) as error:
        command = "git " + " ".join(_redact_git_location(item) for item in arguments)
        raise ExternalCourseError(
            f"{command} could not be executed safely ({type(error).__name__})"
        ) from error


def _is_descendant(candidate: Path, parent: Path) -> bool:
    try:
        candidate.relative_to(parent)
    except ValueError:
        return False
    return candidate != parent


def _is_link_or_reparse(path: Path) -> bool:
    try:
        file_stat = os.lstat(path)
    except FileNotFoundError:
        return False
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    attributes = getattr(file_stat, "st_file_attributes", 0)
    return stat.S_ISLNK(file_stat.st_mode) or bool(attributes & reparse_flag)


def _path_lexically_exists(path: Path) -> bool:
    return os.path.lexists(path)


def _remove_install_staging(staging: Path, parent: Path) -> None:
    resolved = staging.resolve(strict=False)
    if not _is_descendant(resolved, parent) or _is_link_or_reparse(staging):
        raise ExternalCourseError("refusing to clean an unsafe installation staging path")

    def make_writable_and_retry(function: Any, value: str, _: Any) -> None:
        os.chmod(value, stat.S_IWRITE)
        function(value)

    shutil.rmtree(staging, onerror=make_writable_and_retry)


def _move_staging_without_overwrite(staging: Path, target: Path) -> None:
    """Rename a checkout with bounded retries for transient Windows file locks."""

    for attempt in range(8):
        if _path_lexically_exists(target):
            raise ExternalCourseError(f"refusing to overwrite existing target: {target}")
        try:
            os.rename(staging, target)
            return
        except PermissionError:
            if attempt == 7:
                raise
            time.sleep(min(0.05 * (2**attempt), 0.4))
    raise AssertionError("unreachable rename retry state")


def _reject_linked_components(root: Path, relative: PurePosixPath) -> None:
    current = root
    for part in relative.parts:
        current = current / part
        if _is_link_or_reparse(current):
            raise ExternalCourseError(
                f"external checkout path cannot traverse a link or reparse point: {current}"
            )


def checkout_target(source: AssignmentSource, *, repo_root: Path = REPO_ROOT) -> Path:
    root = repo_root.resolve()
    install_relative = PurePosixPath(str(source.pack["install_root"]))
    _reject_linked_components(root, install_relative)
    install_path = root.joinpath(*install_relative.parts)
    if install_path.exists() and not install_path.is_dir():
        raise ExternalCourseError("external course install root must be a directory")
    install_root = install_path.resolve(strict=False)
    external_root = (root / ".external").resolve(strict=False)
    if not _is_descendant(install_root, external_root):
        raise ExternalCourseError("external course install root escaped .external")
    target_relative = install_relative / str(source.assignment["checkout_directory"])
    _reject_linked_components(root, target_relative)
    target = root.joinpath(*target_relative.parts).resolve(strict=False)
    if not _is_descendant(target, install_root):
        raise ExternalCourseError("external course checkout target escaped its install root")
    return target


def _git_value(target: Path, arguments: Sequence[str]) -> str:
    return _run_git(arguments, cwd=target).stdout.strip()


def _git_metadata_is_safe(git_metadata: Path) -> bool:
    required_files = (git_metadata / "config", git_metadata / "HEAD")
    required_directories = (git_metadata / "objects", git_metadata / "refs")
    optional_files = (git_metadata / "packed-refs",)
    forbidden_indirections = (
        git_metadata / "commondir",
        git_metadata / "config.worktree",
        git_metadata / "info" / "grafts",
        git_metadata / "objects" / "info" / "alternates",
        git_metadata / "objects" / "info" / "http-alternates",
    )
    return all(path.is_file() and not _is_link_or_reparse(path) for path in required_files) and all(
        path.is_dir() and not _is_link_or_reparse(path) for path in required_directories
    ) and all(
        not _path_lexically_exists(path)
        or (path.is_file() and not _is_link_or_reparse(path))
        for path in optional_files
    ) and all(not _path_lexically_exists(path) for path in forbidden_indirections)


def _single_local_config_value(target: Path, key: str) -> str:
    """Read one local-only Git value and reject ambiguous multi-value config."""

    output = _run_git(
        ["config", "--file", ".git/config", "--get-all", key],
        cwd=target,
    ).stdout
    if not output.endswith("\n"):
        raise ExternalCourseError(
            f"local Git configuration {key} has an ambiguous output encoding"
        )
    values = output[:-1].split("\n")
    if len(values) != 1:
        raise ExternalCourseError(
            f"local Git configuration {key} must contain exactly one value"
        )
    return values[0]


def _unsafe_local_config_keys(target: Path) -> list[str]:
    """Return local Git keys that could launch programs or import other config."""

    result = _run_git(
        ["config", "--file", ".git/config", "--name-only", "--list"],
        cwd=target,
    )
    unsafe: list[str] = []
    for line in result.stdout.splitlines():
        key = line.casefold()
        if (
            key.startswith(
                (
                    "alias.",
                    "browser.",
                    "credential.",
                    "include.",
                    "includeif.",
                    "pager.",
                )
            )
            or key
            in {
                "core.attributesfile",
                "core.editor",
                "core.fsmonitor",
                "core.gitproxy",
                "core.pager",
                "core.sshcommand",
                "core.worktree",
                "extensions.worktreeconfig",
                "gpg.program",
                "interactive.difffilter",
                "sequence.editor",
                "web.browser",
            }
            or re.fullmatch(r"filter\..*\.(clean|smudge|process|required)", key)
            or re.fullmatch(r"diff\..*\.command", key)
            or re.fullmatch(r"merge\..*\.driver", key)
            or re.fullmatch(r"http\..*\.extraheader", key)
            or re.fullmatch(r"tar\..*\.command", key)
            or re.fullmatch(r"url\..*\.(insteadof|pushinsteadof)", key)
        ):
            unsafe.append(line)
    return unsafe


def inspect_checkout(
    *, target: Path, expected_url: str, expected_revision: str
) -> CheckoutStatus:
    lexical_target = target.absolute()
    if _is_link_or_reparse(lexical_target):
        return CheckoutStatus(
            installed=True,
            source_valid=False,
            target=lexical_target,
            expected_revision=expected_revision,
            message="checkout root cannot be a link or reparse point",
        )
    target = lexical_target.resolve(strict=False)
    if not target.exists():
        return CheckoutStatus(
            installed=False,
            source_valid=False,
            target=target,
            expected_revision=expected_revision,
            message="not installed",
        )
    if not target.is_dir():
        return CheckoutStatus(
            installed=True,
            source_valid=False,
            target=target,
            expected_revision=expected_revision,
            message="target exists but is not a directory",
        )
    git_metadata = target / ".git"
    if (
        not git_metadata.is_dir()
        or _is_link_or_reparse(git_metadata)
        or not _git_metadata_is_safe(git_metadata)
    ):
        return CheckoutStatus(
            installed=True,
            source_valid=False,
            target=target,
            expected_revision=expected_revision,
            message="target is not an independent regular Git checkout",
        )
    try:
        inside = _git_value(target, ["rev-parse", "--is-inside-work-tree"])
        top_level = Path(
            _git_value(target, ["rev-parse", "--show-toplevel"])
        ).resolve()
        head = _git_value(target, ["rev-parse", "HEAD"])
        base = _git_value(target, ["rev-parse", UPSTREAM_REF])
        configured = _single_local_config_value(target, UPSTREAM_CONFIG)
        fetch_spec = _single_local_config_value(target, "remote.origin.fetch")
        tag_option = _single_local_config_value(target, "remote.origin.tagOpt")
        fetch_url = _single_local_config_value(target, "remote.origin.url")
        push_url = _single_local_config_value(target, "remote.origin.pushurl")
        effective_fetch_urls = _git_value(
            target,
            ["remote", "get-url", "--all", "origin"],
        ).splitlines()
        effective_push_urls = _git_value(
            target,
            ["remote", "get-url", "--push", "--all", "origin"],
        ).splitlines()
        hooks_path = _single_local_config_value(target, "core.hooksPath")
        unsafe_config_keys = _unsafe_local_config_keys(target)
        branch = _git_value(target, ["branch", "--show-current"])
        remote_refs = _git_value(
            target,
            ["for-each-ref", "--format=%(refname)", "refs/remotes/origin"],
        ).splitlines()
        tags = _git_value(
            target,
            ["for-each-ref", "--format=%(refname)", "refs/tags"],
        ).splitlines()
        replacement_refs = _git_value(
            target,
            ["for-each-ref", "--format=%(refname)", "refs/replace"],
        ).splitlines()
        audited_remote_revision = _git_value(target, ["rev-parse", AUDITED_REMOTE_REF])
        ancestor = _run_git(
            ["merge-base", "--is-ancestor", expected_revision, "HEAD"],
            cwd=target,
            check=False,
        ).returncode == 0
    except ExternalCourseError as error:
        return CheckoutStatus(
            installed=True,
            source_valid=False,
            target=target,
            expected_revision=expected_revision,
            message=str(error),
        )
    effective_fetch_matches = len(effective_fetch_urls) == 1 and (
        _normalize_git_url(effective_fetch_urls[0]) == _normalize_git_url(expected_url)
    )
    valid = all(
        (
            inside == "true",
            top_level == target,
            base == expected_revision,
            configured == expected_revision,
            fetch_spec == _audited_fetch_spec(expected_revision),
            tag_option == "--no-tags",
            remote_refs == [AUDITED_REMOTE_REF],
            audited_remote_revision == expected_revision,
            not tags,
            not replacement_refs,
            ancestor,
            _normalize_git_url(fetch_url) == _normalize_git_url(expected_url),
            push_url == "DISABLED",
            effective_fetch_matches,
            effective_push_urls == ["DISABLED"],
            hooks_path == ".git/hooks-disabled",
            not unsafe_config_keys,
            bool(branch),
        )
    )
    message = (
        "audited base and source lineage verified; worktree not inspected"
        if valid
        else "source identity mismatch"
    )
    return CheckoutStatus(
        installed=True,
        source_valid=valid,
        target=target,
        expected_revision=expected_revision,
        base_revision=base,
        head_revision=head,
        branch=branch or None,
        dirty=None,
        fetch_url=fetch_url,
        push_url=push_url,
        message=message,
    )


def install_checkout(
    *,
    source_url: str,
    revision: str,
    target: Path,
    learner_branch: str = LEARNER_BRANCH,
) -> CheckoutStatus:
    """Clone one fixed source into a new target and prepare a learner branch.

    The public CLI supplies only audited HTTPS URLs. Tests may use a local Git
    remote to exercise this function without network access.
    """

    target = target.resolve(strict=False)
    parent = target.parent.resolve(strict=False)
    if _path_lexically_exists(target):
        raise ExternalCourseError(f"refusing to overwrite existing target: {target}")
    parent.mkdir(parents=True, exist_ok=True)
    staging = parent / f".{target.name}.install-{uuid.uuid4().hex}"
    if not _is_descendant(staging.resolve(strict=False), parent):
        raise ExternalCourseError("temporary checkout escaped its intended parent")
    try:
        _run_git(["init", "--quiet", str(staging)])
        _run_git(["config", "core.hooksPath", ".git/hooks-disabled"], cwd=staging)
        _run_git(["remote", "add", "origin", source_url], cwd=staging)
        _run_git(
            ["config", "--replace-all", "remote.origin.fetch", _audited_fetch_spec(revision)],
            cwd=staging,
        )
        _run_git(["config", "remote.origin.tagOpt", "--no-tags"], cwd=staging)
        _run_git(
            [
                "fetch",
                "--depth=1",
                "--no-tags",
                "origin",
                _audited_fetch_spec(revision),
            ],
            cwd=staging,
        )
        _run_git(["checkout", "--detach", AUDITED_REMOTE_REF], cwd=staging)
        _run_git(["update-ref", UPSTREAM_REF, revision], cwd=staging)
        _run_git(["config", UPSTREAM_CONFIG, revision], cwd=staging)
        _run_git(["switch", "-c", learner_branch], cwd=staging)
        _run_git(["remote", "set-url", "--push", "origin", "DISABLED"], cwd=staging)
        status = inspect_checkout(
            target=staging,
            expected_url=source_url,
            expected_revision=revision,
        )
        if not status.source_valid:
            raise ExternalCourseError(
                f"new checkout failed source verification: {status.message}"
            )
        _move_staging_without_overwrite(staging, target)
    except Exception as error:
        if _path_lexically_exists(staging):
            try:
                _remove_install_staging(staging, parent)
            except (OSError, ExternalCourseError) as cleanup_error:
                raise ExternalCourseError(
                    "external course installation failed and its staging directory could not "
                    f"be removed safely: {staging} ({cleanup_error})"
                ) from error
        if isinstance(error, ExternalCourseError):
            raise
        if isinstance(error, (OSError, UnicodeError)):
            raise ExternalCourseError(
                "external course installation failed during a filesystem operation "
                f"({type(error).__name__})"
            ) from error
        raise
    final_status = inspect_checkout(
        target=target,
        expected_url=source_url,
        expected_revision=revision,
    )
    if not final_status.source_valid:
        raise ExternalCourseError(
            "installed checkout failed final source verification: "
            f"{final_status.message}; it was left in place for manual inspection"
        )
    return final_status


def _select_sources(
    sources: Mapping[str, AssignmentSource], ids: Sequence[str], *, select_all: bool
) -> list[AssignmentSource]:
    if select_all and ids:
        raise ExternalCourseError("use assignment IDs or --all, not both")
    if not select_all and not ids:
        raise ExternalCourseError("provide at least one assignment ID or --all")
    selected_ids = list(sources) if select_all else list(ids)
    unknown = sorted(set(selected_ids) - set(sources))
    if unknown:
        raise ExternalCourseError(f"unknown external assignment IDs: {unknown}")
    return [sources[item] for item in selected_ids]


def _display_target(target: Path, repo_root: Path) -> str:
    try:
        return target.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return "<outside-repository>"


def _redact_repository_path(value: str, repo_root: Path) -> str:
    flags = re.IGNORECASE if os.name == "nt" else 0
    redacted = re.sub(re.escape(str(repo_root.resolve())), "<repository>", value, flags=flags)
    return redacted.replace(repo_root.resolve().as_posix(), "<repository>")


def _print_status(
    source: AssignmentSource, status: CheckoutStatus, *, repo_root: Path
) -> None:
    state = "valid" if status.source_valid else ("invalid" if status.installed else "missing")
    print(f"{source.id}: {state}")
    print(f"  target: {_display_target(status.target, repo_root)}")
    print(f"  expected base: {status.expected_revision}")
    if status.installed:
        print(f"  recorded base: {status.base_revision or 'unknown'}")
        print(f"  HEAD: {status.head_revision or 'unknown'}")
        print(f"  branch: {status.branch or 'unknown'}")
        print(
            "  learner commits: "
            f"{'present' if status.head_revision != status.base_revision else 'none'}"
        )
        print("  learner changes: not inspected (run `git status` yourself after review)")
        fetch_matches = bool(status.fetch_url) and (
            _normalize_git_url(status.fetch_url) == _normalize_git_url(source.repository_url)
        )
        print(
            "  origin fetch: "
            + ("matches audited URL" if fetch_matches else "mismatch (value hidden)")
        )
        print(
            "  origin push: "
            + ("disabled" if status.push_url == "DISABLED" else "mismatch (value hidden)")
        )
    print(f"  result: {status.message}")


def _show_source(source: AssignmentSource) -> None:
    assignment = source.assignment
    reference = source.reference
    kinds = {"coding": 0, "experiment": 0, "analysis": 0}
    for problem in assignment["problems"]:
        kinds[problem["kind"]] += 1
    licenses = (
        ", ".join(item["spdx"] for item in reference["licenses"])
        if reference["license_status"] == "verified"
        else "not found at audited revision; no redistribution permission assumed"
    )
    print(f"{source.id}: {assignment['title']}")
    print(f"  relationship: {source.pack['non_affiliation_notice']}")
    print(f"  official course: {source.pack['official_course_url']}")
    print(f"  source: {source.repository_url}")
    print(f"  revision: {source.revision}")
    print(f"  upstream offering note: {assignment['upstream_offering_note']}")
    print(f"  license audit: {licenses}")
    print(f"  license evidence: {reference['license_audit_url']}")
    print(f"  license audit method: {reference['license_audit_method']}")
    print(
        "  inventory: "
        f"{len(assignment['problems'])} problems "
        f"({kinds['coding']} coding, {kinds['experiment']} experiment, "
        f"{kinds['analysis']} analysis), {len(assignment['adapter_functions'])} adapters, "
        f"{len(assignment['test_nodes'])} test nodes"
    )
    print(f"  task card: {assignment['task_card']}")
    print(f"  integration status: {assignment['integration_status']}")
    print(
        "  selection mode: "
        + (
            "implementation"
            if assignment["integration_status"] == "implementation-ready"
            else "preview-only"
        )
    )
    print(
        "  aggregate only: canonical problem groups below are Preview-only "
        "and do not enter the native Workspace"
    )
    prerequisites = assignment["prerequisites"]
    print(
        "  assignment prerequisites: "
        + (", ".join(prerequisites) if prerequisites else "none registered")
    )
    readiness = assignment["native_readiness"]
    print(
        "  native readiness: "
        + (", ".join(readiness) if readiness else "no native readiness claims registered")
    )
    print("  runtime tiers:")
    for tier in assignment["runtime_tiers"]:
        print(
            f"    {tier['id']}: availability={tier['availability']}, "
            f"role={tier['completion_role']}"
        )
    print("  canonical problem-group tasks:")
    for group in assignment["problem_groups"]:
        group_prerequisites = [
            f"{source.id}-{item}" for item in group["prerequisite_group_ids"]
        ]
        print(
            f"    {source.id}-{group['id']}: role={group['completion_role']}, "
            f"companion-runtime={group['runtime_tier']}, "
            f"official-runtime={group['official_runtime_tier']}, "
            f"priority={group['priority']}, "
            "prerequisites="
            + (",".join(group_prerequisites) if group_prerequisites else "none")
        )
    print(f"  AI help cap: {source.pack['academic_integrity']['maximum_ai_help']}")
    print(f"  direct AI implementation: forbidden")
    print(f"  academic-integrity policy: {source.pack['academic_integrity']['policy_url']}")
    if assignment["spoiler_for"]:
        print(f"  spoiler warning: contains material for {', '.join(assignment['spoiler_for'])}")


def _source_payload(
    source: AssignmentSource, *, checkout_state: str | None = None
) -> dict[str, Any]:
    assignment = source.assignment
    reference = source.reference
    kinds = {"coding": 0, "experiment": 0, "analysis": 0}
    for problem in assignment["problems"]:
        kinds[problem["kind"]] += 1
    payload: dict[str, Any] = {
        "id": source.id,
        "title": assignment["title"],
        "relationship": source.pack["non_affiliation_notice"],
        "official_course_url": source.pack["official_course_url"],
        "repository_url": source.repository_url,
        "pinned_revision": source.revision,
        "upstream_offering_note": assignment["upstream_offering_note"],
        "license": {
            "status": reference["license_status"],
            "spdx": [item["spdx"] for item in reference["licenses"]],
            "evidence_url": reference["license_audit_url"],
            "audit_method": reference["license_audit_method"],
        },
        "inventory": {
            "problems": len(assignment["problems"]),
            "problem_kinds": kinds,
            "adapters": len(assignment["adapter_functions"]),
            "test_nodes": len(assignment["test_nodes"]),
        },
        "task_card": assignment["task_card"],
        "integration_status": assignment["integration_status"],
        "selection_mode": (
            "implementation"
            if assignment["integration_status"] == "implementation-ready"
            else "preview-only"
        ),
        "prerequisites": list(assignment["prerequisites"]),
        "native_readiness": list(assignment["native_readiness"]),
        "runtime_tiers": list(assignment["runtime_tiers"]),
        "problem_group_tasks": [
            {
                "canonical_task_id": f"{source.id}-{group['id']}",
                "completion_role": group["completion_role"],
                "companion_runtime": group["runtime_tier"],
                "official_runtime": group["official_runtime_tier"],
                "priority": group["priority"],
                "prerequisites": [
                    f"{source.id}-{item}" for item in group["prerequisite_group_ids"]
                ],
                "problem_ids": list(group["problem_ids"]),
                "evidence": list(group["evidence"]),
                "capabilities": list(group["capabilities"]),
            }
            for group in assignment["problem_groups"]
        ],
        "academic_integrity": {
            "maximum_ai_help": source.pack["academic_integrity"]["maximum_ai_help"],
            "direct_implementation_allowed": False,
            "policy_url": source.pack["academic_integrity"]["policy_url"],
        },
        "spoiler_for": list(assignment["spoiler_for"]),
    }
    if checkout_state is not None:
        payload["checkout_state"] = checkout_state
    return payload


def _group_test_commands(group_source: GroupSource) -> list[Mapping[str, Any]]:
    command_ids = {
        evidence.split(":", 1)[1]
        for evidence in group_source.group["evidence"]
        if evidence.startswith("test-command:")
    }
    return [
        command
        for command in group_source.assignment_source.assignment["test_commands"]
        if command["id"] in command_ids
    ]


def _group_payload(group_source: GroupSource) -> dict[str, Any]:
    source = group_source.assignment_source
    assignment = source.assignment
    group = group_source.group
    return {
        "canonical_task_id": group_source.id,
        "assignment_id": source.id,
        "assignment_title": assignment["title"],
        "task_card": assignment["task_card"],
        "relationship": source.pack["non_affiliation_notice"],
        "source": {
            "repository_url": source.repository_url,
            "pinned_revision": source.revision,
            "upstream_offering_note": assignment["upstream_offering_note"],
        },
        "problem_ids": list(group["problem_ids"]),
        "capabilities": list(group["capabilities"]),
        "acceptance_evidence": list(group["evidence"]),
        "related_test_commands": list(_group_test_commands(group_source)),
        "completion_role": group["completion_role"],
        "companion_runtime": group["runtime_tier"],
        "official_runtime": group["official_runtime_tier"],
        "priority": group["priority"],
        "prerequisites": [
            f"{source.id}-{item}" for item in group["prerequisite_group_ids"]
        ],
        "selection_mode": (
            "implementation"
            if assignment["integration_status"] == "implementation-ready"
            else "preview-only"
        ),
        "gate": {
            "assignment_prerequisites": list(assignment["prerequisites"]),
            "native_readiness": list(assignment["native_readiness"]),
            "maximum_ai_help": source.pack["academic_integrity"]["maximum_ai_help"],
            "direct_implementation_allowed": False,
            "policy_url": source.pack["academic_integrity"]["policy_url"],
            "spoiler_for": list(assignment["spoiler_for"]),
        },
        "status_contract": {
            "learner_status_scope": "companion-runtime-only",
            "portable_aggregate_reviewed": (
                "all portable-required problem-group tasks in this assignment are reviewed"
            ),
            "portable_aggregate_retained_7d": (
                "all portable-required problem-group tasks in this assignment are retained_7d"
            ),
            "portable_aggregate_mastered": (
                "all portable-required problem-group tasks in this assignment are mastered"
            ),
            "official_execution": (
                "separate reviewed evidence at official_runtime; never implied by mastered alone"
            ),
        },
        "retention": {
            "d_plus_2": (
                "without opening the checkout, rebuild or re-derive one capability from this "
                "group using a different interface and toy fixture"
            ),
            "d_plus_7": (
                "repeat this group's contract under a changed shape, data, resource, or failure "
                "constraint and answer a group-specific oral question"
            ),
        },
        "automatic_execution_allowed": False,
    }


def _show_group(group_source: GroupSource) -> None:
    payload = _group_payload(group_source)
    print(f"{payload['canonical_task_id']}: {payload['assignment_title']}")
    print(f"  assignment: {payload['assignment_id']}")
    print(f"  task card: {payload['task_card']}")
    print(f"  role: {payload['completion_role']}")
    print(f"  companion runtime: {payload['companion_runtime']}")
    print(f"  official runtime: {payload['official_runtime']}")
    print(f"  priority: {payload['priority']}")
    print(f"  selection mode: {payload['selection_mode']}")
    print(
        "  problem-group prerequisites: "
        + (", ".join(payload["prerequisites"]) if payload["prerequisites"] else "none")
    )
    print(f"  learner status scope: {payload['status_contract']['learner_status_scope']}")
    print(
        "  portable aggregate: all portable-required groups must independently reach "
        "the claimed reviewed/retained_7d/mastered status"
    )
    print("  problems:")
    for problem_id in payload["problem_ids"]:
        print(f"    {problem_id}")
    print("  capabilities:")
    for capability in payload["capabilities"]:
        print(f"    {capability}")
    print("  acceptance evidence:")
    for evidence in payload["acceptance_evidence"]:
        print(f"    {evidence}")
    print("  related upstream commands (review and run yourself):")
    commands = payload["related_test_commands"]
    if commands:
        for command in commands:
            print(
                f"    [{command['id']} | {command['scope']} | "
                f"{command['runtime_tier']}] {command['command']}"
            )
    else:
        print("    none; use the listed artifact/oral evidence contract")
    print(f"  D+2: {payload['retention']['d_plus_2']}")
    print(f"  D+7: {payload['retention']['d_plus_7']}")
    print("  automatic execution: forbidden")


def _print_commands(source: AssignmentSource, *, repo_root: Path) -> None:
    target = checkout_target(source, repo_root=repo_root)
    print(
        "Review dependencies before running third-party code. Checkout: "
        f"{_display_target(target, repo_root)}"
    )
    print("Setup commands (run yourself inside that checkout):")
    for command in source.assignment["setup_commands"]:
        print(f"  {command}")
    print("Validation commands (run yourself; scopes are not interchangeable):")
    for item in source.assignment["test_commands"]:
        print(
            f"  [{item['id']} | {item['scope']} | {item['runtime_tier']}] "
            f"{item['command']}"
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    listing = subparsers.add_parser("list", help="list audited external assignments")
    listing.add_argument("--json", action="store_true", help="emit machine-readable metadata")

    show = subparsers.add_parser("show", help="show one assignment's audited metadata")
    show.add_argument("assignment_id")
    show.add_argument("--json", action="store_true", help="emit machine-readable metadata")

    show_group = subparsers.add_parser(
        "show-group",
        help="show one canonical problem-group task and only its relevant evidence",
    )
    show_group.add_argument("canonical_task_id")
    show_group.add_argument("--json", action="store_true", help="emit machine-readable metadata")

    commands = subparsers.add_parser("commands", help="print, but do not run, upstream commands")
    commands.add_argument("assignment_id")

    for name, help_text in (
        ("status", "inspect installed checkouts without changing them"),
        ("verify", "verify installed source identity and return non-zero on mismatch"),
    ):
        child = subparsers.add_parser(name, help=help_text)
        child.add_argument("assignment_ids", nargs="*")
        child.add_argument("--all", action="store_true", help="select all assignments")
    install = subparsers.add_parser(
        "install",
        help="install one audited fixed revision into .external",
    )
    install.add_argument("assignment_id")
    install.add_argument(
        "--acknowledge-policy",
        action="store_true",
        help="confirm that upstream license and academic-integrity policies were read",
    )
    install.add_argument(
        "--acknowledge-spoilers",
        action="store_true",
        help="confirm any earlier-assignment spoiler warning shown by `show`",
    )
    return parser


def main(argv: Sequence[str] | None = None, *, repo_root: Path = REPO_ROOT) -> int:
    args = _parser().parse_args(argv)
    try:
        sources = load_assignment_sources(repo_root=repo_root)
        if args.command == "show-group":
            group_source = load_group_sources(sources).get(args.canonical_task_id)
            if group_source is None:
                raise ExternalCourseError(
                    f"unknown canonical problem-group task ID: {args.canonical_task_id}"
                )
            if args.json:
                print(
                    json.dumps(
                        {
                            "schema_version": 1,
                            "ok": True,
                            "problem_group_task": _group_payload(group_source),
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )
            else:
                _show_group(group_source)
            return 0
        if args.command == "list":
            payloads: list[dict[str, Any]] = []
            if not args.json:
                print("Independent companion metadata; not affiliated with Stanford University.")
                print("Run `show <ID>` before installation to review policy, license, and spoilers.")
            for source in sources.values():
                license_status = source.reference["license_status"]
                checkout = inspect_checkout(
                    target=checkout_target(source, repo_root=repo_root),
                    expected_url=source.repository_url,
                    expected_revision=source.revision,
                )
                checkout_state = (
                    "valid"
                    if checkout.source_valid
                    else ("invalid" if checkout.installed else "missing")
                )
                if args.json:
                    payloads.append(_source_payload(source, checkout_state=checkout_state))
                else:
                    print(
                        f"{source.id}\tlicense={license_status}\t"
                        f"integration={source.assignment['integration_status']}\t"
                        f"checkout={checkout_state}\t"
                        f"revision={source.revision[:12]}\t{source.assignment['title']}"
                    )
            if args.json:
                print(
                    json.dumps(
                        {"schema_version": 1, "ok": True, "assignments": payloads},
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )
            return 0
        if args.command in {"show", "commands"}:
            source = sources.get(args.assignment_id)
            if source is None:
                raise ExternalCourseError(
                    f"unknown external assignment ID: {args.assignment_id}"
                )
            if args.command == "show":
                if args.json:
                    status = inspect_checkout(
                        target=checkout_target(source, repo_root=repo_root),
                        expected_url=source.repository_url,
                        expected_revision=source.revision,
                    )
                    checkout_state = (
                        "valid"
                        if status.source_valid
                        else ("invalid" if status.installed else "missing")
                    )
                    print(
                        json.dumps(
                            {
                                "schema_version": 1,
                                "ok": True,
                                "assignment": _source_payload(
                                    source, checkout_state=checkout_state
                                ),
                            },
                            ensure_ascii=False,
                            sort_keys=True,
                        )
                    )
                else:
                    _show_source(source)
            else:
                _print_commands(source, repo_root=repo_root)
            return 0

        if args.command == "install":
            source = sources.get(args.assignment_id)
            if source is None:
                raise ExternalCourseError(
                    f"unknown external assignment ID: {args.assignment_id}"
                )
            selected = [source]
            if not args.acknowledge_policy:
                print(
                    "Refusing installation until you read the upstream license and academic-integrity "
                    "policy. Re-run with --acknowledge-policy.",
                    file=sys.stderr,
                )
                return 2
            spoilers = source.assignment["spoiler_for"]
            if spoilers and not args.acknowledge_spoilers:
                print(
                    f"Refusing installation: {source.id} contains material for "
                    f"{', '.join(spoilers)}. Pass --acknowledge-spoilers only after the "
                    "corresponding integration Gate.",
                    file=sys.stderr,
                )
                return 2
            _show_source(source)
            for source in selected:
                target = checkout_target(source, repo_root=repo_root)
                print(f"Installing {source.id} at audited revision {source.revision}...")
                status = install_checkout(
                    source_url=source.repository_url,
                    revision=source.revision,
                    target=target,
                )
                _print_status(source, status, repo_root=repo_root)
            print("Third-party code was installed but not executed. Review it before running commands.")
            return 0

        selected = _select_sources(sources, args.assignment_ids, select_all=args.all)
        failures = 0
        for source in selected:
            status = inspect_checkout(
                target=checkout_target(source, repo_root=repo_root),
                expected_url=source.repository_url,
                expected_revision=source.revision,
            )
            _print_status(source, status, repo_root=repo_root)
            if args.command == "verify" and not status.source_valid:
                failures += 1
        return 1 if failures else 0
    except (ExternalCourseError, CurriculumValidationError) as error:
        safe_error = _redact_repository_path(str(error), repo_root)
        if getattr(args, "json", False):
            print(
                json.dumps(
                    {"schema_version": 1, "ok": False, "error": safe_error},
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
        else:
            print(
                f"ERROR: {safe_error}",
                file=sys.stderr,
            )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
