from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil

import pytest

from scripts.validate_external_courses import (
    CATALOG_RELATIVE,
    NAVIGATION_RELATIVE,
    CurriculumValidationError,
    load_json,
    main,
    validate_external_courses,
)


pytestmark = [pytest.mark.infrastructure]

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_RELATIVE = "curriculum/external/stanford_cs336/manifest.json"


def _manifest() -> dict:
    return load_json(REPO_ROOT / MANIFEST_RELATIVE)


def _temporary_repository(tmp_path: Path, manifest: dict) -> Path:
    root = tmp_path / "repository"
    shutil.copytree(REPO_ROOT / "curriculum" / "external", root / "curriculum" / "external")
    shutil.copytree(REPO_ROOT / "references", root / "references")
    (root / MANIFEST_RELATIVE).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return root


def _validate_mutation(tmp_path: Path, manifest: dict) -> None:
    root = _temporary_repository(tmp_path, manifest)
    validate_external_courses(repo_root=root, check_navigation=False)


def test_stanford_pack_has_complete_audited_inventory_and_current_navigation() -> None:
    catalog, manifests, expected_navigation = validate_external_courses(
        repo_root=REPO_ROOT,
        check_navigation=True,
    )

    assignments = [
        assignment
        for manifest in manifests
        for assignment in manifest["assignments"]
    ]
    assert len(catalog["packs"]) == 1
    assert [assignment["id"] for assignment in assignments] == [
        "EXT-CS336-A1",
        "EXT-CS336-A2",
        "EXT-CS336-A3",
        "EXT-CS336-A4",
        "EXT-CS336-A5",
    ]
    expected_counts = {
        "EXT-CS336-A1": (38, 21, 48),
        "EXT-CS336-A2": (27, 8, 8),
        "EXT-CS336-A3": (2, 0, 7),
        "EXT-CS336-A4": (13, 11, 21),
        "EXT-CS336-A5": (44, 12, 21),
    }
    assert {
        assignment["id"]: (
            len(assignment["problems"]),
            len(assignment["adapter_functions"]),
            len(assignment["test_nodes"]),
        )
        for assignment in assignments
    } == expected_counts
    assert sum(len(assignment["problems"]) for assignment in assignments) == 124
    assert sum(len(assignment["adapter_functions"]) for assignment in assignments) == 52
    assert sum(len(assignment["test_nodes"]) for assignment in assignments) == 105
    assert all(manifest["vendored_material"] == [] for manifest in manifests)
    assert all(
        manifest["academic_integrity"]["maximum_ai_help"] in {"H0", "H1", "H2"}
        and manifest["academic_integrity"]["direct_implementation_allowed"] is False
        for manifest in manifests
    )
    assert {assignment["id"]: assignment["spoiler_for"] for assignment in assignments} == {
        "EXT-CS336-A1": [],
        "EXT-CS336-A2": ["EXT-CS336-A1"],
        "EXT-CS336-A3": [],
        "EXT-CS336-A4": ["EXT-CS336-A1"],
        "EXT-CS336-A5": [],
    }
    actual_navigation = (REPO_ROOT / NAVIGATION_RELATIVE).read_text(encoding="utf-8")
    assert actual_navigation == expected_navigation
    assert "stanford_cs336/TASK_A1.md" in actual_navigation
    assert "stanford_cs336\\TASK_A1.md" not in actual_navigation
    for assignment in assignments:
        card = (REPO_ROOT / assignment["task_card"]).read_text(encoding="utf-8")
        problem_count, adapter_count, test_count = expected_counts[assignment["id"]]
        assert f"{problem_count} 个 Problem" in card
        assert f"{adapter_count} 个 adapter" in card
        assert f"{test_count} 个" in card


def test_manifest_rejects_problem_count_drift_and_ungrouped_problem(tmp_path: Path) -> None:
    count_drift = copy.deepcopy(_manifest())
    count_drift["assignments"][0]["problems"].pop()
    with pytest.raises(CurriculumValidationError, match="expected 38 problems"):
        _validate_mutation(tmp_path / "count", count_drift)

    ungrouped = copy.deepcopy(_manifest())
    removed = ungrouped["assignments"][0]["problem_groups"][0]["problem_ids"].pop()
    with pytest.raises(CurriculumValidationError, match=f"ungrouped problems.*{removed}"):
        _validate_mutation(tmp_path / "ungrouped", ungrouped)

    adapter_drift = copy.deepcopy(_manifest())
    adapter_drift["assignments"][0]["adapter_functions"].pop()
    with pytest.raises(CurriculumValidationError, match="expected 21 adapters"):
        _validate_mutation(tmp_path / "adapter", adapter_drift)

    test_drift = copy.deepcopy(_manifest())
    test_drift["assignments"][0]["test_nodes"].pop()
    with pytest.raises(CurriculumValidationError, match="expected 48 test nodes"):
        _validate_mutation(tmp_path / "tests", test_drift)


