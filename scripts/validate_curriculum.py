"""Validate curriculum metadata, reference provenance, and generated navigation.

The validator is intentionally offline. External repositories are recorded at
audited revisions, but CI never fetches them and never imports their content.
"""

from __future__ import annotations

import argparse
import ast
from datetime import date
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_RELATIVE = "curriculum/catalog.json"
REFERENCE_RELATIVE = "references/registry.json"
NAVIGATION_RELATIVE = "curriculum/NAVIGATION.md"

TOP_LEVEL_KEYS = {"schema_version", "catalog_id", "stages", "job_routes", "tasks"}
STAGE_KEYS = {"id", "title", "order", "gate"}
ROUTE_KEYS = {"id", "title", "description", "order"}
TASK_KEYS = {
    "id",
    "title",
    "stage_id",
    "order",
    "task_file",
    "prerequisites",
    "gate_requirements",
    "priority",
    "difficulty",
    "estimated_minutes",
    "learning_objectives",
    "interview_value",
    "public_maturity",
    "public_portfolio_candidate",
    "runtime_profile",
    "gpu_acceptance_policy",
    "job_routes",
    "reference_exposure",
    "reference_ids",
    "math_prerequisites",
    "visible_test_count",
    "test_nodes",
}
ESTIMATE_KEYS = {"minimum", "maximum"}
PREREQUISITE_KEYS = {"task_id", "minimum_status"}

REFERENCE_TOP_LEVEL_KEYS = {"schema_version", "references"}
REFERENCE_KEYS = {
    "id",
    "kind",
    "title",
    "repository_url",
    "pinned_revision",
    "audited_on",
    "license_status",
    "license_audit_url",
    "license_audit_method",
    "licenses",
    "influence",
    "excluded_material",
    "usage",
}
LICENSE_KEYS = {"scope", "spdx", "evidence_url"}

PRIORITIES = {"P0", "P1", "P2"}
DIFFICULTIES = {"introductory", "intermediate", "advanced"}
PUBLIC_MATURITIES = {"draft", "review-ready", "validated"}
RUNTIME_PROFILES = {"python-cpu", "pytorch-cpu", "pytorch-cuda"}
GPU_POLICIES = {
    "not-applicable",
    "cpu-required-gpu-optional",
    "cuda-required",
}
RUNTIME_GPU_COMBINATIONS = {
    ("python-cpu", "not-applicable"),
    ("pytorch-cpu", "cpu-required-gpu-optional"),
    ("pytorch-cuda", "cuda-required"),
}
REFERENCE_EXPOSURES = {"none", "preview-safe", "post-review-only"}
LEARNER_STATUSES = {
    "implemented",
    "reviewed",
    "retained_48h",
    "retained_7d",
    "mastered",
}
REFERENCE_USAGES = {
    "design-reference-only",
    "review-material",
    "adapted-content",
    "external-course-source",
}
LICENSE_STATUSES = {"verified", "not-found"}

ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*$")
TEST_NAME_PATTERN = re.compile(r"^test_[A-Za-z0-9_]+$")
REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SPDX_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+-]*$")
SAFE_REPOSITORY_PATH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

VALIDATED_CARD_HEADINGS = (
    "## 背景",
    "## 目标函数",
    "## 要求",
    "## 学习点",
    "## 定向测试",
    "## 验收问答",
    "## 间隔复测",
)

MATURITY_LABELS = {
    "draft": "draft",
    "review-ready": "review-ready",
    "validated": "validated",
}
RUNTIME_LABELS = {
    "python-cpu": "Python / CPU",
    "pytorch-cpu": "PyTorch / CPU 必跑",
    "pytorch-cuda": "PyTorch / CUDA 必跑",
}
EXPOSURE_LABELS = {
    "none": "无外部材料",
    "preview-safe": "Preview 可看",
    "post-review-only": "review 后可看",
}


