from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

import llm_interview_lab.catalog as catalog_module
from llm_interview_lab.catalog import CatalogError, PROBLEM_ASSETS, load_catalog
from llm_interview_lab.dag import DagError, topological_order


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]


def test_catalog_contains_public_tracks_and_first_ready_problem() -> None:
    catalog = load_catalog(REPO_ROOT)

    assert "FND-001" in catalog.order
    assert {"ai_foundation", "llm_algorithm", "vlm_algorithm", "post_training", "agent", "systems"}.issubset(catalog.tracks)
    problem = catalog.get("FND-001")
    assert problem.raw["legacy_ids"] == ["00A-1"]
    assert problem.runner_kind == "pytest"
    assert problem.oracle_kind == "fixture_expected"
    assert problem.symbol == "count_wrong_predictions"


def test_ready_problem_has_exactly_four_public_assets() -> None:
    problem = load_catalog(REPO_ROOT).get("FND-001")

    assert {path.name for path in problem.problem_dir.iterdir()} == PROBLEM_ASSETS
    assert not (problem.problem_dir / "solution.py").exists()


def test_catalog_rejects_a_link_or_reparse_problem_asset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protected = (
        REPO_ROOT / "curriculum/problems/FND-001-wrong-prediction-count/hints.md"
    ).resolve()
    original = catalog_module._is_obvious_link
    monkeypatch.setattr(
        catalog_module,
        "_is_obvious_link",
        lambda path: path.resolve() == protected or original(path),
    )

    with pytest.raises(CatalogError, match="regular, unlinked"):
        load_catalog(REPO_ROOT)


@pytest.mark.parametrize(
    "relative",
    (
        "curriculum/schema/catalog.schema.json",
        "curriculum/catalog/foundation.yaml",
    ),
)
def test_catalog_rejects_a_link_or_reparse_metadata_source(
    monkeypatch: pytest.MonkeyPatch,
    relative: str,
) -> None:
    protected = (REPO_ROOT / relative).resolve()
    original = catalog_module._is_obvious_link
    monkeypatch.setattr(
        catalog_module,
        "_is_obvious_link",
        lambda path: path.resolve() == protected or original(path),
    )

    with pytest.raises(CatalogError, match="linked path is not allowed"):
        load_catalog(REPO_ROOT)


def test_catalog_does_not_follow_a_shard_symlink_into_a_profile(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    shutil.copytree(REPO_ROOT / "curriculum", root / "curriculum")
    private = root / "workspace/profiles/learner-one/cache/private-catalog.yaml"
    private.parent.mkdir(parents=True)
    private.write_text("problems: []\n", encoding="utf-8")
    shard = root / "curriculum/catalog/foundation.yaml"
    shard.unlink()
    try:
        shard.symlink_to(private)
    except OSError as error:
        pytest.skip(f"symlink creation is unavailable on this platform: {error}")

    with pytest.raises(CatalogError, match="linked path is not allowed"):
        load_catalog(root)


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
        schema["$defs"]["ready_problem"]["allOf"][1]["properties"]["assessment"]["properties"]
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


def test_transformer_quest_exposes_linear_softmax_mask_and_attention_without_false_hard_edges() -> None:
    catalog = load_catalog(REPO_ROOT)
    sequence = catalog.quests["transformer_forward"].problem_ids

    assert sequence.index("NNL-001") < sequence.index("LOSS-007") < sequence.index("ATT-002")
    assert sequence.index("TNS-010") < sequence.index("ATT-002")
    assert "NNL-001" not in catalog.get("LOSS-007").prerequisites
    assert set(catalog.get("ATT-002").prerequisites) == {"LOSS-007", "TNS-010"}