def test_manifest_rejects_duplicate_group_coverage_and_unknown_evidence(
    tmp_path: Path,
) -> None:
    duplicated = copy.deepcopy(_manifest())
    duplicated_id = duplicated["assignments"][0]["problem_groups"][0]["problem_ids"][0]
    duplicated["assignments"][0]["problem_groups"][1]["problem_ids"].append(duplicated_id)
    with pytest.raises(CurriculumValidationError, match="multiple groups"):
        _validate_mutation(tmp_path / "duplicate", duplicated)

    unknown_evidence = copy.deepcopy(_manifest())
    unknown_evidence["assignments"][0]["problem_groups"][0]["evidence"] = [
        "test-node:tests/test_missing.py::test_missing"
    ]
    with pytest.raises(CurriculumValidationError, match="unknown test node"):
        _validate_mutation(tmp_path / "evidence", unknown_evidence)


def test_manifest_rejects_invalid_problem_group_dependency_graph(tmp_path: Path) -> None:
    unknown = copy.deepcopy(_manifest())
    unknown["assignments"][0]["problem_groups"][0]["prerequisite_group_ids"] = [
        "missing-group"
    ]
    with pytest.raises(CurriculumValidationError, match="unknown group prerequisites"):
        _validate_mutation(tmp_path / "unknown-group", unknown)

    cyclic = copy.deepcopy(_manifest())
    cyclic["assignments"][0]["problem_groups"][0]["prerequisite_group_ids"] = [
        "resource-accounting"
    ]
    cyclic["assignments"][0]["problem_groups"][3]["prerequisite_group_ids"] = [
        "unicode-foundations"
    ]
    with pytest.raises(CurriculumValidationError, match="dependency cycle"):
        _validate_mutation(tmp_path / "cycle", cyclic)

    nonportable = copy.deepcopy(_manifest())
    nonportable["assignments"][0]["problem_groups"][1]["prerequisite_group_ids"] = [
        "generation-and-ablations"
    ]
    with pytest.raises(CurriculumValidationError, match="cannot depend on non-portable"):
        _validate_mutation(tmp_path / "nonportable", nonportable)

    hidden_required = copy.deepcopy(_manifest())
    hidden_required["assignments"][0]["problem_groups"][1][
        "prerequisite_group_ids"
    ] = ["unicode-foundations"]
    with pytest.raises(CurriculumValidationError, match="make elective groups mandatory"):
        _validate_mutation(tmp_path / "hidden-required", hidden_required)


def test_manifest_rejects_vendoring_ai_escalation_and_unsafe_install_root(
    tmp_path: Path,
) -> None:
    vendored = copy.deepcopy(_manifest())
    vendored["vendored_material"] = ["upstream/tests/test_solution.py"]
    with pytest.raises(CurriculumValidationError, match="cannot vendor"):
        _validate_mutation(tmp_path / "vendor", vendored)

    ai_escalation = copy.deepcopy(_manifest())
    ai_escalation["academic_integrity"]["maximum_ai_help"] = "H3"
    with pytest.raises(CurriculumValidationError, match="maximum_ai_help"):
        _validate_mutation(tmp_path / "ai", ai_escalation)

    unsafe_root = copy.deepcopy(_manifest())
    unsafe_root["install_root"] = ".external/../src"
    with pytest.raises(CurriculumValidationError, match="safe path below .external"):
        _validate_mutation(tmp_path / "path", unsafe_root)

    invalid_port = copy.deepcopy(_manifest())
    invalid_port["official_course_url"] = "https://cs336.stanford.edu:not-a-port/"
    with pytest.raises(CurriculumValidationError, match="valid public HTTPS URL"):
        _validate_mutation(tmp_path / "url", invalid_port)

    query_token = copy.deepcopy(_manifest())
    query_token["official_course_url"] = (
        "https://cs336.stanford.edu/?access_token=secret"
    )
    with pytest.raises(CurriculumValidationError, match="without credentials"):
        _validate_mutation(tmp_path / "query", query_token)


def test_manifest_rejects_runtime_evidence_spoiler_and_checkout_conflicts(
    tmp_path: Path,
) -> None:
    wrong_runtime = copy.deepcopy(_manifest())
    flash_group = wrong_runtime["assignments"][1]["problem_groups"][1]
    flash_group["evidence"][0] = "test-command:all"
    with pytest.raises(CurriculumValidationError, match="different runtime tier"):
        _validate_mutation(tmp_path / "runtime", wrong_runtime)

    future_spoiler = copy.deepcopy(_manifest())
    future_spoiler["assignments"][0]["spoiler_for"] = ["EXT-CS336-A2"]
    with pytest.raises(CurriculumValidationError, match="spoilers must name earlier"):
        _validate_mutation(tmp_path / "spoiler", future_spoiler)

    duplicate_checkout = copy.deepcopy(_manifest())
    duplicate_checkout["assignments"][1]["checkout_directory"] = (
        duplicate_checkout["assignments"][0]["checkout_directory"]
    )
    with pytest.raises(CurriculumValidationError, match="duplicate external checkout target"):
        _validate_mutation(tmp_path / "checkout", duplicate_checkout)


def test_cli_reports_offline_machine_readable_counts(capsys) -> None:
    exit_code = main(["--json"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert '"assignment_count": 5' in output
    assert '"problem_count": 124' in output
