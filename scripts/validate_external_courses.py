"""Validate external course-pack metadata and its generated navigation.

The validator is deliberately offline. It validates audited, pinned metadata;
it never clones an upstream repository and never executes third-party code.
"""

from __future__ import annotations

import argparse
from datetime import date
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

try:
    from scripts.validate_curriculum import (
        CurriculumValidationError,
        REFERENCE_RELATIVE,
        REPO_ROOT,
        load_json,
        validate_reference_registry,
    )
except ModuleNotFoundError:  # Direct execution: python scripts/validate_external_courses.py
    from validate_curriculum import (  # type: ignore[no-redef]
        CurriculumValidationError,
        REFERENCE_RELATIVE,
        REPO_ROOT,
        load_json,
        validate_reference_registry,
    )


CATALOG_RELATIVE = "curriculum/external/catalog.json"
NAVIGATION_RELATIVE = "curriculum/external/NAVIGATION.md"

CATALOG_KEYS = {"schema_version", "packs"}
PACK_ENTRY_KEYS = {"id", "order", "manifest_file"}
MANIFEST_KEYS = {
    "schema_version",
    "pack_id",
    "title",
    "provider",
    "offering",
    "official_course_url",
    "audited_on",
    "source_mode",
    "install_root",
    "non_affiliation_notice",
    "academic_integrity",
    "vendored_material",
    "expected_assignment_count",
    "assignments",
}
ACADEMIC_INTEGRITY_KEYS = {
    "policy_url",
    "maximum_ai_help",
    "direct_implementation_allowed",
    "notice",
}
ASSIGNMENT_KEYS = {
    "id",
    "order",
    "title",
    "reference_id",
    "upstream_offering_note",
    "checkout_directory",
    "task_card",
    "prerequisites",
    "spoiler_for",
    "native_readiness",
    "handouts",
    "adapter_functions",
    "test_nodes",
    "setup_commands",
    "test_commands",
    "runtime_tiers",
    "expected_problem_count",
    "expected_adapter_count",
    "expected_test_node_count",
    "problems",
    "problem_groups",
    "integration_status",
}
HANDOUT_KEYS = {"id", "path"}
TEST_COMMAND_KEYS = {"id", "command", "scope", "runtime_tier"}
RUNTIME_TIER_KEYS = {"id", "title", "availability", "completion_role"}
PROBLEM_KEYS = {"id", "kind", "required", "handout_id"}
PROBLEM_GROUP_KEYS = {
    "id",
    "prerequisite_group_ids",
    "problem_ids",
    "evidence",
    "runtime_tier",
    "official_runtime_tier",
    "completion_role",
    "priority",
    "capabilities",
}

ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")
UPSTREAM_TEST_NODE_PATTERN = re.compile(
    r"^(tests/[A-Za-z0-9_./-]+\.py)::(test_[A-Za-z0-9_]+)$"
)
SAFE_PATH_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PROBLEM_KINDS = {"analysis", "coding", "experiment"}
TEST_SCOPES = {"student-contract", "upstream-infrastructure", "optional-supplement"}
RUNTIME_AVAILABILITY = {
    "local-cpu",
    "local-cuda",
    "multi-gpu",
    "hosted-course-service",
    "manual",
}
PRIORITIES = {"P0", "P1", "P2"}
RUNTIME_COMPLETION_ROLES = {"portable-required", "official-full", "optional"}
GROUP_COMPLETION_ROLES = {
    "portable-required",
    "portable-elective",
    "official-only",
    "optional-capstone",
}
INTEGRATION_STATUSES = {"inventory-audited"}
EXTERNAL_CARD_HEADINGS = (
    "## 定位与边界",
    "## 前置 Gate",
    "## 上游作业覆盖",
    "## 安装与验证",
    "## AI 与学术诚信",
    "## 证据与验收",
    "## D+2 / D+7",
    "## 资源与停止条件",
)


def _fail(message: str) -> None:
    raise CurriculumValidationError(message)