class CurriculumValidationError(ValueError):
    """Raised when public curriculum metadata violates its contract."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CurriculumValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    """Load one UTF-8 JSON object while rejecting duplicate keys."""

    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise CurriculumValidationError(f"cannot read {path.name} as UTF-8") from error
    try:
        value = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as error:
        raise CurriculumValidationError(f"invalid JSON in {path.name}: {error.msg}") from error
    if not isinstance(value, dict):
        raise CurriculumValidationError(f"{path.name} must contain one JSON object")
    return value


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], context: str) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        raise CurriculumValidationError(
            f"{context} fields mismatch; missing={missing}, unknown={unknown}"
        )


def _require_object(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise CurriculumValidationError(f"{context} must be an object")
    return value


def _require_list(value: Any, context: str, *, allow_empty: bool = False) -> list[Any]:
    if not isinstance(value, list) or (not value and not allow_empty):
        suffix = "" if allow_empty else " and must not be empty"
        raise CurriculumValidationError(f"{context} must be a list{suffix}")
    return value


def _require_string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CurriculumValidationError(
            f"{context} must be a non-empty string without outer whitespace"
        )
    if "\n" in value or "\r" in value:
        raise CurriculumValidationError(f"{context} must be a single line")
    return value


def _require_integer(value: Any, context: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise CurriculumValidationError(
            f"{context} must be an integer >= {minimum}"
        )
    return value


def _require_string_list(
    value: Any,
    context: str,
    *,
    allow_empty: bool = False,
) -> list[str]:
    items = _require_list(value, context, allow_empty=allow_empty)
    strings = [_require_string(item, f"{context}[{index}]") for index, item in enumerate(items)]
    if len(strings) != len(set(strings)):
        raise CurriculumValidationError(f"{context} contains duplicate values")
    return strings


def _require_enum(value: Any, allowed: set[str], context: str) -> str:
    string = _require_string(value, context)
    if string not in allowed:
        raise CurriculumValidationError(
            f"{context} must be one of {sorted(allowed)}; found {string!r}"
        )
    return string


def _is_link_or_reparse(path: Path) -> bool:
    file_stat = os.lstat(path)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    attributes = getattr(file_stat, "st_file_attributes", 0)
    return stat.S_ISLNK(file_stat.st_mode) or bool(attributes & reparse_flag)


def _has_exact_case(repo_root: Path, relative: PurePosixPath) -> bool:
    current = repo_root.resolve()
    for part in relative.parts:
        try:
            names = {child.name for child in current.iterdir()}
        except OSError:
            return False
        if part not in names:
            return False
        current = current / part
    return True


def _resolve_regular_file(
    repo_root: Path,
    relative_value: Any,
    context: str,
    *,
    prefix: str,
    suffix: str,
) -> tuple[str, Path]:
    relative_text = _require_string(relative_value, context)
    if "\\" in relative_text or not SAFE_REPOSITORY_PATH.fullmatch(relative_text):
        raise CurriculumValidationError(
            f"{context} must use safe POSIX repository path characters"
        )
    relative = PurePosixPath(relative_text)
    if (
        relative.as_posix() != relative_text
        or relative.is_absolute()
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise CurriculumValidationError(f"{context} is not a safe repository-relative path")
    if not relative_text.startswith(prefix) or not relative_text.endswith(suffix):
        raise CurriculumValidationError(
            f"{context} must start with {prefix!r} and end with {suffix!r}"
        )
    path = repo_root.joinpath(*relative.parts)
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(repo_root.resolve())
    except (OSError, ValueError) as error:
        raise CurriculumValidationError(f"{context} does not resolve inside the repository") from error
    current = repo_root
    for part in relative.parts:
        current = current / part
        if _is_link_or_reparse(current):
            raise CurriculumValidationError(f"{context} traverses a link or reparse path")
    if not path.is_file():
        raise CurriculumValidationError(f"{context} must reference a regular file")
    if not _has_exact_case(repo_root, relative):
        raise CurriculumValidationError(f"{context} has a path case mismatch")
    return relative_text, path


def _test_functions(path: Path) -> set[str]:
    try:
        module = ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
    except (OSError, UnicodeError, SyntaxError) as error:
        raise CurriculumValidationError(f"cannot parse test module {path.name}") from error
    return {
        node.name
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    }


def _validate_test_node(repo_root: Path, value: Any, task_id: str) -> tuple[str, Path]:
    node = _require_string(value, f"task {task_id} test node")
    if node.count("::") != 1:
        raise CurriculumValidationError(f"task {task_id} test node must select one function")
    path_value, function_name = node.split("::", 1)
    if not TEST_NAME_PATTERN.fullmatch(function_name):
        raise CurriculumValidationError(f"task {task_id} has invalid test function name")
    _, path = _resolve_regular_file(
        repo_root,
        path_value,
        f"task {task_id} test path",
        prefix="tests/",
        suffix=".py",
    )
    if function_name not in _test_functions(path):
        raise CurriculumValidationError(
            f"task {task_id} test function does not exist: {function_name}"
        )
    return node, path


def _validate_url(value: Any, context: str) -> str:
    url = _require_string(value, context)
    try:
        parsed = urlparse(url)
        # Accessing these parsed properties performs additional validation (for
        # example, rejecting non-numeric or out-of-range ports).
        parsed.port
        username = parsed.username
        password = parsed.password
    except ValueError as error:
        raise CurriculumValidationError(f"{context} must be a valid public HTTPS URL") from error
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or username
        or password
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise CurriculumValidationError(f"{context} must be a public HTTPS URL without credentials")
    return url


def _require_repository_url(
    candidate_url: str,
    repository_url: str,
    context: str,
) -> None:
    candidate = urlparse(candidate_url)
    repository = urlparse(repository_url)
    repository_path = repository.path.rstrip("/")
    if repository_path.endswith(".git"):
        repository_path = repository_path[:-4]
    if (
        candidate.netloc.casefold() != repository.netloc.casefold()
        or not repository_path
        or not candidate.path.startswith(repository_path + "/")
    ):
        raise CurriculumValidationError(
            f"{context} must belong to the registered repository"
        )


def validate_reference_registry(registry: Mapping[str, Any]) -> set[str]:
    """Validate reference provenance and return all registered IDs."""

    _require_exact_keys(registry, REFERENCE_TOP_LEVEL_KEYS, "reference registry")
    if registry["schema_version"] != 2:
        raise CurriculumValidationError("reference registry schema_version must be 2")
    references = _require_list(registry["references"], "references", allow_empty=True)
    seen_ids: set[str] = set()
    for index, raw_reference in enumerate(references):
        reference = _require_object(raw_reference, f"references[{index}]")
        _require_exact_keys(reference, REFERENCE_KEYS, f"references[{index}]")
        reference_id = _require_string(reference["id"], f"references[{index}].id")
        if not ID_PATTERN.fullmatch(reference_id) or reference_id in seen_ids:
            raise CurriculumValidationError(f"invalid or duplicate reference id: {reference_id}")
        seen_ids.add(reference_id)
        if reference["kind"] != "external-repository":
            raise CurriculumValidationError(f"reference {reference_id} kind is unsupported")
        _require_string(reference["title"], f"reference {reference_id} title")
        repository_url = _validate_url(
            reference["repository_url"],
            f"reference {reference_id} repository_url",
        )
        revision = _require_string(
            reference["pinned_revision"],
            f"reference {reference_id} pinned_revision",
        )
        if not REVISION_PATTERN.fullmatch(revision):
            raise CurriculumValidationError(
                f"reference {reference_id} must pin a full lowercase commit SHA"
            )
        audited_on = _require_string(reference["audited_on"], f"reference {reference_id} audited_on")
        try:
            if not ISO_DATE_PATTERN.fullmatch(audited_on):
                raise ValueError
            date.fromisoformat(audited_on)
        except ValueError as error:
            raise CurriculumValidationError(
                f"reference {reference_id} audited_on must be YYYY-MM-DD"
            ) from error
        license_status = _require_enum(
            reference["license_status"],
            LICENSE_STATUSES,
            f"reference {reference_id} license_status",
        )
        license_audit_url = _validate_url(
            reference["license_audit_url"],
            f"reference {reference_id} license_audit_url",
        )
        _require_repository_url(
            license_audit_url,
            repository_url,
            f"reference {reference_id} license_audit_url",
        )
        _require_string(
            reference["license_audit_method"],
            f"reference {reference_id} license_audit_method",
        )
        license_audit_path = urlparse(license_audit_url).path
        if (
            f"/blob/{revision}/" not in license_audit_path
            and f"/tree/{revision}" not in license_audit_path
            and not license_audit_path.endswith(f"/commit/{revision}")
        ):
            raise CurriculumValidationError(
                f"reference {reference_id} license audit must use its pinned revision"
            )
        licenses = _require_list(
            reference["licenses"],
            f"reference {reference_id} licenses",
            allow_empty=license_status == "not-found",
        )
        if license_status == "not-found" and licenses:
            raise CurriculumValidationError(
                f"reference {reference_id} cannot declare licenses when license_status is not-found"
            )
        license_scopes: set[str] = set()
        for license_index, raw_license in enumerate(licenses):
            license_record = _require_object(
                raw_license,
                f"reference {reference_id} licenses[{license_index}]",
            )
            _require_exact_keys(
                license_record,
                LICENSE_KEYS,
                f"reference {reference_id} licenses[{license_index}]",
            )
            scope = _require_string(
                license_record["scope"],
                f"reference {reference_id} license scope",
            )
            if scope in license_scopes:
                raise CurriculumValidationError(
                    f"reference {reference_id} has duplicate license scope: {scope}"
                )
            license_scopes.add(scope)
            spdx = _require_string(
                license_record["spdx"],
                f"reference {reference_id} SPDX identifier",
            )
            if not SPDX_PATTERN.fullmatch(spdx):
                raise CurriculumValidationError(
                    f"reference {reference_id} has invalid SPDX identifier"
                )
            evidence_url = _validate_url(
                license_record["evidence_url"],
                f"reference {reference_id} license evidence_url",
            )
            _require_repository_url(
                evidence_url,
                repository_url,
                f"reference {reference_id} license evidence_url",
            )
            evidence_path = urlparse(evidence_url).path
            if (
                f"/blob/{revision}/" not in evidence_path
                and not evidence_path.endswith(f"/commit/{revision}")
            ):
                raise CurriculumValidationError(
                    f"reference {reference_id} license evidence must use its pinned revision"
                )
        _require_string_list(reference["influence"], f"reference {reference_id} influence")
        _require_string_list(
            reference["excluded_material"],
            f"reference {reference_id} excluded_material",
        )
        usage = _require_enum(
            reference["usage"],
            REFERENCE_USAGES,
            f"reference {reference_id} usage",
        )
        if license_status == "not-found" and usage == "adapted-content":
            raise CurriculumValidationError(
                f"reference {reference_id} without a verified license cannot be adapted-content"
            )
    return seen_ids


def _validate_dependency_graph(tasks_by_id: Mapping[str, Mapping[str, Any]]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            raise CurriculumValidationError(f"task dependency cycle includes {task_id}")
        if task_id in visited:
            return
        visiting.add(task_id)
        for prerequisite in tasks_by_id[task_id]["prerequisites"]:
            visit(prerequisite["task_id"])
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in tasks_by_id:
        visit(task_id)


def validate_catalog(
    catalog: Mapping[str, Any],
    *,
    repo_root: Path,
    registered_reference_ids: set[str],
) -> None:
    """Validate catalog structure, local paths, tests, and dependency semantics."""

    _require_exact_keys(catalog, TOP_LEVEL_KEYS, "curriculum catalog")
    if catalog["schema_version"] != 1:
        raise CurriculumValidationError("curriculum catalog schema_version must be 1")
    _require_string(catalog["catalog_id"], "catalog_id")

    stages = _require_list(catalog["stages"], "stages")
    stage_ids: set[str] = set()
    stage_orders: set[int] = set()
    stage_order_by_id: dict[str, int] = {}
    for index, raw_stage in enumerate(stages):
        stage = _require_object(raw_stage, f"stages[{index}]")
        _require_exact_keys(stage, STAGE_KEYS, f"stages[{index}]")
        stage_id = _require_string(stage["id"], f"stages[{index}].id")
        order = _require_integer(stage["order"], f"stage {stage_id} order")
        if not ID_PATTERN.fullmatch(stage_id) or stage_id in stage_ids:
            raise CurriculumValidationError(f"invalid or duplicate stage id: {stage_id}")
        if order in stage_orders:
            raise CurriculumValidationError(f"duplicate stage order: {order}")
        stage_ids.add(stage_id)
        stage_orders.add(order)
        stage_order_by_id[stage_id] = order
        _require_string(stage["title"], f"stage {stage_id} title")
        _require_string(stage["gate"], f"stage {stage_id} gate")

    routes = _require_list(catalog["job_routes"], "job_routes")
    route_ids: set[str] = set()
    route_orders: set[int] = set()
    for index, raw_route in enumerate(routes):
        route = _require_object(raw_route, f"job_routes[{index}]")
        _require_exact_keys(route, ROUTE_KEYS, f"job_routes[{index}]")
        route_id = _require_string(route["id"], f"job_routes[{index}].id")
        order = _require_integer(route["order"], f"job route {route_id} order")
        if not ID_PATTERN.fullmatch(route_id) or route_id in route_ids:
            raise CurriculumValidationError(f"invalid or duplicate job route id: {route_id}")
        if order in route_orders:
            raise CurriculumValidationError(f"duplicate job route order: {order}")
        route_ids.add(route_id)
        route_orders.add(order)
        _require_string(route["title"], f"job route {route_id} title")
        _require_string(route["description"], f"job route {route_id} description")

    tasks = _require_list(catalog["tasks"], "tasks")
    tasks_by_id: dict[str, Mapping[str, Any]] = {}
    task_orders: set[tuple[str, int]] = set()
    all_test_nodes: set[str] = set()
    task_files: set[str] = set()
    test_source_by_path: dict[Path, str] = {}

    for index, raw_task in enumerate(tasks):
        task = _require_object(raw_task, f"tasks[{index}]")
        _require_exact_keys(task, TASK_KEYS, f"tasks[{index}]")
        task_id = _require_string(task["id"], f"tasks[{index}].id")
        if not ID_PATTERN.fullmatch(task_id) or task_id in tasks_by_id:
            raise CurriculumValidationError(f"invalid or duplicate task id: {task_id}")
        tasks_by_id[task_id] = task
        _require_string(task["title"], f"task {task_id} title")
        stage_id = _require_string(task["stage_id"], f"task {task_id} stage_id")
        if stage_id not in stage_ids:
            raise CurriculumValidationError(f"task {task_id} references unknown stage {stage_id}")
        order = _require_integer(task["order"], f"task {task_id} order", minimum=1)
        if (stage_id, order) in task_orders:
            raise CurriculumValidationError(f"duplicate task order {order} in {stage_id}")
        task_orders.add((stage_id, order))

        task_file, task_path = _resolve_regular_file(
            repo_root,
            task["task_file"],
            f"task {task_id} task_file",
            prefix="curriculum/",
            suffix=".md",
        )
        if task_file in task_files:
            raise CurriculumValidationError(f"multiple tasks share Task Card {task_file}")
        task_files.add(task_file)
        card_text = task_path.read_text(encoding="utf-8")
        if f"# Task {task_id}" not in card_text:
            raise CurriculumValidationError(f"Task Card heading does not identify {task_id}")

        prerequisites = _require_list(
            task["prerequisites"],
            f"task {task_id} prerequisites",
            allow_empty=True,
        )
        prerequisite_ids: set[str] = set()
        for prerequisite_index, raw_prerequisite in enumerate(prerequisites):
            prerequisite = _require_object(
                raw_prerequisite,
                f"task {task_id} prerequisites[{prerequisite_index}]",
            )
            _require_exact_keys(
                prerequisite,
                PREREQUISITE_KEYS,
                f"task {task_id} prerequisites[{prerequisite_index}]",
            )
            prerequisite_id = _require_string(
                prerequisite["task_id"],
                f"task {task_id} prerequisite task_id",
            )
            if prerequisite_id == task_id or prerequisite_id in prerequisite_ids:
                raise CurriculumValidationError(
                    f"task {task_id} has a self or duplicate prerequisite"
                )
            prerequisite_ids.add(prerequisite_id)
            _require_enum(
                prerequisite["minimum_status"],
                LEARNER_STATUSES,
                f"task {task_id} prerequisite status",
            )

        _require_string_list(task["gate_requirements"], f"task {task_id} gate_requirements")
        _require_enum(task["priority"], PRIORITIES, f"task {task_id} priority")
        _require_enum(task["difficulty"], DIFFICULTIES, f"task {task_id} difficulty")
        estimate = _require_object(task["estimated_minutes"], f"task {task_id} estimated_minutes")
        _require_exact_keys(estimate, ESTIMATE_KEYS, f"task {task_id} estimated_minutes")
        minimum = _require_integer(
            estimate["minimum"],
            f"task {task_id} minimum estimate",
            minimum=1,
        )
        maximum = _require_integer(
            estimate["maximum"],
            f"task {task_id} maximum estimate",
            minimum=1,
        )
        if minimum > maximum:
            raise CurriculumValidationError(f"task {task_id} estimate minimum exceeds maximum")
        _require_string_list(task["learning_objectives"], f"task {task_id} learning_objectives")
        _require_string(task["interview_value"], f"task {task_id} interview_value")
        maturity = _require_enum(
            task["public_maturity"],
            PUBLIC_MATURITIES,
            f"task {task_id} public_maturity",
        )
        if type(task["public_portfolio_candidate"]) is not bool:
            raise CurriculumValidationError(
                f"task {task_id} public_portfolio_candidate must be boolean"
            )
        runtime = _require_enum(
            task["runtime_profile"],
            RUNTIME_PROFILES,
            f"task {task_id} runtime_profile",
        )
        gpu_policy = _require_enum(
            task["gpu_acceptance_policy"],
            GPU_POLICIES,
            f"task {task_id} gpu_acceptance_policy",
        )
        if (runtime, gpu_policy) not in RUNTIME_GPU_COMBINATIONS:
            raise CurriculumValidationError(
                f"task {task_id} has inconsistent runtime and GPU policy"
            )
        task_routes = _require_string_list(task["job_routes"], f"task {task_id} job_routes")
        unknown_routes = sorted(set(task_routes) - route_ids)
        if unknown_routes:
            raise CurriculumValidationError(
                f"task {task_id} references unknown job routes: {unknown_routes}"
            )
        exposure = _require_enum(
            task["reference_exposure"],
            REFERENCE_EXPOSURES,
            f"task {task_id} reference_exposure",
        )
        reference_ids = _require_string_list(
            task["reference_ids"],
            f"task {task_id} reference_ids",
            allow_empty=True,
        )
        unknown_references = sorted(set(reference_ids) - registered_reference_ids)
        if unknown_references:
            raise CurriculumValidationError(
                f"task {task_id} references unknown sources: {unknown_references}"
            )
        if (exposure == "none") != (not reference_ids):
            raise CurriculumValidationError(
                f"task {task_id} reference_exposure and reference_ids disagree"
            )
        _require_string_list(task["math_prerequisites"], f"task {task_id} math_prerequisites")

        visible_count = _require_integer(
            task["visible_test_count"],
            f"task {task_id} visible_test_count",
            minimum=1,
        )
        test_nodes = _require_list(task["test_nodes"], f"task {task_id} test_nodes")
        if visible_count != len(test_nodes):
            raise CurriculumValidationError(
                f"task {task_id} visible_test_count does not match test_nodes"
            )
        task_test_paths: set[Path] = set()
        for test_node in test_nodes:
            node, test_path = _validate_test_node(repo_root, test_node, task_id)
            if node in all_test_nodes:
                raise CurriculumValidationError(f"test node belongs to multiple tasks: {node}")
            all_test_nodes.add(node)
            task_test_paths.add(test_path)
            if test_path not in test_source_by_path:
                test_source_by_path[test_path] = test_path.read_text(encoding="utf-8")
        test_source = "\n".join(test_source_by_path[path] for path in task_test_paths)
        if runtime.startswith("pytorch-") and "pytest.mark.requires_torch" not in test_source:
            raise CurriculumValidationError(f"task {task_id} PyTorch tests lack requires_torch marker")
        if gpu_policy == "cuda-required" and "pytest.mark.requires_cuda" not in test_source:
            raise CurriculumValidationError(f"task {task_id} CUDA tests lack requires_cuda marker")
        if maturity == "validated":
            if "pytest.mark.locked" in test_source:
                raise CurriculumValidationError(f"validated task {task_id} still uses locked tests")
            missing_headings = [heading for heading in VALIDATED_CARD_HEADINGS if heading not in card_text]
            if missing_headings:
                raise CurriculumValidationError(
                    f"validated Task Card {task_id} lacks headings: {missing_headings}"
                )

    for task_id, task in tasks_by_id.items():
        stage_id = task["stage_id"]
        for prerequisite in task["prerequisites"]:
            prerequisite_id = prerequisite["task_id"]
            if prerequisite_id not in tasks_by_id:
                raise CurriculumValidationError(
                    f"task {task_id} references unknown prerequisite {prerequisite_id}"
                )
            prerequisite_task = tasks_by_id[prerequisite_id]
            prerequisite_position = (
                stage_order_by_id[prerequisite_task["stage_id"]],
                prerequisite_task["order"],
            )
            task_position = (stage_order_by_id[stage_id], task["order"])
            if prerequisite_position >= task_position:
                raise CurriculumValidationError(
                    f"task {task_id} prerequisite {prerequisite_id} is not earlier in the route"
                )
    _validate_dependency_graph(tasks_by_id)


def _escape_table_cell(value: str) -> str:
    """Escape generated Markdown table content, including LaTeX backslashes."""

    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _task_link(task: Mapping[str, Any]) -> str:
    relative = PurePosixPath(task["task_file"]).relative_to("curriculum")
    return f"[{_escape_table_cell(task['id'])}]({relative.as_posix()})"


def render_navigation(catalog: Mapping[str, Any]) -> str:
    """Render the public dependency and job-route indexes deterministically."""

    stages = sorted(catalog["stages"], key=lambda stage: stage["order"])
    routes = sorted(catalog["job_routes"], key=lambda route: route["order"])
    stage_order = {stage["id"]: stage["order"] for stage in stages}
    tasks = sorted(
        catalog["tasks"],
        key=lambda task: (stage_order[task["stage_id"]], task["order"], task["id"]),
    )
    tasks_by_id = {task["id"]: task for task in tasks}

    lines = [
        "# Curriculum Navigation",
        "",
        "<!-- Generated by scripts/validate_curriculum.py from curriculum/catalog.json. Do not edit manually. -->",
        "",
        "本页同时提供依赖轴和岗位轴。它只展示已经存在的 Task Card；长期规划中的能力不会以空任务占位。",
        "",
        "> `public_maturity` 描述公共任务包质量，不描述任何学习者的 `implemented`、`reviewed` 或 `mastered` 状态。当前唯一实现任务仍以 [`state/CURRENT_TASK.md`](../state/CURRENT_TASK.md) 为准。",
        "",
        "## 公开成熟度",
        "",
        "| 值 | 含义 | 能否据此解锁个人任务 |",
        "|---|---|---|",
        "| `draft` | Task Card 或验收包仍需补齐 | 否 |",
        "| `review-ready` | 材料完整，等待独立课程审查或试用 | 否 |",
        "| `validated` | 公共任务契约和可见测试已通过维护者验证 | 仍不能；必须查看私人 ledger |",
        "",
        "## 依赖轴",
        "",
    ]

    for stage in stages:
        lines.extend(
            [
                f"### {_escape_table_cell(stage['title'])}（{_escape_table_cell(stage['gate'])}）",
                "",
                "| Task | 名称 | 公共成熟度 | 前置 Gate | Runtime | 可见测试 | 数学前置 |",
                "|---|---|---|---|---|---:|---|",
            ]
        )
        stage_tasks = [task for task in tasks if task["stage_id"] == stage["id"]]
        for task in stage_tasks:
            prerequisites = task["prerequisites"]
            prerequisite_text = (
                "无"
                if not prerequisites
                else "<br>".join(
                    f"{item['task_id']} ≥ {item['minimum_status']}" for item in prerequisites
                )
            )
            math_text = "<br>".join(task["math_prerequisites"])
            lines.append(
                "| "
                + " | ".join(
                    (
                        _task_link(task),
                        _escape_table_cell(task["title"]),
                        f"`{MATURITY_LABELS[task['public_maturity']]}`",
                        _escape_table_cell(prerequisite_text),
                        _escape_table_cell(RUNTIME_LABELS[task["runtime_profile"]]),
                        str(task["visible_test_count"]),
                        _escape_table_cell(math_text),
                    )
                )
                + " |"
            )
        lines.append("")

    lines.extend(
        [
            "## 岗位轴",
            "",
            "岗位轴用于发现关联任务，不改变依赖 Gate，也不允许同时开启多个 Implementation Lane Task。",
            "",
            "| 路线 | 定位 | 当前已登记 Task |",
            "|---|---|---|",
        ]
    )
    for route in routes:
        route_tasks = [task for task in tasks if route["id"] in task["job_routes"]]
        task_text = (
            "尚无已登记任务"
            if not route_tasks
            else "、".join(_task_link(task) for task in route_tasks)
        )
        lines.append(
            "| "
            + " | ".join(
                (
                    _escape_table_cell(route["title"]),
                    _escape_table_cell(route["description"]),
                    task_text,
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## 运行与参考边界",
            "",
            "| Task | 最低运行环境 | GPU 验收 | 外部参考暴露 | 预计独立实现 |",
            "|---|---|---|---|---:|",
        ]
    )
    for task in tasks:
        estimate = task["estimated_minutes"]
        lines.append(
            "| "
            + " | ".join(
                (
                    _task_link(task),
                    _escape_table_cell(RUNTIME_LABELS[task["runtime_profile"]]),
                    f"`{task['gpu_acceptance_policy']}`",
                    _escape_table_cell(EXPOSURE_LABELS[task["reference_exposure"]]),
                    f"{estimate['minimum']}–{estimate['maximum']} 分钟",
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## 依赖边",
            "",
        ]
    )
    edges: list[str] = []
    for task in tasks:
        for prerequisite in task["prerequisites"]:
            source = tasks_by_id[prerequisite["task_id"]]
            edges.append(
                f"- {_task_link(source)} → {_task_link(task)}："
                f"前者至少达到 `{prerequisite['minimum_status']}`。"
            )
    lines.extend(edges or ["- 当前 catalog 没有任务依赖边。"])
    lines.extend(
        [
            "",
            "外部材料的固定版本、许可证和暴露规则见[参考登记](../references/README.md)与[来源治理](../docs/REFERENCE_POLICY.md)。",
            "",
        ]
    )
    return "\n".join(lines)


def validate_repository(
    *,
    repo_root: Path = REPO_ROOT,
    check_navigation: bool = True,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Validate both registries and optionally require navigation to match."""

    root = repo_root.resolve()
    _, catalog_path = _resolve_regular_file(
        root,
        CATALOG_RELATIVE,
        "curriculum catalog",
        prefix="curriculum/",
        suffix=".json",
    )
    _, registry_path = _resolve_regular_file(
        root,
        REFERENCE_RELATIVE,
        "reference registry",
        prefix="references/",
        suffix=".json",
    )
    catalog = load_json(catalog_path)
    registry = load_json(registry_path)
    reference_ids = validate_reference_registry(registry)
    validate_catalog(catalog, repo_root=root, registered_reference_ids=reference_ids)
    expected_navigation = render_navigation(catalog)
    if check_navigation:
        _, navigation_path = _resolve_regular_file(
            root,
            NAVIGATION_RELATIVE,
            "generated curriculum navigation",
            prefix="curriculum/",
            suffix=".md",
        )
        try:
            actual_navigation = navigation_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise CurriculumValidationError("generated curriculum navigation is missing or invalid") from error
        if actual_navigation != expected_navigation:
            raise CurriculumValidationError(
                "curriculum/NAVIGATION.md is stale; run "
                "python scripts/validate_curriculum.py --write-navigation"
            )
    return catalog, registry, expected_navigation


