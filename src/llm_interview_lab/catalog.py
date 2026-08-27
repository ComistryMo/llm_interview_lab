"""Load and validate the LEAN-V2 fixed curriculum catalog."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator
import yaml

from .dag import DagError, topological_order


PROBLEM_ASSETS = frozenset({"task.md", "starter.py", "test_public.py", "hints.md"})


class CatalogError(RuntimeError):
    """Raised when fixed curriculum metadata or assets are invalid."""


@dataclass(frozen=True)
class Problem:
    """The fields needed by the first vertical training slice."""

    id: str
    title: str
    status: str
    prerequisites: tuple[str, ...]
    problem_dir: Path
    symbol: str
    runner_kind: str
    public_tests: Path
    oracle_kind: str
    raw: dict[str, Any]


@dataclass(frozen=True)
class Catalog:
    """Validated problems and their stable topological order."""

    problems: dict[str, Problem]
    order: tuple[str, ...]

    def get(self, problem_id: str) -> Problem:
        try:
            return self.problems[problem_id]
        except KeyError as error:
            raise CatalogError(f"unknown problem ID: {problem_id}") from error

    def unlocked(self, implemented: set[str]) -> tuple[Problem, ...]:
        return tuple(
            self.problems[problem_id]
            for problem_id in self.order
            if problem_id not in implemented
            and set(self.problems[problem_id].prerequisites).issubset(implemented)
        )


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CatalogError(f"{label} cannot be read") from error
    if not isinstance(value, dict):
        raise CatalogError(f"{label} must be an object")
    return value


def _load_yaml_object(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise CatalogError(f"catalog shard cannot be read: {path.name}") from error
    if not isinstance(value, dict):
        raise CatalogError(f"catalog shard must contain an object: {path.name}")
    return value


def _safe_repository_path(repo_root: Path, value: str, label: str) -> Path:
    pure = PurePosixPath(value)
    if (
        pure.is_absolute()
        or not pure.parts
        or any(part in {"", ".", ".."} for part in pure.parts)
        or "\\" in value
    ):
        raise CatalogError(f"unsafe repository-relative path for {label}")
    resolved = repo_root.joinpath(*pure.parts).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as error:
        raise CatalogError(f"path escapes repository for {label}") from error
    return resolved


def _validate_shard(data: dict[str, Any], schema: dict[str, Any], name: str) -> None:
    errors = sorted(
        Draft202012Validator(schema).iter_errors(data),
        key=lambda item: list(item.path),
    )
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "<root>"
        raise CatalogError(f"invalid catalog shard {name} at {location}: {errors[0].message}")


def _build_problem(repo_root: Path, item: dict[str, Any]) -> Problem:
    problem_dir = _safe_repository_path(
        repo_root,
        item["assets"]["problem_dir"],
        f"{item['id']} problem_dir",
    )
    public_tests = problem_dir / item["assessment"]["runner"]["public_tests"]
    return Problem(
        id=item["id"],
        title=item["title"],
        status=item["status"],
        prerequisites=tuple(item["prerequisites"]),
        problem_dir=problem_dir,
        symbol=item["interface"]["symbol"],
        runner_kind=item["assessment"]["runner"]["kind"],
        public_tests=public_tests,
        oracle_kind=item["assessment"]["oracle"]["kind"],
        raw=item,
    )


def _validate_assets(repo_root: Path, problems: dict[str, Problem]) -> None:
    ready_directories: set[Path] = set()
    for problem in problems.values():
        if problem.status == "planned":
            if problem.problem_dir.exists():
                raise CatalogError(f"planned problem must not have assets: {problem.id}")
            continue
        if not problem.problem_dir.is_dir():
            raise CatalogError(f"problem assets are missing: {problem.id}")
        actual = {
            path.name
            for path in problem.problem_dir.iterdir()
            if path.name != "__pycache__" and path.suffix != ".pyc"
        }
        if actual != PROBLEM_ASSETS:
            missing = sorted(PROBLEM_ASSETS.difference(actual))
            extra = sorted(actual.difference(PROBLEM_ASSETS))
            raise CatalogError(
                f"problem assets mismatch for {problem.id}; missing={missing}, extra={extra}"
            )
        if not problem.public_tests.is_file():
            raise CatalogError(f"public test file is missing: {problem.id}")
        ready_directories.add(problem.problem_dir.resolve())

    problems_root = repo_root / "curriculum" / "problems"
    if problems_root.exists():
        unknown = sorted(
            path.name
            for path in problems_root.iterdir()
            if path.is_dir() and path.resolve() not in ready_directories
        )
        if unknown:
            raise CatalogError(f"problem directories not registered as ready: {', '.join(unknown)}")


def load_catalog(repo_root: Path) -> Catalog:
    """Load every LEAN-V2 YAML shard and validate one deterministic graph."""

    schema = _load_json_object(
        repo_root / "curriculum" / "schema" / "catalog.schema.json",
        "catalog schema",
    )
    shard_root = repo_root / "curriculum" / "catalog"
    shard_paths = sorted(shard_root.glob("*.yaml"))
    if not shard_paths:
        raise CatalogError("catalog has no YAML shards")

    problems: dict[str, Problem] = {}
    legacy_ids: set[str] = set()
    for shard_path in shard_paths:
        data = _load_yaml_object(shard_path)
        _validate_shard(data, schema, shard_path.name)
        for item in data["problems"]:
            problem_id = item["id"]
            if problem_id in problems:
                raise CatalogError(f"duplicate problem ID: {problem_id}")
            for legacy_id in item.get("legacy_ids", []):
                if legacy_id in legacy_ids:
                    raise CatalogError(f"duplicate legacy problem ID: {legacy_id}")
                legacy_ids.add(legacy_id)
            problems[problem_id] = _build_problem(repo_root, item)

    try:
        order = topological_order(
            {
                problem_id: problem.prerequisites
                for problem_id, problem in problems.items()
            }
        )
    except DagError as error:
        raise CatalogError(str(error)) from error
    _validate_assets(repo_root, problems)
    return Catalog(problems=problems, order=order)