def _object(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{context} must be an object")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], context: str) -> None:
    actual = set(value)
    if actual != expected:
        _fail(
            f"{context} keys mismatch; missing={sorted(expected - actual)}, "
            f"unknown={sorted(actual - expected)}"
        )


def _string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        _fail(f"{context} must be a non-empty trimmed string")
    if "\n" in value or "\r" in value:
        _fail(f"{context} must be one line")
    return value


def _identifier(value: Any, context: str) -> str:
    identifier = _string(value, context)
    if not ID_PATTERN.fullmatch(identifier):
        _fail(f"{context} has an invalid identifier: {identifier!r}")
    return identifier


def _integer(value: Any, context: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        _fail(f"{context} must be an integer >= {minimum}")
    return value


def _boolean(value: Any, context: str) -> bool:
    if not isinstance(value, bool):
        _fail(f"{context} must be a boolean")
    return value


def _list(value: Any, context: str, *, allow_empty: bool = False) -> list[Any]:
    if not isinstance(value, list) or (not allow_empty and not value):
        suffix = "" if allow_empty else " and cannot be empty"
        _fail(f"{context} must be a list{suffix}")
    return value


def _string_list(value: Any, context: str, *, allow_empty: bool = False) -> list[str]:
    items = _list(value, context, allow_empty=allow_empty)
    result = [_string(item, f"{context}[{index}]") for index, item in enumerate(items)]
    if len(result) != len(set(result)):
        _fail(f"{context} cannot contain duplicates")
    return result


def _enum(value: Any, allowed: set[str], context: str) -> str:
    item = _string(value, context)
    if item not in allowed:
        _fail(f"{context} must be one of {sorted(allowed)}; found {item!r}")
    return item


def _validate_problem_group_dag(
    assignment_id: str,
    dependencies: Mapping[str, Sequence[str]],
) -> None:
    states: dict[str, int] = {}

    def visit(group_id: str, trail: tuple[str, ...]) -> None:
        state = states.get(group_id, 0)
        if state == 2:
            return
        if state == 1:
            cycle = " -> ".join((*trail, group_id))
            _fail(f"assignment {assignment_id} problem-group dependency cycle: {cycle}")
        states[group_id] = 1
        for prerequisite in dependencies[group_id]:
            visit(prerequisite, (*trail, group_id))
        states[group_id] = 2

    for group_id in dependencies:
        visit(group_id, ())


def _https_url(value: Any, context: str) -> str:
    url = _string(value, context)
    try:
        parsed = urlparse(url)
        parsed.port
        username = parsed.username
        password = parsed.password
    except ValueError as error:
        _fail(f"{context} must be a valid public HTTPS URL")
        raise AssertionError("unreachable") from error
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or username
        or password
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        _fail(f"{context} must be a public HTTPS URL without credentials")
    return url


def _safe_relative_path(
    value: Any,
    context: str,
    *,
    prefix: str | None = None,
    suffix: str | None = None,
) -> str:
    text = _string(value, context)
    if "\\" in text or not SAFE_PATH_PATTERN.fullmatch(text):
        _fail(f"{context} must be a safe POSIX repository-relative path")
    relative = PurePosixPath(text)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        _fail(f"{context} must be a safe repository-relative path")
    if prefix is not None and not text.startswith(prefix):
        _fail(f"{context} must start with {prefix!r}")
    if suffix is not None and not text.endswith(suffix):
        _fail(f"{context} must end with {suffix!r}")
    return text


def _safe_install_root(value: Any, context: str) -> str:
    text = _string(value, context)
    if "\\" in text or not re.fullmatch(r"\.external/[A-Za-z0-9][A-Za-z0-9._/-]*", text):
        _fail(f"{context} must be a safe path below .external/")
    relative = PurePosixPath(text)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        _fail(f"{context} must be a safe path below .external/")
    return text


def _is_link_or_reparse(path: Path) -> bool:
    file_stat = os.lstat(path)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    attributes = getattr(file_stat, "st_file_attributes", 0)
    return stat.S_ISLNK(file_stat.st_mode) or bool(attributes & reparse_flag)


def _has_exact_case(root: Path, relative: PurePosixPath) -> bool:
    current = root
    for part in relative.parts:
        try:
            names = {entry.name for entry in current.iterdir()}
        except OSError:
            return False
        if part not in names:
            return False
        current = current / part
    return True


def _repository_file(
    root: Path,
    value: Any,
    context: str,
    *,
    prefix: str,
    suffix: str,
) -> tuple[str, Path]:
    text = _safe_relative_path(value, context, prefix=prefix, suffix=suffix)
    relative = PurePosixPath(text)
    current = root
    for part in relative.parts:
        current = current / part
        try:
            if _is_link_or_reparse(current):
                _fail(f"{context} cannot traverse a symlink or reparse point")
        except FileNotFoundError:
            _fail(f"{context} does not exist: {text}")
    if not current.is_file() or not _has_exact_case(root, relative):
        _fail(f"{context} must reference an exact-case regular file: {text}")
    return text, current


def _validate_iso_date(value: Any, context: str) -> str:
    text = _string(value, context)
    try:
        if not ISO_DATE_PATTERN.fullmatch(text):
            raise ValueError
        date.fromisoformat(text)
    except ValueError as error:
        raise CurriculumValidationError(f"{context} must be YYYY-MM-DD") from error
    return text


def _validate_task_card(path: Path, assignment_id: str) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise CurriculumValidationError(
            f"external task card for {assignment_id} must be valid UTF-8"
        ) from error
    missing = [heading for heading in EXTERNAL_CARD_HEADINGS if heading not in text]
    if missing:
        _fail(f"external task card {assignment_id} is missing headings: {missing}")


def _reference_records(repo_root: Path) -> dict[str, Mapping[str, Any]]:
    registry = load_json(repo_root / REFERENCE_RELATIVE)
    validate_reference_registry(registry)
    return {record["id"]: record for record in registry["references"]}


def _validate_assignment(
    raw: Any,
    *,
    repo_root: Path,
    references: Mapping[str, Mapping[str, Any]],
    earlier_assignments: set[str],
) -> Mapping[str, Any]:
    assignment = _object(raw, "external assignment")
    _exact_keys(assignment, ASSIGNMENT_KEYS, "external assignment")
    assignment_id = _identifier(assignment["id"], "external assignment id")
    _integer(assignment["order"], f"assignment {assignment_id} order", minimum=1)
    _string(assignment["title"], f"assignment {assignment_id} title")
    _string(
        assignment["upstream_offering_note"],
        f"assignment {assignment_id} upstream_offering_note",
    )

    reference_id = _identifier(
        assignment["reference_id"], f"assignment {assignment_id} reference_id"
    )
    reference = references.get(reference_id)
    if reference is None:
        _fail(f"assignment {assignment_id} uses unknown reference: {reference_id}")
    if reference["usage"] != "external-course-source":
        _fail(f"assignment {assignment_id} reference must be external-course-source")
    revision = reference["pinned_revision"]
    if not REVISION_PATTERN.fullmatch(revision):
        _fail(f"assignment {assignment_id} reference is not pinned")

    checkout = _identifier(
        assignment["checkout_directory"],
        f"assignment {assignment_id} checkout_directory",
    )
    if "/" in checkout or "\\" in checkout:
        _fail(f"assignment {assignment_id} checkout_directory must be one path segment")

    _, task_card = _repository_file(
        repo_root,
        assignment["task_card"],
        f"assignment {assignment_id} task_card",
        prefix="curriculum/external/",
        suffix=".md",
    )
    _validate_task_card(task_card, assignment_id)

    prerequisites = _string_list(
        assignment["prerequisites"],
        f"assignment {assignment_id} prerequisites",
        allow_empty=True,
    )
    missing_or_late = sorted(set(prerequisites) - earlier_assignments)
    if missing_or_late:
        _fail(
            f"assignment {assignment_id} prerequisites must be earlier assignments: "
            f"{missing_or_late}"
        )
    spoiler_for = _string_list(
        assignment["spoiler_for"],
        f"assignment {assignment_id} spoiler_for",
        allow_empty=True,
    )
    invalid_spoilers = sorted(set(spoiler_for) - earlier_assignments)
    if invalid_spoilers:
        _fail(
            f"assignment {assignment_id} spoilers must name earlier assignments: "
            f"{invalid_spoilers}"
        )
    _string_list(
        assignment["native_readiness"],
        f"assignment {assignment_id} native_readiness",
    )

    handout_ids: set[str] = set()
    for index, raw_handout in enumerate(
        _list(assignment["handouts"], f"assignment {assignment_id} handouts")
    ):
        handout = _object(raw_handout, f"assignment {assignment_id} handouts[{index}]")
        _exact_keys(handout, HANDOUT_KEYS, f"assignment {assignment_id} handouts[{index}]")
        handout_id = _identifier(
            handout["id"], f"assignment {assignment_id} handout id"
        )
        if handout_id in handout_ids:
            _fail(f"assignment {assignment_id} has duplicate handout id: {handout_id}")
        handout_ids.add(handout_id)
        _safe_relative_path(
            handout["path"],
            f"assignment {assignment_id} handout path",
            suffix=".pdf",
        )

    adapters = _string_list(
        assignment["adapter_functions"],
        f"assignment {assignment_id} adapter_functions",
        allow_empty=True,
    )
    for adapter in adapters:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", adapter):
            _fail(f"assignment {assignment_id} has invalid adapter function: {adapter}")
    expected_adapter_count = _integer(
        assignment["expected_adapter_count"],
        f"assignment {assignment_id} expected_adapter_count",
    )
    if len(adapters) != expected_adapter_count:
        _fail(
            f"assignment {assignment_id} expected {expected_adapter_count} adapters, "
            f"found {len(adapters)}"
        )

    test_nodes = _string_list(
        assignment["test_nodes"],
        f"assignment {assignment_id} test_nodes",
        allow_empty=True,
    )
    for node in test_nodes:
        if not UPSTREAM_TEST_NODE_PATTERN.fullmatch(node):
            _fail(f"assignment {assignment_id} has invalid upstream test node: {node}")
    expected_test_node_count = _integer(
        assignment["expected_test_node_count"],
        f"assignment {assignment_id} expected_test_node_count",
    )
    if len(test_nodes) != expected_test_node_count:
        _fail(
            f"assignment {assignment_id} expected {expected_test_node_count} test nodes, "
            f"found {len(test_nodes)}"
        )

    _string_list(
        assignment["setup_commands"],
        f"assignment {assignment_id} setup_commands",
    )

    runtime_ids: set[str] = set()
    runtime_roles: dict[str, str] = {}
    for index, raw_tier in enumerate(
        _list(assignment["runtime_tiers"], f"assignment {assignment_id} runtime_tiers")
    ):
        tier = _object(raw_tier, f"assignment {assignment_id} runtime_tiers[{index}]")
        _exact_keys(tier, RUNTIME_TIER_KEYS, f"assignment {assignment_id} runtime_tiers[{index}]")
        tier_id = _identifier(tier["id"], f"assignment {assignment_id} runtime tier id")
        if tier_id in runtime_ids:
            _fail(f"assignment {assignment_id} has duplicate runtime tier: {tier_id}")
        runtime_ids.add(tier_id)
        _string(tier["title"], f"assignment {assignment_id} runtime tier title")
        _enum(
            tier["availability"],
            RUNTIME_AVAILABILITY,
            f"assignment {assignment_id} runtime availability",
        )
        runtime_roles[tier_id] = _enum(
            tier["completion_role"],
            RUNTIME_COMPLETION_ROLES,
            f"assignment {assignment_id} runtime completion_role",
        )
    if "portable-required" not in runtime_roles.values():
        _fail(f"assignment {assignment_id} requires a portable-required runtime tier")

    command_ids: set[str] = set()
    command_runtime_tiers: dict[str, str] = {}
    for index, raw_command in enumerate(
        _list(assignment["test_commands"], f"assignment {assignment_id} test_commands")
    ):
        command = _object(raw_command, f"assignment {assignment_id} test_commands[{index}]")
        _exact_keys(command, TEST_COMMAND_KEYS, f"assignment {assignment_id} test_commands[{index}]")
        command_id = _identifier(command["id"], f"assignment {assignment_id} command id")
        if command_id in command_ids:
            _fail(f"assignment {assignment_id} has duplicate command id: {command_id}")
        command_ids.add(command_id)
        _string(command["command"], f"assignment {assignment_id} command")
        _enum(command["scope"], TEST_SCOPES, f"assignment {assignment_id} command scope")
        runtime_tier = _identifier(
            command["runtime_tier"], f"assignment {assignment_id} command runtime_tier"
        )
        if runtime_tier not in runtime_ids:
            _fail(f"assignment {assignment_id} command uses unknown runtime tier: {runtime_tier}")
        command_runtime_tiers[command_id] = runtime_tier

    expected_problem_count = _integer(
        assignment["expected_problem_count"],
        f"assignment {assignment_id} expected_problem_count",
        minimum=1,
    )
    problem_ids: set[str] = set()
    for index, raw_problem in enumerate(
        _list(assignment["problems"], f"assignment {assignment_id} problems")
    ):
        problem = _object(raw_problem, f"assignment {assignment_id} problems[{index}]")
        _exact_keys(problem, PROBLEM_KEYS, f"assignment {assignment_id} problems[{index}]")
        problem_id = _identifier(problem["id"], f"assignment {assignment_id} problem id")
        if problem_id in problem_ids:
            _fail(f"assignment {assignment_id} has duplicate problem id: {problem_id}")
        problem_ids.add(problem_id)
        _enum(problem["kind"], PROBLEM_KINDS, f"assignment {assignment_id} problem kind")
        _boolean(problem["required"], f"assignment {assignment_id} problem required")
        handout_id = _identifier(
            problem["handout_id"], f"assignment {assignment_id} problem handout_id"
        )
        if handout_id not in handout_ids:
            _fail(f"assignment {assignment_id} problem uses unknown handout: {handout_id}")
    if len(problem_ids) != expected_problem_count:
        _fail(
            f"assignment {assignment_id} expected {expected_problem_count} problems, "
            f"found {len(problem_ids)}"
        )

    grouped_problem_ids: list[str] = []
    group_ids: set[str] = set()
    group_dependencies: dict[str, list[str]] = {}
    group_roles: dict[str, str] = {}
    for index, raw_group in enumerate(
        _list(assignment["problem_groups"], f"assignment {assignment_id} problem_groups")
    ):
        group = _object(raw_group, f"assignment {assignment_id} problem_groups[{index}]")
        _exact_keys(group, PROBLEM_GROUP_KEYS, f"assignment {assignment_id} problem_groups[{index}]")
        group_id = _identifier(group["id"], f"assignment {assignment_id} group id")
        if group_id in group_ids:
            _fail(f"assignment {assignment_id} has duplicate problem group: {group_id}")
        group_ids.add(group_id)
        group_dependencies[group_id] = _string_list(
            group["prerequisite_group_ids"],
            f"assignment {assignment_id} group {group_id} prerequisite_group_ids",
            allow_empty=True,
        )
        group_problem_ids = _string_list(
            group["problem_ids"], f"assignment {assignment_id} group {group_id} problem_ids"
        )
        unknown = sorted(set(group_problem_ids) - problem_ids)
        if unknown:
            _fail(f"assignment {assignment_id} group {group_id} has unknown problems: {unknown}")
        grouped_problem_ids.extend(group_problem_ids)
        evidence_items = _string_list(
            group["evidence"], f"assignment {assignment_id} group {group_id} evidence"
        )
        for evidence in evidence_items:
            prefix, separator, target = evidence.partition(":")
            if not separator or not target:
                _fail(f"assignment {assignment_id} group {group_id} has invalid evidence: {evidence}")
            if prefix == "test-node" and target not in test_nodes:
                _fail(f"assignment {assignment_id} group {group_id} cites unknown test node: {target}")
            if prefix == "test-command" and target not in command_ids:
                _fail(f"assignment {assignment_id} group {group_id} cites unknown test command: {target}")
            if (
                prefix == "test-command"
                and target in command_runtime_tiers
                and command_runtime_tiers[target] != group["runtime_tier"]
            ):
                _fail(
                    f"assignment {assignment_id} group {group_id} cites test command "
                    "from a different runtime tier"
                )
            if prefix not in {"test-node", "test-command", "artifact", "oral"}:
                _fail(f"assignment {assignment_id} group {group_id} has unsupported evidence: {prefix}")
        runtime_tier = _identifier(
            group["runtime_tier"], f"assignment {assignment_id} group {group_id} runtime_tier"
        )
        if runtime_tier not in runtime_ids:
            _fail(f"assignment {assignment_id} group {group_id} uses unknown runtime tier")
        official_runtime_tier = _identifier(
            group["official_runtime_tier"],
            f"assignment {assignment_id} group {group_id} official_runtime_tier",
        )
        if official_runtime_tier not in runtime_ids:
            _fail(
                f"assignment {assignment_id} group {group_id} uses unknown official runtime tier"
            )
        completion_role = _enum(
            group["completion_role"],
            GROUP_COMPLETION_ROLES,
            f"assignment {assignment_id} group {group_id} completion_role",
        )
        group_roles[group_id] = completion_role
        if (
            completion_role in {"portable-required", "portable-elective"}
            and runtime_roles[runtime_tier] != "portable-required"
        ):
            _fail(
                f"assignment {assignment_id} group {group_id} portable evidence must use "
                "a portable-required runtime tier"
            )
        if (
            completion_role == "official-only"
            and runtime_roles[official_runtime_tier] != "official-full"
        ):
            _fail(
                f"assignment {assignment_id} group {group_id} official-only evidence must "
                "name an official-full runtime tier"
            )
        if (
            completion_role == "optional-capstone"
            and runtime_roles[official_runtime_tier] != "optional"
        ):
            _fail(
                f"assignment {assignment_id} group {group_id} optional capstone must use "
                "an optional runtime tier"
            )
        _enum(group["priority"], PRIORITIES, f"assignment {assignment_id} group priority")
        _string_list(
            group["capabilities"], f"assignment {assignment_id} group {group_id} capabilities"
        )
    for group_id, prerequisites in group_dependencies.items():
        unknown_prerequisites = sorted(set(prerequisites) - group_ids)
        if unknown_prerequisites:
            _fail(
                f"assignment {assignment_id} group {group_id} has unknown group prerequisites: "
                f"{unknown_prerequisites}"
            )
        if group_id in prerequisites:
            _fail(f"assignment {assignment_id} group {group_id} cannot depend on itself")
        if group_roles[group_id] in {"portable-required", "portable-elective"}:
            nonportable = sorted(
                prerequisite
                for prerequisite in prerequisites
                if group_roles[prerequisite] not in {"portable-required", "portable-elective"}
            )
            if nonportable:
                _fail(
                    f"assignment {assignment_id} portable group {group_id} cannot depend on "
                    f"non-portable groups: {nonportable}"
                )
        if group_roles[group_id] == "portable-required":
            elective_prerequisites = sorted(
                prerequisite
                for prerequisite in prerequisites
                if group_roles[prerequisite] != "portable-required"
            )
            if elective_prerequisites:
                _fail(
                    f"assignment {assignment_id} portable-required group {group_id} cannot "
                    f"make elective groups mandatory: {elective_prerequisites}"
                )
    _validate_problem_group_dag(assignment_id, group_dependencies)
    if len(grouped_problem_ids) != len(set(grouped_problem_ids)):
        _fail(f"assignment {assignment_id} assigns a problem to multiple groups")
    ungrouped = sorted(problem_ids - set(grouped_problem_ids))
    if ungrouped:
        _fail(f"assignment {assignment_id} has ungrouped problems: {ungrouped}")

    _enum(
        assignment["integration_status"],
        INTEGRATION_STATUSES,
        f"assignment {assignment_id} integration_status",
    )
    return assignment


def validate_external_courses(
    *, repo_root: Path = REPO_ROOT, check_navigation: bool = True
) -> tuple[Mapping[str, Any], list[Mapping[str, Any]], str]:
    root = repo_root.resolve()
    _, catalog_path = _repository_file(
        root,
        CATALOG_RELATIVE,
        "external course catalog",
        prefix="curriculum/external/",
        suffix=".json",
    )
    catalog = load_json(catalog_path)
    _exact_keys(catalog, CATALOG_KEYS, "external course catalog")
    if catalog["schema_version"] != 1:
        _fail("external course catalog schema_version must be 1")
    references = _reference_records(root)

    pack_ids: set[str] = set()
    pack_orders: set[int] = set()
    global_assignment_ids: set[str] = set()
    checkout_targets: set[str] = set()
    manifests: list[Mapping[str, Any]] = []
    for index, raw_entry in enumerate(_list(catalog["packs"], "external course packs")):
        entry = _object(raw_entry, f"external course packs[{index}]")
        _exact_keys(entry, PACK_ENTRY_KEYS, f"external course packs[{index}]")
        pack_id = _identifier(entry["id"], f"external course packs[{index}].id")
        order = _integer(entry["order"], f"external course pack {pack_id} order", minimum=1)
        if pack_id in pack_ids or order in pack_orders:
            _fail(f"duplicate external course pack id/order: {pack_id}/{order}")
        pack_ids.add(pack_id)
        pack_orders.add(order)
        _, manifest_path = _repository_file(
            root,
            entry["manifest_file"],
            f"external course pack {pack_id} manifest",
            prefix="curriculum/external/",
            suffix=".json",
        )
        manifest = load_json(manifest_path)
        _exact_keys(manifest, MANIFEST_KEYS, f"external course pack {pack_id}")
        if manifest["schema_version"] != 1 or manifest["pack_id"] != pack_id:
            _fail(f"external course pack {pack_id} manifest identity/version mismatch")
        _string(manifest["title"], f"external course pack {pack_id} title")
        _string(manifest["provider"], f"external course pack {pack_id} provider")
        _string(manifest["offering"], f"external course pack {pack_id} offering")
        _https_url(manifest["official_course_url"], f"external course pack {pack_id} URL")
        _validate_iso_date(manifest["audited_on"], f"external course pack {pack_id} audited_on")
        if manifest["source_mode"] != "external-pinned-checkout":
            _fail(f"external course pack {pack_id} must use external-pinned-checkout")
        install_root = _safe_install_root(
            manifest["install_root"], f"external course pack {pack_id} install_root"
        )
        if not install_root.startswith(".external/"):
            _fail(f"external course pack {pack_id} must install below .external/")
        _string(
            manifest["non_affiliation_notice"],
            f"external course pack {pack_id} non_affiliation_notice",
        )
        policy = _object(
            manifest["academic_integrity"],
            f"external course pack {pack_id} academic_integrity",
        )
        _exact_keys(
            policy,
            ACADEMIC_INTEGRITY_KEYS,
            f"external course pack {pack_id} academic_integrity",
        )
        _https_url(policy["policy_url"], f"external course pack {pack_id} policy URL")
        if policy["maximum_ai_help"] not in {"H0", "H1", "H2"}:
            _fail(f"external course pack {pack_id} maximum_ai_help must be H0, H1, or H2")
        if _boolean(
            policy["direct_implementation_allowed"],
            f"external course pack {pack_id} direct_implementation_allowed",
        ):
            _fail(f"external course pack {pack_id} cannot allow direct AI implementation")
        _string(policy["notice"], f"external course pack {pack_id} policy notice")
        if _list(
            manifest["vendored_material"],
            f"external course pack {pack_id} vendored_material",
            allow_empty=True,
        ):
            _fail(f"external course pack {pack_id} cannot vendor upstream material")

        expected_assignment_count = _integer(
            manifest["expected_assignment_count"],
            f"external course pack {pack_id} expected_assignment_count",
            minimum=1,
        )
        assignments = sorted(
            _list(manifest["assignments"], f"external course pack {pack_id} assignments"),
            key=lambda item: item.get("order", -1) if isinstance(item, dict) else -1,
        )
        if len(assignments) != expected_assignment_count:
            _fail(
                f"external course pack {pack_id} expected {expected_assignment_count} assignments, "
                f"found {len(assignments)}"
            )
        assignment_ids: set[str] = set()
        assignment_orders: set[int] = set()
        validated_assignments: list[Mapping[str, Any]] = []
        for raw_assignment in assignments:
            assignment = _validate_assignment(
                raw_assignment,
                repo_root=root,
                references=references,
                earlier_assignments=assignment_ids,
            )
            assignment_id = assignment["id"]
            order = assignment["order"]
            if assignment_id in assignment_ids or order in assignment_orders:
                _fail(f"pack {pack_id} has duplicate assignment id/order: {assignment_id}/{order}")
            assignment_ids.add(assignment_id)
            assignment_orders.add(order)
            if assignment_id in global_assignment_ids:
                _fail(f"duplicate external assignment id across packs: {assignment_id}")
            global_assignment_ids.add(assignment_id)
            checkout_target = (
                PurePosixPath(install_root) / assignment["checkout_directory"]
            ).as_posix()
            checkout_key = checkout_target.casefold()
            if checkout_key in checkout_targets:
                _fail(f"duplicate external checkout target: {checkout_target}")
            checkout_targets.add(checkout_key)
            validated_assignments.append(assignment)
        manifest = dict(manifest)
        manifest["assignments"] = validated_assignments
        manifests.append(manifest)

    expected_navigation = render_navigation(catalog, manifests, references)
    if check_navigation:
        _, navigation_path = _repository_file(
            root,
            NAVIGATION_RELATIVE,
            "external course navigation",
            prefix="curriculum/external/",
            suffix=".md",
        )
        try:
            actual = navigation_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise CurriculumValidationError(
                "external course navigation is missing or invalid"
            ) from error
        if actual != expected_navigation:
            _fail(
                "curriculum/external/NAVIGATION.md is stale; run "
                "python scripts/validate_external_courses.py --write-navigation"
            )
    return catalog, manifests, expected_navigation


def _escape(value: Any) -> str:
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def render_navigation(
    catalog: Mapping[str, Any],
    manifests: Sequence[Mapping[str, Any]],
    references: Mapping[str, Mapping[str, Any]],
) -> str:
    del catalog
    lines = [
        "# External Course Packs",
        "",
        "<!-- Generated by scripts/validate_external_courses.py. Do not edit manually. -->",
        "",
        "外部课程包是固定版本的兼容层，不是第三方内容镜像。安装与 Preview 不会改变 `state/CURRENT_TASK.md`；只有 assignment 升级为 `implementation-ready` 后，才能通过受校验的选择流程把一个 canonical problem group 设为唯一当前任务。当前 `inventory-audited` 项目 fail closed。官方作业的许可证与学术诚信政策继续生效；一次官方测试全绿不等于本仓库 mastery。",
        "",
    ]
    for manifest in manifests:
        policy = manifest["academic_integrity"]
        lines.extend(
            [
                f"## {_escape(manifest['title'])}",
                "",
                f"- Provider：{_escape(manifest['provider'])}；Offering：{_escape(manifest['offering'])}。",
                f"- 安装模式：`{_escape(manifest['source_mode'])}` → `{_escape(manifest['install_root'])}`。",
                f"- AI 边界：最高 `{_escape(policy['maximum_ai_help'])}`，禁止 AI 直接实现；[官方政策]({_escape(policy['policy_url'])})。",
                f"- 非隶属声明：{_escape(manifest['non_affiliation_notice'])}",
                "",
                "| Assignment | 上游固定版本 | License audit | Problems (code / exp / analysis) | Adapter | Tests | Task Card |",
                "|---|---|---|---:|---:|---:|---|",
            ]
        )
        for assignment in manifest["assignments"]:
            reference = references[assignment["reference_id"]]
            counts = {kind: 0 for kind in PROBLEM_KINDS}
            for problem in assignment["problems"]:
                counts[problem["kind"]] += 1
            task_relative = PurePosixPath(assignment["task_card"])
            navigation_parent = PurePosixPath(NAVIGATION_RELATIVE).parent
            task_link = os.path.relpath(task_relative, navigation_parent).replace(os.sep, "/")
            revision = reference["pinned_revision"]
            source_link = f"{reference['repository_url']}/commit/{revision}"
            license_text = (
                ", ".join(record["spdx"] for record in reference["licenses"])
                if reference["license_status"] == "verified"
                else "not found; no redistribution"
            )
            lines.append(
                "| "
                + " | ".join(
                    (
                        f"`{assignment['id']}` {_escape(assignment['title'])}",
                        f"[`{revision[:12]}`]({source_link})",
                        _escape(license_text),
                        f"{len(assignment['problems'])} ({counts['coding']} / {counts['experiment']} / {counts['analysis']})",
                        str(len(assignment["adapter_functions"])),
                        str(len(assignment["test_nodes"])),
                        f"[open]({task_link})",
                    )
                )
                + " |"
            )
        lines.extend(["", "### 上游版本说明", ""])
        for assignment in manifest["assignments"]:
            spoiler_text = (
                "；包含会泄露 " + ", ".join(f"`{item}`" for item in assignment["spoiler_for"])
                if assignment["spoiler_for"]
                else ""
            )
            lines.append(
                f"- `{assignment['id']}`：{_escape(assignment['upstream_offering_note'])}"
                f"{spoiler_text}。"
            )
        lines.extend(["", "### 全量 problem inventory", ""])
        for assignment in manifest["assignments"]:
            lines.extend([f"#### `{assignment['id']}`", ""])
            for kind in ("coding", "experiment", "analysis"):
                identifiers = [
                    f"`{problem['id']}`"
                    for problem in assignment["problems"]
                    if problem["kind"] == kind
                ]
                lines.append(f"- {kind}：{', '.join(identifiers) if identifiers else '无'}。")
            lines.append("")
        lines.extend(["### Problem-group 实施单元", ""])
        lines.extend(
            [
                "整份 assignment 是聚合 Gate；正式实施时每次只把一个下列 canonical task ID "
                "登记为私人 ledger 的唯一 `CURRENT_TASK`。安装 checkout 本身不会开始任务；"
                "`inventory-audited` 状态只能 Preview，不能登记。",
                "每个 canonical task 的 learner 状态只证明 companion runtime。全部 `portable-required` group 分别达到 `reviewed` / `retained_7d` / `mastered` 时，才分别形成 assignment 的 portable aggregate；official runtime 必须另存真实运行证据，不能由 `mastered` 推定。",
                "Prerequisite groups 是本 companion 为小步训练定义的顺序，不声称是 Stanford 官方课程规则；前置 group 至少 `reviewed` 才能解锁后继。",
                "",
                "| Canonical task ID | Role | Companion evidence runtime | Official runtime | Prerequisite groups | Priority |",
                "|---|---|---|---|---|---|",
            ]
        )
        for assignment in manifest["assignments"]:
            for group in assignment["problem_groups"]:
                canonical_id = f"{assignment['id']}-{group['id']}"
                lines.append(
                    "| "
                    + " | ".join(
                        (
                            f"`{_escape(canonical_id)}`",
                            _escape(group["completion_role"]),
                            f"`{_escape(group['runtime_tier'])}`",
                            f"`{_escape(group['official_runtime_tier'])}`",
                            (
                                ", ".join(
                                    f"`{_escape(assignment['id'])}-{_escape(item)}`"
                                    for item in group["prerequisite_group_ids"]
                                )
                                if group["prerequisite_group_ids"]
                                else "none"
                            ),
                            _escape(group["priority"]),
                        )
                    )
                    + " |"
                )
        lines.append("")
        lines.extend(["### 依赖边", ""])
        edges: list[str] = []
        assignments_by_id = {item["id"]: item for item in manifest["assignments"]}
        for assignment in manifest["assignments"]:
            for prerequisite in assignment["prerequisites"]:
                edges.append(
                    f"- `{prerequisite}` → `{assignment['id']}`：先完成 "
                    f"{_escape(assignments_by_id[prerequisite]['title'])} 的兼容验收。"
                )
        lines.extend(edges or ["- 无 assignment 依赖边。"])
        lines.append("")
    lines.extend(
        [
            "安装器只负责固定版本检出和身份验证，不自动运行第三方代码。许可证事实见 [`references/registry.json`](../../references/registry.json)，使用方法见[外部课程包说明](../../docs/EXTERNAL_COURSE_PACKS.md)。",
            "",
        ]
    )
    return "\n".join(lines)


def _navigation_destination(repo_root: Path) -> Path:
    root = repo_root.resolve()
    relative = PurePosixPath(NAVIGATION_RELATIVE)
    destination = root.joinpath(*relative.parts)
    parent = destination.parent
    if not parent.is_dir() or _is_link_or_reparse(parent):
        _fail("external course navigation parent must be a regular repository directory")
    if destination.exists() and (not destination.is_file() or _is_link_or_reparse(destination)):
        _fail("external course navigation destination must be a regular file")
    return destination


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-navigation",
        action="store_true",
        help="write the deterministic external-course navigation after validation",
    )
    parser.add_argument("--json", action="store_true", help="print machine-readable output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        catalog, manifests, expected = validate_external_courses(
            check_navigation=not args.write_navigation
        )
        if args.write_navigation:
            destination = _navigation_destination(REPO_ROOT)
            destination.write_text(expected, encoding="utf-8")
            validate_external_courses(check_navigation=True)
    except CurriculumValidationError as error:
        if args.json:
            print(json.dumps({"schema_version": 1, "ok": False, "error": str(error)}))
        else:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    assignment_count = sum(len(item["assignments"]) for item in manifests)
    problem_count = sum(
        len(assignment["problems"])
        for item in manifests
        for assignment in item["assignments"]
    )
    result = {
        "schema_version": 1,
        "ok": True,
        "pack_count": len(catalog["packs"]),
        "assignment_count": assignment_count,
        "problem_count": problem_count,
        "navigation": "updated" if args.write_navigation else "current",
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(
            "External-course validation passed: "
            f"{result['pack_count']} pack, {assignment_count} assignments, "
            f"{problem_count} audited problems."
        )
        print(f"Navigation: {result['navigation']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