def _safe_navigation_destination(repo_root: Path) -> Path:
    """Return the generated navigation path without following links."""

    root = repo_root.resolve()
    relative = PurePosixPath(NAVIGATION_RELATIVE)
    parent = root
    for part in relative.parts[:-1]:
        parent = parent / part
        if not parent.is_dir() or _is_link_or_reparse(parent):
            raise CurriculumValidationError(
                "generated navigation parent must be a regular repository directory"
            )
    destination = root.joinpath(*relative.parts)
    try:
        os.lstat(destination)
    except FileNotFoundError:
        pass
    except OSError as error:
        raise CurriculumValidationError(
            "generated navigation destination cannot be inspected"
        ) from error
    else:
        if not destination.is_file() or _is_link_or_reparse(destination):
            raise CurriculumValidationError(
                "generated navigation destination must be a regular file"
            )
        if not _has_exact_case(root, relative):
            raise CurriculumValidationError("generated navigation path has a case mismatch")
    return destination


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-navigation",
        action="store_true",
        help="rewrite the generated navigation after validating source metadata",
    )
    parser.add_argument("--json", action="store_true", help="print machine-readable output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        catalog, registry, expected = validate_repository(
            check_navigation=not args.write_navigation
        )
        if args.write_navigation:
            destination = _safe_navigation_destination(REPO_ROOT)
            try:
                destination.write_text(expected, encoding="utf-8")
            except OSError as error:
                raise CurriculumValidationError(
                    "could not write generated curriculum navigation"
                ) from error
            validate_repository(check_navigation=True)
    except CurriculumValidationError as error:
        if args.json:
            print(json.dumps({"schema_version": 1, "ok": False, "error": str(error)}))
        else:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    result = {
        "schema_version": 1,
        "ok": True,
        "task_count": len(catalog["tasks"]),
        "stage_count": len(catalog["stages"]),
        "job_route_count": len(catalog["job_routes"]),
        "reference_count": len(registry["references"]),
        "navigation": "updated" if args.write_navigation else "current",
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(
            "Curriculum validation passed: "
            f"{result['task_count']} tasks, {result['stage_count']} stage, "
            f"{result['job_route_count']} job routes, "
            f"{result['reference_count']} reference."
        )
        print(f"Navigation: {result['navigation']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
