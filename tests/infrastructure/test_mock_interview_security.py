from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

import llm_interview_lab.cli as cli_module
from llm_interview_lab.catalog import Catalog, Problem, Track
from llm_interview_lab.interviews import (
    InterviewError,
    create_interview,
    current_question,
    finish_interview,
    list_interviews,
    load_session,
    record_answer,
    record_assessment,
    report_interview,
    run_coding_test,
    start_interview,
)
from llm_interview_lab.materials import add_material
from llm_interview_lab.submissions import SubmissionError
from llm_interview_lab.workspace import init_profile, profile_paths


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]
T0 = datetime(2026, 8, 27, 9, 0, tzinfo=timezone.utc)
SUBJECTIVE_DIMENSIONS = (
    "reasoning_complexity",
    "technical_oral",
    "project_evidence",
    "communication",
)


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        "[project]\nname = 'interview-security-fixture'\nversion = '0'\n",
        encoding="utf-8",
    )
    (root / ".gitignore").write_text(
        "/workspace/profiles/*\n!/workspace/profiles/.gitkeep\n",
        encoding="utf-8",
    )
    (root / "curriculum").mkdir()
    for name in ("schema", "templates"):
        shutil.copytree(REPO_ROOT / "workspace" / name, root / "workspace" / name)
    profiles = root / "workspace" / "profiles"
    profiles.mkdir(parents=True)
    (profiles / ".gitkeep").write_text("", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return root


def _problem(root: Path) -> Problem:
    problem_id = "FND-991"
    problem_dir = root / "synthetic-problems" / problem_id
    problem_dir.mkdir(parents=True)
    (problem_dir / "task.md").write_text(
        "# Synthetic add-one problem\n\nReturn the integer plus one.\n",
        encoding="utf-8",
    )
    (problem_dir / "starter.py").write_text(
        "def add_one(value: int) -> int:\n    raise NotImplementedError\n",
        encoding="utf-8",
    )
    (problem_dir / "test_public.py").write_text(
        "def test_positive(submission):\n"
        "    assert submission.add_one(1) == 2\n\n"
        "def test_negative(submission):\n"
        "    assert submission.add_one(-2) == -1\n",
        encoding="utf-8",
    )
    (problem_dir / "hints.md").write_text("Synthetic hints.\n", encoding="utf-8")
    raw = {
        "id": problem_id,
        "title": "Synthetic Add One",
        "status": "ready",
        "domain": "foundation",
        "tracks": ["ai_foundation"],
        "tier": "core",
        "difficulty": {"concept": 3, "coding": 3, "debugging": 3},
        "prerequisites": [],
        "skills": ["python.functions"],
        "validation": {"level": "oracle", "field_runs": 0},
        "assets": {"problem_dir": problem_dir.relative_to(root).as_posix()},
        "interface": {
            "language": "python",
            "framework": "stdlib",
            "symbol": "add_one",
        },
        "constraints": {
            "forbidden_apis": [],
            "time_limit_ms": 2_000,
            "output_limit_kb": 32,
        },
        "assessment": {
            "runner": {"kind": "pytest", "public_tests": "test_public.py"},
            "oracle": {
                "kind": "fixture_expected",
                "target": "synthetic fixture",
                "description": "Exact outputs for an infrastructure-only problem.",
            },
            "oral_questions": [
                "What is the contract?",
                "What is the complexity?",
                "Which invalid inputs matter?",
                "How would you test it?",
            ],
        },
        "variant_axes": ["integer_value"],
        "invariants": ["result_is_incremented"],
        "common_bugs": ["returns_input"],
        "retention": {
            "d2": "not part of interview fixture",
            "d7": "not part of interview fixture",
        },
        "sources": [
            {"type": "documentation", "title": "Synthetic infrastructure fixture"}
        ],
    }
    return Problem(
        problem_id,
        raw["title"],
        "ready",
        (),
        problem_dir,
        "add_one",
        "pytest",
        problem_dir / "test_public.py",
        "fixture_expected",
        raw,
        2_000,
        32,
    )


def _initialized(tmp_path: Path) -> tuple[Path, Catalog, Problem]:
    root = _repository(tmp_path)
    init_profile(root, "learner-one", ("ai_foundation",))
    problem = _problem(root)
    catalog = Catalog(
        problems={problem.id: problem},
        order=(problem.id,),
        tracks={
            "ai_foundation": Track(
                "ai_foundation", "AI Foundation", "Synthetic security track"
            )
        },
        quests={},
        capstones={},
    )
    return root, catalog, problem


def _create(
    root: Path,
    catalog: Catalog,
    **overrides: object,
) -> dict:
    options: dict[str, object] = {
        "difficulty": "medium",
        "duration_minutes": 45,
        "track_id": "ai_foundation",
        "problem_id": "FND-991",
        "seed": 7,
        "now": T0,
    }
    options.update(overrides)
    return create_interview(root, "learner-one", catalog, **options)  # type: ignore[arg-type]


def _interview_root(root: Path, interview_id: str) -> Path:
    return profile_paths(root, "learner-one").interviews_root / interview_id


def _submission(root: Path, interview_id: str) -> Path:
    return _interview_root(root, interview_id) / "coding" / "submission.py"


def _write_answer_source(tmp_path: Path, question_id: str) -> Path:
    source = tmp_path / f"answer-{question_id}.md"
    source.write_text(
        f"Synthetic, non-sensitive answer for {question_id}.\n", encoding="utf-8"
    )
    return source


def _complete_candidate(
    root: Path,
    catalog: Catalog,
    interview_id: str,
    tmp_path: Path,
) -> None:
    for minute in range(1, 20):
        current = current_question(
            root,
            "learner-one",
            interview_id,
            catalog,
            now=T0 + timedelta(minutes=minute),
        )
        question = current["question"]
        if question is None:
            assert current["status"] == "awaiting_score"
            return
        if question["kind"] == "coding":
            _submission(root, interview_id).write_text(
                "def add_one(value: int) -> int:\n    return value + 1\n",
                encoding="utf-8",
            )
            result = run_coding_test(
                root,
                "learner-one",
                interview_id,
                catalog,
                now=T0 + timedelta(minutes=minute),
            )
            assert result.status in {"passed", "failed"}
        else:
            record_answer(
                root,
                "learner-one",
                interview_id,
                catalog,
                question["question_id"],
                _write_answer_source(tmp_path, question["question_id"]),
                now=T0 + timedelta(minutes=minute),
            )
    raise AssertionError("synthetic interview did not reach awaiting_score")


def _assess(root: Path, catalog: Catalog, interview_id: str) -> None:
    question_by_dimension = {
        "reasoning_complexity": "q-004",
        "technical_oral": "q-003",
        "project_evidence": "q-002",
        "communication": "q-001",
    }
    for dimension in SUBJECTIVE_DIMENSIONS:
        record_assessment(
            root,
            "learner-one",
            interview_id,
            catalog,
            dimension,
            75,
            "human",
            f"Synthetic evidence for {dimension}.",
            "high",
            question_ids=(question_by_dimension[dimension],),
            now=T0 + timedelta(minutes=30),
        )


def _complete_interview(
    root: Path,
    catalog: Catalog,
    tmp_path: Path,
    **create_options: object,
) -> dict:
    session = _create(root, catalog, **create_options)
    interview_id = session["interview_id"]
    start_interview(root, "learner-one", interview_id, catalog, now=T0)
    _complete_candidate(root, catalog, interview_id, tmp_path)
    _assess(root, catalog, interview_id)
    return finish_interview(
        root,
        "learner-one",
        interview_id,
        catalog,
        now=T0 + timedelta(minutes=40),
    )


def _symlink_or_skip(link: Path, target: Path, *, directory: bool) -> None:
    try:
        link.symlink_to(target, target_is_directory=directory)
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"symlink creation is unavailable on this platform: {error}")


