from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

import llm_interview_lab.workspace as workspace_module
from llm_interview_lab.materials import MATERIAL_KINDS, add_material, list_materials
from llm_interview_lab.workspace import (
    WorkspaceError,
    init_profile,
    load_profile,
    profile_paths,
    update_career_intent,
)


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]
CAREER_FIELDS = {
    "target_job_titles",
    "employment_stage",
    "preferred_locations",
    "interview_languages",
    "priorities",
}
NEW_MATERIAL_KINDS = {
    "career_intent",
    "internship",
    "project",
    "paper",
    "competition",
    "interview_question",
}


def _workspace_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    (root / ".gitignore").write_text(
        "/workspace/profiles/*\n!/workspace/profiles/.gitkeep\n",
        encoding="utf-8",
    )
    shutil.copytree(REPO_ROOT / "workspace/schema", root / "workspace/schema")
    shutil.copytree(
        REPO_ROOT / "workspace/templates", root / "workspace/templates"
    )
    profiles = root / "workspace/profiles"
    profiles.mkdir()
    (profiles / ".gitkeep").write_text("", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return root


def _intent(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "target_job_titles": ["VLM Algorithm Engineer"],
        "employment_stage": "internship",
        "preferred_locations": ["Hong Kong", "Shenzhen"],
        "interview_languages": ["zh-CN", "en"],
        "priorities": ["post-training", "multimodal evaluation"],
    }
    value.update(overrides)
    return value


def test_new_profile_template_has_bounded_career_intent(tmp_path: Path) -> None:
    root = _workspace_repo(tmp_path)
    paths = init_profile(root, "learner-one").paths

    profile = load_profile(paths, root)
    assert profile["career_intent"] == {
        "target_job_titles": [],
        "employment_stage": "flexible",
        "preferred_locations": [],
        "interview_languages": [],
        "priorities": [],
    }
    schema = json.loads(
        (root / "workspace/schema/profile.schema.json").read_text(encoding="utf-8")
    )
    career_schema = schema["properties"]["career_intent"]
    assert career_schema["additionalProperties"] is False
    assert set(career_schema["properties"]) == CAREER_FIELDS
    assert "career_intent" not in schema["required"]


def test_profile_init_rejects_a_partial_git_ignore_rule(tmp_path: Path) -> None:
    root = _workspace_repo(tmp_path)
    (root / ".gitignore").write_text(
        "/workspace/profiles/*/events.jsonl\n",
        encoding="utf-8",
    )

    with pytest.raises(WorkspaceError, match="not fully ignored"):
        init_profile(root, "learner-one")

    assert not profile_paths(root, "learner-one").root.exists()


def test_legacy_profile_without_career_intent_remains_valid_and_unchanged(
    tmp_path: Path,
) -> None:
    root = _workspace_repo(tmp_path)
    paths = init_profile(root, "learner-one").paths
    legacy = yaml.safe_load(paths.profile_file.read_text(encoding="utf-8"))
    legacy.pop("career_intent")
    paths.profile_file.write_text(
        yaml.safe_dump(legacy, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
        newline="\n",
    )
    profile_before = paths.profile_file.read_bytes()
    events_before = paths.events_file.read_bytes()

    assert "career_intent" not in load_profile(paths, root)
    result = init_profile(root, "learner-one")

    assert not result.created
    assert paths.profile_file.read_bytes() == profile_before
    assert paths.events_file.read_bytes() == events_before


def test_update_career_intent_is_atomic_current_configuration_only(
    tmp_path: Path,
) -> None:
    root = _workspace_repo(tmp_path)
    paths = init_profile(root, "learner-one", ("llm_algorithm",)).paths
    before = load_profile(paths, root)
    events_before = paths.events_file.read_bytes()
    git_before = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    expected = _intent()
    updated = update_career_intent(root, "learner-one", expected)

    assert updated["career_intent"] == expected
    assert load_profile(paths, root) == updated
    assert {key: value for key, value in updated.items() if key != "career_intent"} == {
        key: value for key, value in before.items() if key != "career_intent"
    }
    assert paths.events_file.read_bytes() == events_before
    assert not tuple(paths.root.glob(".profile.yaml.*.tmp"))
    git_after = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert git_after == git_before


@pytest.mark.parametrize(
    "invalid",
    [
        _intent(employment_stage="student"),
        _intent(target_job_titles=["x" * 101]),
        _intent(target_job_titles=[f"role-{index}" for index in range(11)]),
        _intent(preferred_locations=["x" * 101]),
        _intent(interview_languages=["../../private/resume"]),
        _intent(interview_languages=["en"] * 2),
        _intent(priorities=["x" * 121]),
        {**_intent(), "resume_path": "C:/private/resume.md"},
    ],
)
def test_update_career_intent_rejects_unbounded_or_unknown_values_without_writes(
    tmp_path: Path,
    invalid: dict[str, object],
) -> None:
    root = _workspace_repo(tmp_path)
    paths = init_profile(root, "learner-one").paths
    profile_before = paths.profile_file.read_bytes()
    events_before = paths.events_file.read_bytes()

    with pytest.raises(WorkspaceError, match="invalid profile"):
        update_career_intent(root, "learner-one", invalid)

    assert paths.profile_file.read_bytes() == profile_before
    assert paths.events_file.read_bytes() == events_before


def test_update_career_intent_rolls_back_an_atomic_replace_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _workspace_repo(tmp_path)
    paths = init_profile(root, "learner-one").paths
    profile_before = paths.profile_file.read_bytes()
    events_before = paths.events_file.read_bytes()

    def fail_replace(source: Path, destination: Path) -> None:
        raise OSError("injected replace failure")

    monkeypatch.setattr(workspace_module.os, "replace", fail_replace)
    with pytest.raises(WorkspaceError, match="atomically"):
        update_career_intent(root, "learner-one", _intent())

    assert paths.profile_file.read_bytes() == profile_before
    assert paths.events_file.read_bytes() == events_before
    assert not tuple(paths.root.glob(".profile.yaml.*.tmp"))


def test_specific_career_material_kinds_are_additive_and_schema_synchronized(
    tmp_path: Path,
) -> None:
    root = _workspace_repo(tmp_path)
    init_profile(root, "learner-one")
    source = tmp_path / "sanitized.md"
    source.write_text("synthetic: true\n", encoding="utf-8")

    for kind in sorted(NEW_MATERIAL_KINDS):
        add_material(
            root,
            "learner-one",
            source,
            material_id=f"kind-{kind.replace('_', '-')}",
            kind=kind,
            ai_access=True,
        )

    assert {record.kind for record in list_materials(root, "learner-one")} == (
        NEW_MATERIAL_KINDS
    )
    material_schema = json.loads(
        (root / "workspace/schema/material.schema.json").read_text(encoding="utf-8")
    )
    interview_schema = json.loads(
        (root / "workspace/schema/interview.schema.json").read_text(encoding="utf-8")
    )
    assert set(material_schema["$defs"]["material"]["properties"]["kind"]["enum"]) == (
        MATERIAL_KINDS
    )
    assert set(interview_schema["$defs"]["material_ref"]["properties"]["kind"]["enum"]) == (
        MATERIAL_KINDS
    )
