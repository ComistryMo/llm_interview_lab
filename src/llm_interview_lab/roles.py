"""Canonical skills, role profiles, interview blueprints and fixed interview items."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator
import yaml

from .catalog import Catalog, load_catalog


INTERVIEW_ITEM_ASSETS = frozenset(
    {"task.md", "response_template.md", "rubric.yaml", "hints.md"}
)
SENIORITY_LEVELS = ("intern", "new_grad", "mid", "senior")
BLUEPRINT_SENIORITY_LEVELS = SENIORITY_LEVELS[:3]
INTERVIEW_ITEM_KINDS = frozenset(
    {
        "coding",
        "debugging",
        "product_case",
        "system_design",
        "evaluation_case",
        "project_deep_dive",
        "behavioral",
        "oral",
    }
)


class RoleCatalogError(RuntimeError):
    """Raised when public role or interview metadata is inconsistent."""


@dataclass(frozen=True)
class Skill:
    id: str
    title: str
    domain: str
    description: str
    levels: Mapping[str, str]
    evidence: tuple[str, ...]
    related_problems: tuple[str, ...]
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class RoleSkillTarget:
    weight: float
    target_level: Mapping[str, int]


@dataclass(frozen=True)
class RoleProfile:
    id: str
    title: str
    aliases: tuple[str, ...]
    summary: str
    seniority: tuple[str, ...]
    skill_weights: Mapping[str, RoleSkillTarget]
    required_tracks: tuple[str, ...]
    recommended_quests: tuple[str, ...]
    optional_quests: tuple[str, ...]
    interview_blueprints: Mapping[str, str]


@dataclass(frozen=True)
class InterviewRound:
    type: str
    duration: int
    weight: float
    skills: tuple[str, ...]
    item_count: int


@dataclass(frozen=True)
class InterviewBlueprint:
    id: str
    role: str
    seniority: str
    duration_minutes: int
    rounds: tuple[InterviewRound, ...]


@dataclass(frozen=True)
class InterviewItem:
    id: str
    title: str
    kind: str
    status: str
    roles: tuple[str, ...]
    seniority: tuple[str, ...]
    difficulty: int
    duration_minutes: int
    skills: tuple[str, ...]
    asset_dir: Path
    validation: str
    raw: Mapping[str, Any]

    @property
    def task_path(self) -> Path:
        return self.asset_dir / "task.md"

    @property
    def response_template_path(self) -> Path:
        return self.asset_dir / "response_template.md"

    @property
    def rubric_path(self) -> Path:
        return self.asset_dir / "rubric.yaml"

    @property
    def hints_path(self) -> Path:
        return self.asset_dir / "hints.md"


@dataclass(frozen=True)
class RoleCatalog:
    skills: Mapping[str, Skill]
    roles: Mapping[str, RoleProfile]
    blueprints: Mapping[str, InterviewBlueprint]
    items: Mapping[str, InterviewItem]
    aliases: Mapping[str, str]

    def resolve_role(self, role_or_alias: str) -> RoleProfile:
        key = role_or_alias.strip().casefold()
        role_id = self.aliases.get(key, role_or_alias)
        try:
            return self.roles[role_id]
        except KeyError as error:
            raise RoleCatalogError(f"unknown role or alias: {role_or_alias}") from error

    def blueprint_for(self, role_id: str, seniority: str) -> InterviewBlueprint:
        role = self.resolve_role(role_id)
        try:
            blueprint_id = role.interview_blueprints[seniority]
            return self.blueprints[blueprint_id]
        except KeyError as error:
            raise RoleCatalogError(
                f"role {role.id} has no interview blueprint for {seniority}"
            ) from error

    def eligible_items(
        self,
        role_id: str,
        seniority: str,
        round_type: str,
        skill_ids: tuple[str, ...] = (),
    ) -> tuple[InterviewItem, ...]:
        role = self.resolve_role(role_id)
        wanted = set(skill_ids)
        return tuple(
            item
            for item in self.items.values()
            if item.status == "ready"
            and role.id in item.roles
            and seniority in item.seniority
            and item.kind == round_type
            and (not wanted or wanted.intersection(item.skills))
        )


def _read_yaml(path: Path, label: str) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise RoleCatalogError(f"{label} cannot be read") from error
    if not isinstance(value, dict):
        raise RoleCatalogError(f"{label} must be a YAML object")
    return value


def _validate(value: Mapping[str, Any], schema: Mapping[str, Any], label: str) -> None:
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value), key=lambda error: list(error.path)
    )
    if errors:
        path = ".".join(str(part) for part in errors[0].path) or "<root>"
        raise RoleCatalogError(f"invalid {label} at {path}: {errors[0].message}")


def _schema_view(schema: Mapping[str, Any], definition: str) -> dict[str, Any]:
    """Keep local JSON-Schema references rooted at the complete schema document."""

    return {
        "$schema": schema.get("$schema", "https://json-schema.org/draft/2020-12/schema"),
        "$defs": schema["$defs"],
        "$ref": f"#/$defs/{definition}",
    }


def _unique(values: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for value in values:
        identifier = value["id"]
        if identifier in result:
            raise RoleCatalogError(f"duplicate {label} ID: {identifier}")
        result[identifier] = value
    return result


def _validate_rubric(path: Path, item_id: str) -> None:
    value = _read_yaml(path, f"rubric for {item_id}")
    dimensions = value.get("dimensions")
    if not isinstance(dimensions, dict) or not dimensions:
        raise RoleCatalogError(f"rubric has no dimensions: {item_id}")
    total = 0.0
    for name, dimension in dimensions.items():
        if not isinstance(name, str) or not isinstance(dimension, dict):
            raise RoleCatalogError(f"invalid rubric dimension: {item_id}")
        weight = dimension.get("weight")
        anchors = dimension.get("anchors")
        if not isinstance(weight, (int, float)) or isinstance(weight, bool) or weight <= 0:
            raise RoleCatalogError(f"invalid rubric weight: {item_id}/{name}")
        if not isinstance(anchors, dict) or set(anchors) != {1, 3, 5}:
            raise RoleCatalogError(f"rubric anchors must be 1, 3 and 5: {item_id}/{name}")
        if any(not isinstance(text, str) or not text.strip() for text in anchors.values()):
            raise RoleCatalogError(f"rubric anchors must be non-empty: {item_id}/{name}")
        total += float(weight)
    if abs(total - 1.0) > 1e-9:
        raise RoleCatalogError(f"rubric weights must sum to 1: {item_id}")
    fatal = value.get("fatal_issues")
    if not isinstance(fatal, list) or len(fatal) != len(set(fatal)):
        raise RoleCatalogError(f"rubric fatal_issues must be a unique list: {item_id}")


def _asset_dir(repo_root: Path, relative: str, item_id: str) -> Path:
    root = (repo_root / "curriculum" / "interviews" / "assets").resolve()
    candidate = (repo_root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise RoleCatalogError(f"interview item assets escape their public root: {item_id}") from error
    if not candidate.is_dir() or candidate.is_symlink():
        raise RoleCatalogError(f"interview item assets are missing: {item_id}")
    actual = {path.name for path in candidate.iterdir() if path.is_file()}
    if actual != INTERVIEW_ITEM_ASSETS:
        raise RoleCatalogError(
            f"interview item assets mismatch for {item_id}; "
            f"missing={sorted(INTERVIEW_ITEM_ASSETS - actual)}, "
            f"extra={sorted(actual - INTERVIEW_ITEM_ASSETS)}"
        )
    if any(path.is_symlink() for path in candidate.iterdir()):
        raise RoleCatalogError(f"interview item assets cannot be links: {item_id}")
    return candidate


def load_role_catalog(
    repo_root: Path,
    *,
    curriculum: Catalog | None = None,
) -> RoleCatalog:
    """Load and cross-validate the public role-aware interview model."""

    repo_root = repo_root.resolve()
    curriculum = curriculum or load_catalog(repo_root)
    schema = _read_yaml(
        repo_root / "curriculum/schema/role-interview.schema.yaml", "role interview schema"
    )
    skill_data = _read_yaml(repo_root / "curriculum/skills/ontology.yaml", "skill ontology")
    role_data = _read_yaml(repo_root / "curriculum/roles/profiles.yaml", "role profiles")
    interview_data = _read_yaml(
        repo_root / "curriculum/interviews/catalog.yaml", "interview catalog"
    )
    _validate(skill_data, _schema_view(schema, "skill_catalog"), "skill ontology")
    _validate(role_data, _schema_view(schema, "role_catalog"), "role profiles")
    _validate(
        interview_data,
        _schema_view(schema, "interview_catalog"),
        "interview catalog",
    )

    raw_skills = _unique(skill_data["skills"], "skill")
    raw_roles = _unique(role_data["roles"], "role")
    raw_blueprints = _unique(interview_data["blueprints"], "blueprint")
    raw_items = _unique(interview_data["items"], "interview item")

    known_problems = set(curriculum.problems)
    skills: dict[str, Skill] = {}
    skill_aliases: set[str] = set()
    for identifier, value in raw_skills.items():
        unknown = set(value["related_problems"]) - known_problems
        if unknown:
            raise RoleCatalogError(
                f"unknown related problem on {identifier}: {', '.join(sorted(unknown))}"
            )
        aliases = tuple(value.get("aliases", ()))
        for alias in aliases:
            folded = alias.casefold()
            if folded in skill_aliases:
                raise RoleCatalogError(f"duplicate skill alias: {alias}")
            skill_aliases.add(folded)
        skills[identifier] = Skill(
            identifier,
            value["title"],
            value["domain"],
            value["description"],
            value["levels"],
            tuple(value["evidence"]),
            tuple(value["related_problems"]),
            aliases,
        )

    for problem in curriculum.problems.values():
        unknown = set(problem.canonical_skills) - set(skills)
        if unknown:
            raise RoleCatalogError(
                f"unknown canonical skill on {problem.id}: {', '.join(sorted(unknown))}"
            )

    roles: dict[str, RoleProfile] = {}
    aliases: dict[str, str] = {}
    known_tracks = set(curriculum.tracks)
    known_quests = set(curriculum.quests)
    for identifier, value in raw_roles.items():
        unknown_skills = set(value["skill_weights"]) - set(skills)
        if unknown_skills:
            raise RoleCatalogError(
                f"unknown role skill on {identifier}: {', '.join(sorted(unknown_skills))}"
            )
        unknown_tracks = set(value["required_tracks"]) - known_tracks
        unknown_quests = (
            set(value["recommended_quests"]) | set(value["optional_quests"])
        ) - known_quests
        if unknown_tracks or unknown_quests:
            raise RoleCatalogError(f"invalid Track or Quest reference on role: {identifier}")
        targets = {
            skill_id: RoleSkillTarget(float(target["weight"]), target["target_level"])
            for skill_id, target in value["skill_weights"].items()
        }
        roles[identifier] = RoleProfile(
            identifier,
            value["title"],
            tuple(value["aliases"]),
            value["summary"],
            tuple(value["seniority"]),
            targets,
            tuple(value["required_tracks"]),
            tuple(value["recommended_quests"]),
            tuple(value["optional_quests"]),
            value["interview_blueprints"],
        )
        for name in (identifier, value["title"], *value["aliases"]):
            key = name.casefold()
            if key in aliases:
                raise RoleCatalogError(f"role alias collision: {name}")
            aliases[key] = identifier

    blueprints: dict[str, InterviewBlueprint] = {}
    for identifier, value in raw_blueprints.items():
        if value["role"] not in roles:
            raise RoleCatalogError(f"unknown blueprint role: {identifier}")
        rounds = tuple(
            InterviewRound(
                item["type"],
                item["duration"],
                float(item["weight"]),
                tuple(item["skills"]),
                item["item_count"],
            )
            for item in value["rounds"]
        )
        if sum(item.duration for item in rounds) != value["duration_minutes"]:
            raise RoleCatalogError(f"blueprint durations do not sum correctly: {identifier}")
        if abs(sum(item.weight for item in rounds) - 1.0) > 1e-9:
            raise RoleCatalogError(f"blueprint weights do not sum to 1: {identifier}")
        unknown_skills = {skill for item in rounds for skill in item.skills} - set(skills)
        if unknown_skills:
            raise RoleCatalogError(f"unknown blueprint skill: {identifier}")
        blueprints[identifier] = InterviewBlueprint(
            identifier,
            value["role"],
            value["seniority"],
            value["duration_minutes"],
            rounds,
        )

    for role in roles.values():
        for seniority in BLUEPRINT_SENIORITY_LEVELS:
            blueprint_id = role.interview_blueprints.get(seniority)
            if blueprint_id not in blueprints:
                raise RoleCatalogError(
                    f"role {role.id} has an invalid {seniority} blueprint reference"
                )
            blueprint = blueprints[blueprint_id]
            if blueprint.role != role.id or blueprint.seniority != seniority:
                raise RoleCatalogError(f"role blueprint identity mismatch: {blueprint_id}")

    items: dict[str, InterviewItem] = {}
    task_hashes: set[str] = set()
    for identifier, value in raw_items.items():
        unknown_roles = set(value["roles"]) - set(roles)
        unknown_skills = set(value["skills"]) - set(skills)
        if unknown_roles or unknown_skills:
            raise RoleCatalogError(f"invalid role or skill on interview item: {identifier}")
        assets = _asset_dir(repo_root, value["assets"]["item_dir"], identifier)
        _validate_rubric(assets / "rubric.yaml", identifier)
        task_digest = (assets / "task.md").read_text(encoding="utf-8").strip().casefold()
        if task_digest in task_hashes:
            raise RoleCatalogError(f"duplicate interview task content: {identifier}")
        task_hashes.add(task_digest)
        items[identifier] = InterviewItem(
            identifier,
            value["title"],
            value.get("kind", "coding"),
            value["status"],
            tuple(value["roles"]),
            tuple(value["seniority"]),
            value["difficulty"],
            value["duration_minutes"],
            tuple(value["skills"]),
            assets,
            value["validation"],
            value,
        )

    for blueprint in blueprints.values():
        for round_ in blueprint.rounds:
            if round_.type == "coding":
                continue
            eligible = [
                item
                for item in items.values()
                if blueprint.role in item.roles
                and blueprint.seniority in item.seniority
                and item.kind == round_.type
                and set(item.skills).intersection(round_.skills)
            ]
            if len(eligible) < round_.item_count:
                raise RoleCatalogError(
                    f"blueprint round has too few fixed items: {blueprint.id}/{round_.type}"
                )

    return RoleCatalog(skills, roles, blueprints, items, aliases)