def test_profile_ignore_drift_blocks_interview_writes(tmp_path: Path) -> None:
    root, catalog, _ = _initialized(tmp_path)
    (root / ".gitignore").write_text("", encoding="utf-8")

    with pytest.raises(InterviewError, match="ignore|Git"):
        _create(root, catalog)

    assert not any(profile_paths(root, "learner-one").interviews_root.iterdir())


def test_interviews_root_symlink_cannot_escape_profile(tmp_path: Path) -> None:
    root, catalog, _ = _initialized(tmp_path)
    interviews_root = profile_paths(root, "learner-one").interviews_root
    interviews_root.rmdir()
    outside = tmp_path / "outside-interviews"
    outside.mkdir()
    _symlink_or_skip(interviews_root, outside, directory=True)

    with pytest.raises(InterviewError, match="link|reparse|outside|path"):
        _create(root, catalog)

    assert list(outside.iterdir()) == []


def test_answers_symlink_cannot_escape_profile(tmp_path: Path) -> None:
    root, catalog, _ = _initialized(tmp_path)
    session = _create(root, catalog)
    interview_id = session["interview_id"]
    start_interview(root, "learner-one", interview_id, catalog, now=T0)
    outside = tmp_path / "outside-answers"
    outside.mkdir()
    _symlink_or_skip(_interview_root(root, interview_id) / "answers", outside, directory=True)

    with pytest.raises(InterviewError, match="link|reparse|outside|path"):
        record_answer(
            root,
            "learner-one",
            interview_id,
            catalog,
            "q-001",
            _write_answer_source(tmp_path, "q-001"),
            now=T0 + timedelta(minutes=1),
        )

    assert list(outside.iterdir()) == []


