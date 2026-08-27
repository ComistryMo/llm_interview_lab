"""Load the fixed curriculum graph from its single YAML source."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
import yaml

from .dag import DagError, topological_order

PROBLEM_ASSETS = frozenset({"task.md", "starter.py", "test_public.py", "hints.md"})
RETENTION_ASSETS = frozenset({"starter.py", "test_public.py"})


class CatalogError(RuntimeError):
    """Raised when fixed curriculum metadata or assets are invalid."""


@dataclass(frozen=True)
class Problem:
    id: str
    title: str
    status: str
    prerequisites: tuple[str, ...]
    problem_dir: Path | None
    symbol: str | None
    runner_kind: str | None
    public_tests: Path | None
    oracle_kind: str | None
    raw: dict[str, Any]
    time_limit_ms: int = 5000
    output_limit_kb: int = 256

    @property
    def ready(self) -> bool:
        return self.status in {"ready", "stable"}

    def retention_variant(self, repo_root: Path, stage: str) -> tuple[Path, Path, str] | None:
        value = self.raw["retention"].get(stage)
        if not isinstance(value, dict) or value.get("oracle_validated") is not True:
            return None
        root = _repository_path(repo_root, value["assets"]["root"], f"{self.id} {stage} retention")
        return root / value["assets"]["starter"], root / value["assets"]["public_tests"], value["interface"]["symbol"]


@dataclass(frozen=True)
class Track:
    id: str
    title: str
    description: str


@dataclass(frozen=True)
class Quest:
    id: str
    title: str
    problem_ids: tuple[str, ...]
    description: str


@dataclass(frozen=True)
class Capstone:
    id: str
    title: str
    tracks: tuple[str, ...]
    prerequisites: tuple[str, ...]
    description: str


@dataclass(frozen=True)
class Catalog:
    problems: dict[str, Problem]
    order: tuple[str, ...]
    tracks: dict[str, Track]
    quests: dict[str, Quest]
    capstones: dict[str, Capstone]

    def get(self, problem_id: str) -> Problem:
        try:
            return self.problems[problem_id]
        except KeyError as error:
            raise CatalogError(f"unknown problem ID: {problem_id}") from error

    def unlocked(self, mastered: set[str], track_ids: set[str] | None = None) -> tuple[Problem, ...]:
        return tuple(
            self.problems[problem_id]
            for problem_id in self.order
            if self.problems[problem_id].ready
            and problem_id not in mastered
            and set(self.problems[problem_id].prerequisites).issubset(mastered)
            and (not track_ids or track_ids.intersection(self.problems[problem_id].raw["tracks"]))
        )


def _json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CatalogError(f"{label} cannot be read") from error
    if not isinstance(value, dict):
        raise CatalogError(f"{label} must be an object")
    return value


def _yaml_object(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise CatalogError(f"catalog shard cannot be read: {path.name}") from error
    if not isinstance(value, dict):
        raise CatalogError(f"catalog shard must contain an object: {path.name}")
    return value


def _repository_path(repo_root: Path, value: str, label: str) -> Path:
    pure = PurePosixPath(value)
    if pure.is_absolute() or not pure.parts or "\\" in value or any(part in {"", ".", ".."} for part in pure.parts):
        raise CatalogError(f"unsafe repository-relative path for {label}")
    resolved = repo_root.joinpath(*pure.parts).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as error:
        raise CatalogError(f"path escapes repository for {label}") from error
    return resolved


def _validate_shard(data: dict[str, Any], schema: dict[str, Any], name: str) -> None:
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(data), key=lambda item: list(item.path))
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "<root>"
        raise CatalogError(f"invalid catalog shard {name} at {location}: {errors[0].message}")


def _problem(repo_root: Path, item: dict[str, Any]) -> Problem:
    if item["status"] == "planned":
        return Problem(item["id"], item["title"], "planned", tuple(item["prerequisites"]), None, None, None, None, None, item)
    problem_dir = _repository_path(repo_root, item["assets"]["problem_dir"], f"{item['id']} problem_dir")
    constraints = item["constraints"]
    return Problem(
        item["id"], item["title"], item["status"], tuple(item["prerequisites"]), problem_dir,
        item["interface"]["symbol"], item["assessment"]["runner"]["kind"],
        problem_dir / item["assessment"]["runner"]["public_tests"], item["assessment"]["oracle"]["kind"], item,
        constraints["time_limit_ms"], constraints["output_limit_kb"],
    )


def _put(target: dict[str, Any], item: Any, kind: str) -> None:
    if item.id in target:
        raise CatalogError(f"duplicate {kind} ID: {item.id}")
    target[item.id] = item


def _validate_assets(repo_root: Path, problems: dict[str, Problem]) -> None:
    ready_dirs: set[Path] = set()
    for problem in problems.values():
        if not problem.ready:
            continue
        assert problem.problem_dir is not None and problem.public_tests is not None
        if not problem.problem_dir.is_dir():
            raise CatalogError(f"problem assets are missing: {problem.id}")
        actual = {p.name for p in problem.problem_dir.iterdir() if p.name != "__pycache__" and p.suffix != ".pyc"}
        if actual != PROBLEM_ASSETS:
            raise CatalogError(f"problem assets mismatch for {problem.id}; missing={sorted(PROBLEM_ASSETS - actual)}, extra={sorted(actual - PROBLEM_ASSETS)}")
        if not problem.public_tests.is_file():
            raise CatalogError(f"public test file is missing: {problem.id}")
        for stage in ("d2", "d7"):
            value = problem.raw["retention"][stage]
            if not isinstance(value, dict):
                continue
            root = _repository_path(repo_root, value["assets"]["root"], f"{problem.id} {stage} retention")
            if root.parts[-2:] != (problem.id, stage):
                raise CatalogError(f"retention assets do not match problem and stage: {problem.id}/{stage}")
            if not root.is_dir():
                raise CatalogError(f"retention assets are missing: {problem.id}/{stage}")
            actual = {p.name for p in root.iterdir() if p.name != "__pycache__" and p.suffix != ".pyc"}
            if actual != RETENTION_ASSETS:
                raise CatalogError(f"retention assets mismatch for {problem.id}/{stage}")
        ready_dirs.add(problem.problem_dir.resolve())
    problems_root = repo_root / "curriculum/problems"
    if problems_root.exists():
        unknown = sorted(path.name for path in problems_root.iterdir() if path.is_dir() and path.resolve() not in ready_dirs)
        if unknown:
            raise CatalogError(f"problem directories not registered as ready: {', '.join(unknown)}")


def load_catalog(repo_root: Path) -> Catalog:
    schema = _json_object(repo_root / "curriculum/schema/catalog.schema.json", "catalog schema")
    paths = sorted((repo_root / "curriculum/catalog").glob("*.yaml"))
    if not paths:
        raise CatalogError("catalog has no YAML shards")
    problems: dict[str, Problem] = {}
    tracks: dict[str, Track] = {}
    quests: dict[str, Quest] = {}
    capstones: dict[str, Capstone] = {}
    legacy_ids: set[str] = set()
    for path in paths:
        data = _yaml_object(path)
        _validate_shard(data, schema, path.name)
        for item in data.get("tracks", []):
            _put(tracks, Track(item["id"], item["title"], item["description"]), "track")
        for item in data.get("quests", []):
            _put(quests, Quest(item["id"], item["title"], tuple(item["problem_ids"]), item["description"]), "quest")
        for item in data.get("capstones", []):
            _put(capstones, Capstone(item["id"], item["title"], tuple(item["tracks"]), tuple(item["prerequisites"]), item["description"]), "capstone")
        for item in data["problems"]:
            problem = _problem(repo_root, item)
            _put(problems, problem, "problem")
            for legacy_id in item.get("legacy_ids", []):
                if legacy_id in legacy_ids:
                    raise CatalogError(f"duplicate legacy problem ID: {legacy_id}")
                legacy_ids.add(legacy_id)
    if not tracks:
        raise CatalogError("catalog must define tracks")
    known_tracks = set(tracks)
    for problem in problems.values():
        unknown = set(problem.raw["tracks"]) - known_tracks
        if unknown:
            raise CatalogError(f"unknown track on {problem.id}: {', '.join(sorted(unknown))}")
    try:
        order = topological_order({problem_id: problem.prerequisites for problem_id, problem in problems.items()})
    except DagError as error:
        raise CatalogError(str(error)) from error
    for quest in quests.values():
        unknown = set(quest.problem_ids) - set(problems)
        if unknown:
            raise CatalogError(f"unknown quest problem on {quest.id}: {', '.join(sorted(unknown))}")
    for capstone in capstones.values():
        if set(capstone.prerequisites) - set(problems) or set(capstone.tracks) - known_tracks:
            raise CatalogError(f"invalid capstone references: {capstone.id}")
    _validate_assets(repo_root, problems)
    return Catalog(problems, order, tracks, quests, capstones)
