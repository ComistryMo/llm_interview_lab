from __future__ import annotations

import copy
from pathlib import Path

import pytest

from scripts.validate_curriculum import (
    CATALOG_RELATIVE,
    NAVIGATION_RELATIVE,
    REFERENCE_RELATIVE,
    CurriculumValidationError,
    _escape_table_cell,
    load_json,
    main,
    render_navigation,
    validate_catalog,
    validate_reference_registry,
    validate_repository,
)


pytestmark = [pytest.mark.infrastructure]

REPO_ROOT = Path(__file__).resolve().parents[2]


def _catalog() -> dict:
    return load_json(REPO_ROOT / CATALOG_RELATIVE)


def _registry() -> dict:
    return load_json(REPO_ROOT / REFERENCE_RELATIVE)


def _validate(catalog: dict) -> None:
    references = validate_reference_registry(_registry())
    validate_catalog(
        catalog,
        repo_root=REPO_ROOT,
        registered_reference_ids=references,
    )


def test_public_catalog_and_generated_navigation_are_current() -> None:
    catalog, registry, expected = validate_repository(repo_root=REPO_ROOT)

    assert len(catalog["tasks"]) == 4
    assert registry["schema_version"] == 2
    assert len(registry["references"]) == 6
    assert (REPO_ROOT / NAVIGATION_RELATIVE).read_text(encoding="utf-8") == expected
    assert "state/CURRENT_TASK.md" in expected
    assert "尚无已登记任务" in expected


def test_json_loader_rejects_duplicate_keys(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"schema_version": 1, "schema_version": 2}', encoding="utf-8")

    with pytest.raises(CurriculumValidationError, match="duplicate JSON key"):
        load_json(duplicate)


def test_catalog_rejects_unknown_fields_and_test_count_drift() -> None:
    unknown = copy.deepcopy(_catalog())
    unknown["tasks"][0]["answer"] = "should never exist"
    with pytest.raises(CurriculumValidationError, match="unknown=.*answer"):
        _validate(unknown)

    wrong_count = copy.deepcopy(_catalog())
    wrong_count["tasks"][0]["visible_test_count"] += 1
    with pytest.raises(CurriculumValidationError, match="visible_test_count"):
        _validate(wrong_count)


def test_catalog_rejects_missing_test_node_and_unsafe_path() -> None:
    missing_node = copy.deepcopy(_catalog())
    missing_node["tasks"][0]["test_nodes"][0] = (
        "tests/stage00/test_task_00a1.py::test_does_not_exist"
    )
    with pytest.raises(CurriculumValidationError, match="does not exist"):
        _validate(missing_node)

    unsafe_path = copy.deepcopy(_catalog())
    unsafe_path["tasks"][0]["task_file"] = "curriculum/../README.md"
    with pytest.raises(CurriculumValidationError, match="safe POSIX|safe repository-relative"):
        _validate(unsafe_path)


def test_catalog_rejects_dangling_and_cyclic_dependencies() -> None:
    dangling = copy.deepcopy(_catalog())
    dangling["tasks"][1]["prerequisites"][0]["task_id"] = "MISSING"
    with pytest.raises(CurriculumValidationError, match="unknown prerequisite"):
        _validate(dangling)

    cycle = copy.deepcopy(_catalog())
    cycle["tasks"][0]["prerequisites"] = [
        {"task_id": "00A-2", "minimum_status": "implemented"}
    ]
    with pytest.raises(CurriculumValidationError, match="not earlier|cycle"):
        _validate(cycle)


def test_catalog_rejects_reference_exposure_and_runtime_mismatches() -> None:
    exposure = copy.deepcopy(_catalog())
    exposure["tasks"][0]["reference_ids"] = ["datawhale-llm-algo-leetcode"]
    with pytest.raises(CurriculumValidationError, match="reference_exposure"):
        _validate(exposure)

    runtime = copy.deepcopy(_catalog())
    runtime["tasks"][0]["gpu_acceptance_policy"] = "cuda-required"
    with pytest.raises(CurriculumValidationError, match="inconsistent runtime"):
        _validate(runtime)