def test_coding_symlink_is_rejected_before_grading(tmp_path: Path) -> None:
    root, catalog, _ = _initialized(tmp_path)
    session = _create(root, catalog)
    interview_id = session["interview_id"]
    start_interview(root, "learner-one", interview_id, catalog, now=T0)
    coding = _interview_root(root, interview_id) / "coding"
    shutil.rmtree(coding)
    outside = tmp_path / "outside-coding"
    outside.mkdir()
    (outside / "submission.py").write_text(
        "def add_one(value: int) -> int:\n    return value + 1\n", encoding="utf-8"
    )
    _symlink_or_skip(coding, outside, directory=True)

    with pytest.raises((InterviewError, SubmissionError), match="link|reparse|outside|path"):
        run_coding_test(
            root,
            "learner-one",
            interview_id,
            catalog,
            now=T0 + timedelta(minutes=10),
        )


def test_report_symlink_cannot_overwrite_external_file(tmp_path: Path) -> None:
    root, catalog, _ = _initialized(tmp_path)
    session = _create(root, catalog)
    interview_id = session["interview_id"]
    start_interview(root, "learner-one", interview_id, catalog, now=T0)
    _complete_candidate(root, catalog, interview_id, tmp_path)
    _assess(root, catalog, interview_id)
    external = tmp_path / "external-report.md"
    external.write_text("must survive unchanged\n", encoding="utf-8")
    _symlink_or_skip(
        _interview_root(root, interview_id) / "report.md", external, directory=False
    )

    with pytest.raises(InterviewError, match="link|reparse|report|path"):
        finish_interview(
            root,
            "learner-one",
            interview_id,
            catalog,
            now=T0 + timedelta(minutes=40),
        )

    assert external.read_text(encoding="utf-8") == "must survive unchanged\n"


