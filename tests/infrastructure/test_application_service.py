from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from llm_interview_lab.application import ApplicationService
from llm_interview_lab.workspace import load_profile, profile_paths


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        "[project]\nname='application-fixture'\nversion='0'\n", encoding="utf-8"
    )
    (root / ".gitignore").write_text(
        "/workspace/profiles/*\n!/workspace/profiles/.gitkeep\n", encoding="utf-8"
    )
    shutil.copytree(REPO_ROOT / "curriculum", root / "curriculum")
    shutil.copytree(REPO_ROOT / "workspace/schema", root / "workspace/schema")
    shutil.copytree(REPO_ROOT / "workspace/templates", root / "workspace/templates")
    (root / "workspace/profiles").mkdir(parents=True)
    (root / "workspace/profiles/.gitkeep").write_text("", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return root


def test_shared_application_service_initializes_role_and_local_material(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    service = ApplicationService(root)
    cards = service.role_cards()
    assert len(cards) == 8
    assert all(6 <= len(card["top_skills"]) <= 8 for card in cards)
    result = service.initialize_profile(
        "learner-one",
        role_id="applied_ai_engineer",
        seniority="new_grad",
        ai_mode="disabled",
    )
    assert result["created"]
    profile = load_profile(profile_paths(root, "learner-one"), root)
    assert profile["role_preferences"]["primary_role"] == "applied_ai_engineer"
    dashboard = service.dashboard("learner-one")
    assert dashboard["unlocks"]
    assert dashboard["role"]["title"] == "Applied AI Engineer"

    source = tmp_path / "resume.md"
    source.write_text("Synthetic resume. No employer data.\n", encoding="utf-8")
    material = service.add_career_material(
        "learner-one",
        source,
        kind="resume",
        title="Synthetic resume",
        ai_access=True,
    )
    assert material["id"].startswith("material-")
    assert service.material_cards("learner-one") == [material]
    assert "No employer data" not in (
        root / "workspace/profiles/learner-one/materials/manifest.json"
    ).read_text(encoding="utf-8")


def test_noninteractive_quickstart_is_one_command_and_needs_no_ai(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "llm_interview_lab.cli",
            "quickstart",
            "--profile",
            "first-user",
            "--role",
            "ai_product_manager",
            "--seniority",
            "new_grad",
            "--ai",
            "disabled",
            "--non-interactive",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "PROFILE first-user: created" in completed.stdout
    assert "ROLE AI Product Manager" in completed.stdout
    assert "AI disabled" in completed.stdout
    assert "NEXT llm-lab test" in completed.stdout
    assert profile_paths(root, "first-user").profile_file.is_file()


def test_application_service_edits_only_the_active_interview_coding_answer(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    service = ApplicationService(root)
    service.initialize_profile(
        "coding-user", role_id="applied_ai_engineer", seniority="new_grad"
    )
    session = service.create_interview(
        "coding-user",
        role_id="applied_ai_engineer",
        seniority="new_grad",
        difficulty="medium",
        seed=3,
    )
    interview_id = session["interview_id"]
    service.start_interview("coding-user", interview_id)
    current = service.current_interview("coding-user", interview_id)["question"]
    assert current is not None and current["kind"] == "coding"
    original = service.current_interview_coding_submission(
        "coding-user", interview_id
    )
    replacement = original["text"] + "\n# local timed attempt\n"
    saved = service.save_interview_coding_submission(
        "coding-user", interview_id, replacement
    )
    assert saved["text"] == replacement
    assert saved["sha256"] != original["sha256"]
    assert service.current_interview_coding_submission(
        "coding-user", interview_id
    )["text"] == replacement