def test_reference_registry_requires_full_pin_and_pinned_license_evidence() -> None:
    short_pin = copy.deepcopy(_registry())
    short_pin["references"][0]["pinned_revision"] = "c7a81f9"
    with pytest.raises(CurriculumValidationError, match="full lowercase commit SHA"):
        validate_reference_registry(short_pin)

    floating_evidence = copy.deepcopy(_registry())
    floating_evidence["references"][0]["licenses"][0]["evidence_url"] = (
        "https://github.com/datawhalechina/llm-algo-leetcode/blob/main/README.md"
    )
    with pytest.raises(CurriculumValidationError, match="pinned revision"):
        validate_reference_registry(floating_evidence)

    unrelated_audit = copy.deepcopy(_registry())
    revision = unrelated_audit["references"][0]["pinned_revision"]
    unrelated_audit["references"][0]["license_audit_url"] = (
        f"https://github.com/unrelated/project/tree/{revision}"
    )
    with pytest.raises(CurriculumValidationError, match="registered repository"):
        validate_reference_registry(unrelated_audit)

    unrelated_evidence = copy.deepcopy(_registry())
    unrelated_evidence["references"][0]["licenses"][0]["evidence_url"] = (
        f"https://github.com/unrelated/project/blob/{revision}/LICENSE"
    )
    with pytest.raises(CurriculumValidationError, match="registered repository"):
        validate_reference_registry(unrelated_evidence)

    invalid_port = copy.deepcopy(_registry())
    invalid_port["references"][0]["repository_url"] = (
        "https://github.com:not-a-port/datawhalechina/llm-algo-leetcode"
    )
    with pytest.raises(CurriculumValidationError, match="valid public HTTPS URL"):
        validate_reference_registry(invalid_port)

    query_token = copy.deepcopy(_registry())
    query_token["references"][0]["repository_url"] = (
        "https://github.com/datawhalechina/llm-algo-leetcode?access_token=secret"
    )
    with pytest.raises(CurriculumValidationError, match="without credentials"):
        validate_reference_registry(query_token)


def test_reference_registry_treats_missing_license_as_no_redistribution_permission() -> None:
    registry = _registry()
    missing_license = next(
        reference
        for reference in registry["references"]
        if reference["id"] == "stanford-cs336-assignment5-alignment"
    )
    assert missing_license["license_status"] == "not-found"
    assert missing_license["licenses"] == []
    assert missing_license["usage"] == "external-course-source"
    assert "recursively" in missing_license["license_audit_method"]
    assert "not legal advice" in missing_license["license_audit_method"]

    false_positive = copy.deepcopy(registry)
    altered = next(
        reference
        for reference in false_positive["references"]
        if reference["id"] == "stanford-cs336-assignment5-alignment"
    )
    altered["licenses"] = [
        {
            "scope": "entire repository",
            "spdx": "MIT",
            "evidence_url": (
                "https://github.com/stanford-cs336/assignment5-alignment/blob/"
                f"{altered['pinned_revision']}/LICENSE"
            ),
        }
    ]
    with pytest.raises(CurriculumValidationError, match="cannot declare licenses"):
        validate_reference_registry(false_positive)


def test_generated_tables_escape_pipes_and_math_backslashes() -> None:
    escaped = _escape_table_cell(r"$x \mid y$ | boundary")

    assert escaped == r"$x \\mid y$ \| boundary"

    catalog = copy.deepcopy(_catalog())
    catalog["tasks"][0]["math_prerequisites"] = [r"$x \mid y$ | boundary"]
    rendered = render_navigation(catalog)
    assert r"$x \\mid y$ \| boundary" in rendered


def test_cli_reports_machine_readable_summary(capsys) -> None:
    exit_code = main(["--json"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert '"ok": true' in output
    assert '"task_count": 4' in output