def test_completed_archive_survives_reference_drift_but_active_mutations_do_not(
    tmp_path: Path,
) -> None:
    root, catalog, problem = _initialized(tmp_path)
    material_source = tmp_path / "resume.md"
    material_source.write_text("Synthetic resume version one.\n", encoding="utf-8")
    material = add_material(
        root,
        "learner-one",
        material_source,
        kind="resume",
        ai_access=True,
        material_id="resume-one",
    )
    tailored = {
        "mode": "tailored",
        "material_ids": (material.id,),
        "consent_materials": True,
    }
    completed = _complete_interview(root, catalog, tmp_path, **tailored)

    stale_material_session = _create(root, catalog, **tailored)
    start_interview(
        root,
        "learner-one",
        stale_material_session["interview_id"],
        catalog,
        now=T0,
    )
    stale_catalog_session = _create(root, catalog)
    start_interview(
        root,
        "learner-one",
        stale_catalog_session["interview_id"],
        catalog,
        now=T0,
    )
    for minute, question_id in enumerate(("q-001", "q-002", "q-003"), 1):
        record_answer(
            root,
            "learner-one",
            stale_catalog_session["interview_id"],
            catalog,
            question_id,
            _write_answer_source(tmp_path, f"catalog-{question_id}"),
            now=T0 + timedelta(minutes=minute),
        )

    stored_material = profile_paths(root, "learner-one").root.joinpath(
        *material.relative_path.split("/")
    )
    stored_material.write_text("Synthetic resume version two.\n", encoding="utf-8")
    task_path = problem.problem_dir / "task.md"
    task_path.write_text(
        task_path.read_text(encoding="utf-8") + "\nContract changed.\n",
        encoding="utf-8",
    )

    archived = load_session(
        root, "learner-one", completed["interview_id"], catalog
    )
    assert archived["status"] == "completed"
    assert completed["interview_id"] in {
        item["interview_id"] for item in list_interviews(root, "learner-one", catalog)
    }
    assert completed["interview_id"] in report_interview(
        root, "learner-one", completed["interview_id"], catalog
    )

    with pytest.raises(InterviewError, match="material|consent|changed|stale"):
        record_answer(
            root,
            "learner-one",
            stale_material_session["interview_id"],
            catalog,
            "q-001",
            _write_answer_source(tmp_path, "stale-material"),
            now=T0 + timedelta(minutes=1),
        )
    with pytest.raises(InterviewError, match="problem|contract|changed|stale"):
        run_coding_test(
            root,
            "learner-one",
            stale_catalog_session["interview_id"],
            catalog,
            now=T0 + timedelta(minutes=10),
        )


@pytest.mark.parametrize("change", ["delete", "tamper"])
def test_missing_or_changed_answer_cannot_complete(
    tmp_path: Path, change: str
) -> None:
    root, catalog, _ = _initialized(tmp_path)
    session = _create(root, catalog)
    interview_id = session["interview_id"]
    start_interview(root, "learner-one", interview_id, catalog, now=T0)
    _complete_candidate(root, catalog, interview_id, tmp_path)
    _assess(root, catalog, interview_id)
    stored = load_session(root, "learner-one", interview_id, catalog)
    answer = profile_paths(root, "learner-one").root.joinpath(
        *stored["answers"]["q-001"]["answer_relpath"].split("/")
    )
    if change == "delete":
        answer.unlink()
    else:
        answer.write_text("tampered after recording\n", encoding="utf-8")

    final = finish_interview(
        root,
        "learner-one",
        interview_id,
        catalog,
        now=T0 + timedelta(minutes=46),
    )
    assert final["result"]["completion_status"] != "completed"


def test_failed_grader_status_can_never_receive_full_coding_score(
    tmp_path: Path,
) -> None:
    root, catalog, problem = _initialized(tmp_path)
    problem.public_tests.write_text(
        "def test_passes(submission):\n"
        "    assert submission.add_one(1) == 2\n\n"
        "def test_errors(submission, fixture_that_does_not_exist):\n"
        "    assert submission.add_one(2) == 3\n",
        encoding="utf-8",
    )
    session = _create(root, catalog)
    interview_id = session["interview_id"]
    start_interview(root, "learner-one", interview_id, catalog, now=T0)
    _complete_candidate(root, catalog, interview_id, tmp_path)
    _assess(root, catalog, interview_id)

    evidence = load_session(root, "learner-one", interview_id, catalog)[
        "coding_evidence"
    ]
    assert evidence["status"] == "failed"
    assert evidence["passed"] == 1 and evidence["failed"] == 0
    final = finish_interview(
        root,
        "learner-one",
        interview_id,
        catalog,
        now=T0 + timedelta(minutes=40),
    )
    assert final["result"]["dimensions"]["coding_correctness"]["score"] < 100


