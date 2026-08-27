from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from llm_interview_lab.catalog import load_catalog
from llm_interview_lab.roles import (
    BLUEPRINT_SENIORITY_LEVELS,
    INTERVIEW_ITEM_ASSETS,
    INTERVIEW_ITEM_KINDS,
    load_role_catalog,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
ROLE_IDS = {
    "ai_product_manager",
    "applied_ai_engineer",
    "ai_agent_engineer",
    "ai_algorithm_research_engineer",
    "post_training_engineer",
    "ai_infra_engineer",
    "ai_inference_systems_engineer",
    "ai_evaluation_data_safety_engineer",
}


@pytest.fixture(scope="module")
def role_catalog():
    curriculum = load_catalog(REPO_ROOT)
    return load_role_catalog(REPO_ROOT, curriculum=curriculum)


def test_skill_ontology_is_canonical_and_broad(role_catalog) -> None:
    assert len(role_catalog.skills) >= 60
    assert len({skill.domain for skill in role_catalog.skills.values()}) >= 12
    assert all(skill.id.startswith("skill.") for skill in role_catalog.skills.values())
    assert all(set(skill.levels) == {"0", "1", "2", "3", "4"} for skill in role_catalog.skills.values())
    assert all(skill.evidence for skill in role_catalog.skills.values())


def test_eight_public_roles_have_valid_targets(role_catalog) -> None:
    assert set(role_catalog.roles) == ROLE_IDS
    for role in role_catalog.roles.values():
        assert role.seniority == ("intern", "new_grad", "mid", "senior")
        assert len(role.skill_weights) >= 6
        for target in role.skill_weights.values():
            assert 0 < target.weight <= 1
            assert set(target.target_level) == {"intern", "new_grad", "mid", "senior"}
            assert all(0 <= value <= 4 for value in target.target_level.values())


def test_role_aliases_resolve_without_copying_profiles(role_catalog) -> None:
    assert role_catalog.resolve_role("LLM Product Manager").id == "ai_product_manager"
    assert role_catalog.resolve_role("AI Application Engineer").id == "applied_ai_engineer"
    assert role_catalog.resolve_role("ML Systems Engineer").id == "ai_infra_engineer"
    assert role_catalog.resolve_role("AI Quality Engineer").id == "ai_evaluation_data_safety_engineer"


def test_blueprints_cover_every_role_and_supported_seniority(role_catalog) -> None:
    assert len(role_catalog.blueprints) == len(ROLE_IDS) * len(BLUEPRINT_SENIORITY_LEVELS)
    for role in role_catalog.roles.values():
        for seniority in BLUEPRINT_SENIORITY_LEVELS:
            blueprint = role_catalog.blueprint_for(role.id, seniority)
            assert blueprint.role == role.id
            assert blueprint.seniority == seniority
            assert sum(round_.duration for round_ in blueprint.rounds) == blueprint.duration_minutes
            assert sum(round_.weight for round_ in blueprint.rounds) == pytest.approx(1.0)


def test_fixed_non_coding_items_have_complete_assets_and_rubrics(role_catalog) -> None:
    assert len(role_catalog.items) >= 24
    for item in role_catalog.items.values():
        assert item.kind in INTERVIEW_ITEM_KINDS - {"coding"}
        assert item.validation == "maintainer_reviewed"
        assert {path.name for path in item.asset_dir.iterdir()} == INTERVIEW_ITEM_ASSETS
        rubric = yaml.safe_load(item.rubric_path.read_text(encoding="utf-8"))
        assert sum(value["weight"] for value in rubric["dimensions"].values()) == pytest.approx(1.0)
        assert rubric["fatal_issues"]


def test_every_non_coding_blueprint_round_has_a_fixed_item(role_catalog) -> None:
    for blueprint in role_catalog.blueprints.values():
        for round_ in blueprint.rounds:
            if round_.type == "coding":
                continue
            eligible = role_catalog.eligible_items(
                blueprint.role,
                blueprint.seniority,
                round_.type,
                round_.skills,
            )
            assert len(eligible) >= round_.item_count, (blueprint.id, round_.type)


def test_legacy_problem_kind_is_backward_compatible() -> None:
    catalog = load_catalog(REPO_ROOT)
    assert catalog.get("FND-001").kind == "coding"
    assert catalog.get("FND-001").canonical_skills == ()
    assert len(catalog.order) == len(catalog.problems)  # the existing DAG remains acyclic
