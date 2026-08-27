from __future__ import annotations

import json
from pathlib import Path

import pytest

from llm_interview_lab.catalog import PROBLEM_ASSETS, load_catalog
from llm_interview_lab.dag import DagError, topological_order


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]


def test_catalog_contains_only_the_first_vertical_slice_problem() -> None:
    catalog = load_catalog(REPO_ROOT)

    assert catalog.order == ("FND-001",)
    problem = catalog.get("FND-001")
    assert problem.raw["legacy_ids"] == ["00A-1"]
    assert problem.runner_kind == "pytest"
    assert problem.oracle_kind == "fixture_expected"
    assert problem.symbol == "count_wrong_predictions"


def test_ready_problem_has_exactly_four_public_assets() -> None:
    problem = load_catalog(REPO_ROOT).get("FND-001")

    assert {path.name for path in problem.problem_dir.iterdir()} == PROBLEM_ASSETS
    assert not (problem.problem_dir / "solution.py").exists()


def test_runner_and_oracle_are_separate_catalog_objects() -> None:
    assessment = load_catalog(REPO_ROOT).get("FND-001").raw["assessment"]

    assert assessment["runner"] == {
        "kind": "pytest",
        "public_tests": "test_public.py",
    }
    assert assessment["oracle"]["kind"] == "fixture_expected"
    assert "public_tests" not in assessment["oracle"]


def test_schema_reserves_reviewed_oracle_kinds() -> None:
    schema = json.loads(
        (REPO_ROOT / "curriculum" / "schema" / "catalog.schema.json").read_text(
            encoding="utf-8"
        )
    )
    kinds = set(
        schema["$defs"]["problem"]["properties"]["assessment"]["properties"]
        ["oracle"]["properties"]["kind"]["enum"]
    )

    assert kinds == {
        "fixture_expected",
        "closed_form",
        "framework_reference",
        "brute_force",
        "cross_implementation",
        "property_only",
    }


def test_problem_tests_depend_only_on_injected_submission_fixture() -> None:
    problem = load_catalog(REPO_ROOT).get("FND-001")
    public_tests = problem.public_tests.read_text(encoding="utf-8")

    assert "import starter" not in public_tests
    assert "sys.path" not in public_tests
    assert "workspace/" not in public_tests.lower()
    assert "load_submission" not in public_tests
    assert "def test_" in public_tests
    assert "submission" in public_tests


def test_dag_order_is_stable() -> None:
    assert topological_order(
        {
            "FND-003": ["FND-001", "FND-002"],
            "FND-002": ["FND-001"],
            "FND-001": [],
        }
    ) == ("FND-001", "FND-002", "FND-003")


def test_dag_rejects_unknown_prerequisite_and_cycle() -> None:
    with pytest.raises(DagError, match="unknown prerequisite"):
        topological_order({"FND-001": ["FND-999"]})
    with pytest.raises(DagError, match="cycle"):
        topological_order({"FND-001": ["FND-002"], "FND-002": ["FND-001"]})