def test_revoking_ai_access_blocks_active_tailored_interview(tmp_path: Path) -> None:
    root, catalog, _ = _initialized(tmp_path)
    source = tmp_path / "experience.md"
    source.write_text("Synthetic project evidence.\n", encoding="utf-8")
    material = add_material(
        root,
        "learner-one",
        source,
        kind="experience",
        ai_access=True,
        material_id="experience-one",
    )
    session = _create(
        root,
        catalog,
        mode="tailored",
        material_ids=(material.id,),
        consent_materials=True,
    )
    start_interview(root, "learner-one", session["interview_id"], catalog, now=T0)
    manifest_path = profile_paths(root, "learner-one").materials_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["materials"][0]["ai_access"] = False
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    with pytest.raises(InterviewError, match="AI access|consent|revoked|stale"):
        record_answer(
            root,
            "learner-one",
            session["interview_id"],
            catalog,
            "q-001",
            _write_answer_source(tmp_path, "revoked"),
            now=T0 + timedelta(minutes=1),
        )


def test_corrupt_session_does_not_hide_other_interviews(tmp_path: Path) -> None:
    root, catalog, _ = _initialized(tmp_path)
    good = _create(root, catalog)
    bad = _create(root, catalog)
    (_interview_root(root, bad["interview_id"]) / "session.json").write_text(
        "{not valid json", encoding="utf-8"
    )

    values = list_interviews(root, "learner-one", catalog)

    assert good["interview_id"] in {item["interview_id"] for item in values}
    unreadable = next(item for item in values if item["interview_id"] == bad["interview_id"])
    assert unreadable["status"] == "unreadable"
    assert unreadable["warnings"] and all(
        isinstance(warning, str) for warning in unreadable["warnings"]
    )


def test_repeated_finish_rebuilds_a_missing_generated_report(tmp_path: Path) -> None:
    root, catalog, _ = _initialized(tmp_path)
    completed = _complete_interview(root, catalog, tmp_path)
    interview_id = completed["interview_id"]
    report_path = _interview_root(root, interview_id) / "report.md"
    expected = report_interview(root, "learner-one", interview_id, catalog)
    report_path.unlink()

    repeated = finish_interview(
        root,
        "learner-one",
        interview_id,
        catalog,
        now=T0 + timedelta(minutes=41),
    )

    assert repeated == completed
    assert report_path.read_text(encoding="utf-8") == expected


@pytest.mark.parametrize("field", ["started_at", "deadline", "coding_submission_relpath"])
def test_active_session_requires_complete_execution_state(
    tmp_path: Path,
    field: str,
) -> None:
    root, catalog, _ = _initialized(tmp_path)
    created = _create(root, catalog)
    interview_id = created["interview_id"]
    start_interview(root, "learner-one", interview_id, catalog, now=T0)
    session_path = _interview_root(root, interview_id) / "session.json"
    raw = json.loads(session_path.read_text(encoding="utf-8"))
    raw[field] = None
    session_path.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    with pytest.raises(InterviewError, match="active|execution|state|started|deadline|submission"):
        load_session(root, "learner-one", interview_id, catalog)


@pytest.mark.parametrize("field", ["started_at", "deadline", "coding_submission_relpath"])
def test_finalized_session_requires_complete_execution_state(
    tmp_path: Path,
    field: str,
) -> None:
    root, catalog, _ = _initialized(tmp_path)
    completed = _complete_interview(root, catalog, tmp_path)
    interview_id = completed["interview_id"]
    session_path = _interview_root(root, interview_id) / "session.json"
    raw = json.loads(session_path.read_text(encoding="utf-8"))
    raw[field] = None
    session_path.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    with pytest.raises(InterviewError, match="final|execution|state|started|deadline|submission"):
        load_session(
            root,
            "learner-one",
            interview_id,
            catalog,
            verify_references=False,
        )


def test_completed_archive_show_and_report_disclose_reference_drift(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, catalog, _ = _initialized(tmp_path)
    source = tmp_path / "archive-resume.md"
    source.write_text("Synthetic archive material version one.\n", encoding="utf-8")
    material = add_material(
        root,
        "learner-one",
        source,
        kind="resume",
        ai_access=True,
        material_id="archive-resume",
    )
    completed = _complete_interview(
        root,
        catalog,
        tmp_path,
        mode="tailored",
        material_ids=(material.id,),
        consent_materials=True,
    )
    stored = profile_paths(root, "learner-one").root.joinpath(
        *material.relative_path.split("/")
    )
    stored.write_text("Synthetic archive material version two.\n", encoding="utf-8")

    assert cli_module._interview_show(
        root, catalog, "learner-one", completed["interview_id"], False
    ) == 0
    shown = capsys.readouterr().out.lower()
    assert "warning" in shown and material.id in shown
    assert "plan sha256=" in shown and "question plan" in shown

    assert cli_module._interview_report(
        root,
        catalog,
        "learner-one",
        completed["interview_id"],
        "markdown",
    ) == 0
    report = capsys.readouterr().out.lower()
    assert "warning" in report and material.id in report


def test_late_candidate_evidence_records_actual_elapsed_time(tmp_path: Path) -> None:
    root, catalog, _ = _initialized(tmp_path)
    session = _create(root, catalog)
    interview_id = session["interview_id"]
    start_interview(root, "learner-one", interview_id, catalog, now=T0)
    _complete_candidate(root, catalog, interview_id, tmp_path)
    _assess(root, catalog, interview_id)
    session_path = _interview_root(root, interview_id) / "session.json"
    raw = json.loads(session_path.read_text(encoding="utf-8"))
    late = (T0 + timedelta(minutes=46)).isoformat()
    assessed_late = (T0 + timedelta(minutes=47)).isoformat()
    raw["coding_evidence"]["tested_at"] = late
    for assessment in raw["assessments"].values():
        assessment["assessed_at"] = assessed_late
    for event in raw["timeline"]:
        if event["event"] == "coding_tested":
            event["timestamp"] = late
        elif event["event"] == "assessment_recorded":
            event["timestamp"] = assessed_late
    session_path.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    final = finish_interview(
        root,
        "learner-one",
        interview_id,
        catalog,
        now=T0 + timedelta(minutes=48),
    )

    assert final["result"]["completion_status"] == "timed_out"
    assert final["result"]["elapsed_seconds"] == 46 * 60


def test_completed_archive_discloses_answer_and_submission_drift(
    tmp_path: Path,
) -> None:
    root, catalog, _ = _initialized(tmp_path)
    completed = _complete_interview(root, catalog, tmp_path)
    interview_id = completed["interview_id"]
    profile_root = profile_paths(root, "learner-one").root
    answer = completed["answers"]["q-001"]
    profile_root.joinpath(*answer["answer_relpath"].split("/")).write_text(
        "Changed archived answer.\n", encoding="utf-8"
    )
    _submission(root, interview_id).write_text(
        "def add_one(value: int) -> int:\n    return value - 1\n",
        encoding="utf-8",
    )

    listed = list_interviews(root, "learner-one", catalog)[0]
    assert any("answer q-001" in item for item in listed["warnings"])
    assert any("coding submission" in item for item in listed["warnings"])
    rendered = report_interview(
        root, "learner-one", interview_id, catalog, format_name="markdown"
    )
    assert "Archive reference warnings" in rendered
    assert "answer q-001" in rendered and "coding submission" in rendered
