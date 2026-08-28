from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from llm_interview_lab.catalog import Catalog, Problem, Track
from llm_interview_lab.events import read_events, reduce_events
from llm_interview_lab.grader import GraderResult
from llm_interview_lab.interviews import (
    InterviewError,
    create_interview,
    current_question,
    finish_interview,
    list_interviews,
    load_session,
    record_answer,
    record_assessment,
    run_coding_test,
    start_interview,
)
from llm_interview_lab.materials import add_material
from llm_interview_lab.workspace import event_schema_path, init_profile, profile_paths


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]
T0 = datetime(2026, 8, 27, 9, 0, tzinfo=timezone.utc)
DIMENSIONS = {
    "coding_correctness": 30,
    "reasoning_complexity": 20,
    "technical_oral": 20,
    "project_evidence": 15,
    "communication": 10,
    "time_management": 5,
}


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        "[project]\nname = 'interview-fixture'\nversion = '0'\n",
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


def _problem(
    root: Path,
    problem_id: str,
    *,
    difficulty: int,
    track: str = "ai_foundation",
    validation: str = "oracle",
    status: str = "ready",
) -> Problem:
    raw = {
        "id": problem_id,
        "title": f"Synthetic {problem_id}",
        "status": status,
        "domain": "foundation",
        "tracks": [track],
        "tier": "core",
        "difficulty": {
            "concept": difficulty,
            "coding": difficulty,
            "debugging": difficulty,
        },
        "prerequisites": [],
        "skills": ["python.functions"],
        "validation": {"level": validation, "field_runs": 0},
        "variant_axes": ["integer_value"],
        "invariants": ["result_is_incremented"],
        "common_bugs": ["returns_input"],
        "retention": {"d2": "not part of interview fixture", "d7": "not part of interview fixture"},
        "sources": [{"type": "documentation", "title": "Synthetic infrastructure fixture"}],
    }
    if status == "planned":
        raw.update({"problem_type": "implementation", "description": "Synthetic planned node"})
        return Problem(problem_id, raw["title"], status, (), None, None, None, None, None, raw)

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
    raw.update(
        {
            "assets": {"problem_dir": problem_dir.relative_to(root).as_posix()},
            "interface": {"language": "python", "framework": "stdlib", "symbol": "add_one"},
            "constraints": {"forbidden_apis": [], "time_limit_ms": 2_000, "output_limit_kb": 32},
            "assessment": {
                "runner": {"kind": "pytest", "public_tests": "test_public.py"},
                "oracle": {
                    "kind": "fixture_expected",
                    "target": "synthetic fixture",
                    "description": "Exact outputs for a tiny infrastructure-only problem.",
                },
                "oral_questions": [
                    "What is the contract?",
                    "What is the complexity?",
                    "Which invalid inputs matter?",
                    "How would you test it?",
                ],
            },
        }
    )
    return Problem(
        problem_id,
        raw["title"],
        status,
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


def _catalog(root: Path) -> Catalog:
    problems = {
        "FND-901": _problem(root, "FND-901", difficulty=1),
        "FND-902": _problem(root, "FND-902", difficulty=3),
        "FND-903": _problem(root, "FND-903", difficulty=5),
        "FND-904": _problem(root, "FND-904", difficulty=3, track="systems"),
        "FND-905": _problem(root, "FND-905", difficulty=3, validation="contract"),
        "FND-906": _problem(root, "FND-906", difficulty=3, status="planned"),
        "CAP-FND-999": _problem(root, "CAP-FND-999", difficulty=3),
    }
    return Catalog(
        problems=problems,
        order=tuple(problems),
        tracks={
            "ai_foundation": Track("ai_foundation", "AI Foundation", "Synthetic foundation track"),
            "systems": Track("systems", "Systems", "Synthetic systems track"),
        },
        quests={},
        capstones={},
    )


def _initialized(tmp_path: Path, *profile_ids: str) -> tuple[Path, Catalog]:
    root = _repository(tmp_path)
    for profile_id in profile_ids or ("learner-one",):
        init_profile(root, profile_id, ("ai_foundation",))
    return root, _catalog(root)


def _create(
    root: Path,
    catalog: Catalog,
    profile_id: str = "learner-one",
    **overrides,
) -> dict:
    options = {
        "difficulty": "medium",
        "duration_minutes": 45,
        "track_id": "ai_foundation",
        "problem_id": "FND-902",
        "seed": 7,
        "now": T0,
    }
    options.update(overrides)
    return create_interview(root, profile_id, catalog, **options)


def _session_path(root: Path, profile_id: str, interview_id: str) -> Path:
    return profile_paths(root, profile_id).root / "interviews" / interview_id / "session.json"


def _coding_path(root: Path, profile_id: str, interview_id: str, problem_id: str) -> Path:
    del problem_id
    return (
        profile_paths(root, profile_id).root
        / "interviews"
        / interview_id
        / "coding"
        / "submission.py"
    )


def _record_complete_assessment(
    root: Path,
    profile_id: str,
    interview_id: str,
    catalog: Catalog,
) -> None:
    scores = {
        "reasoning_complexity": 80,
        "technical_oral": 60,
        "project_evidence": 40,
        "communication": 20,
    }
    evidence_questions = {
        "reasoning_complexity": ("q-004",),
        "technical_oral": ("q-003",),
        "project_evidence": ("q-002",),
        "communication": ("q-001",),
    }
    for dimension, score in scores.items():
        record_assessment(
            root,
            profile_id,
            interview_id,
            catalog,
            dimension,
            score,
            "ai",
            f"Synthetic evidence for {dimension}.",
            "medium",
            question_ids=evidence_questions[dimension],
            now=T0 + timedelta(minutes=30),
        )


def _record_complete_candidate_evidence(
    root: Path,
    profile_id: str,
    interview_id: str,
    catalog: Catalog,
) -> None:
    session = load_session(root, profile_id, interview_id, catalog)
    for index, question in enumerate(session["questions"], 1):
        if question["kind"] == "coding":
            submission = _coding_path(
                root,
                profile_id,
                interview_id,
                session["selected_problem"]["problem_id"],
            )
            submission.write_text(
                "def add_one(value: int) -> int:\n    return value + 1\n",
                encoding="utf-8",
            )
            result = run_coding_test(
                root,
                profile_id,
                interview_id,
                catalog,
                now=T0 + timedelta(minutes=index),
            )
            assert result.status == "passed"
            continue
        source = root.parent / f"{profile_id}-{question['question_id']}.md"
        source.write_text(
            f"Synthetic answer for {question['question_id']}.", encoding="utf-8"
        )
        record_answer(
            root,
            profile_id,
            interview_id,
            catalog,
            question["question_id"],
            source,
            now=T0 + timedelta(minutes=index),
        )


def _advance_to_coding(
    root: Path,
    profile_id: str,
    interview_id: str,
    catalog: Catalog,
) -> dict:
    for index in range(10):
        current = current_question(
            root,
            profile_id,
            interview_id,
            catalog,
            now=T0 + timedelta(minutes=index),
        )
        question = current["question"]
        assert question is not None, "synthetic interview must contain a coding question"
        if question["kind"] == "coding":
            return question
        answer = root.parent / f"advance-{profile_id}-{question['question_id']}.md"
        answer.write_text(
            f"Synthetic answer for {question['question_id']}.", encoding="utf-8"
        )
        record_answer(
            root,
            profile_id,
            interview_id,
            catalog,
            question["question_id"],
            answer,
            now=T0 + timedelta(minutes=index),
        )
    raise AssertionError("coding question was not reached")


@pytest.mark.parametrize("duration", [30, 45, 60, 90])
@pytest.mark.parametrize(
    ("difficulty", "problem_id"),
    [("easy", "FND-901"), ("medium", "FND-902"), ("hard", "FND-903")],
)
def test_create_accepts_only_supported_presets_and_matching_problem(
    tmp_path: Path,
    duration: int,
    difficulty: str,
    problem_id: str,
) -> None:
    root, catalog = _initialized(tmp_path)

    session = _create(
        root,
        catalog,
        difficulty=difficulty,
        duration_minutes=duration,
        problem_id=problem_id,
    )

    assert session["interview_id"] == "interview-0001"
    assert session["status"] == "ready"
    assert session["configuration"]["difficulty"] == difficulty
    assert session["configuration"]["duration_minutes"] == duration
    assert session["selected_problem"]["problem_id"] == problem_id
    assert _session_path(root, "learner-one", "interview-0001").is_file()


@pytest.mark.parametrize("duration", [0, 29, 31, 120, True])
def test_create_rejects_invalid_duration(tmp_path: Path, duration: object) -> None:
    root, catalog = _initialized(tmp_path)

    with pytest.raises(InterviewError, match="duration"):
        _create(root, catalog, duration_minutes=duration)  # type: ignore[arg-type]


@pytest.mark.parametrize("difficulty", ["", "beginner", "MEDIUM", 3, True])
def test_create_rejects_invalid_difficulty(tmp_path: Path, difficulty: object) -> None:
    root, catalog = _initialized(tmp_path)

    with pytest.raises(InterviewError, match="difficulty"):
        _create(root, catalog, difficulty=difficulty)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("problem_id", "track_id", "difficulty", "message"),
    [
        ("FND-901", "ai_foundation", "medium", "selected problem"),
        ("FND-904", "ai_foundation", "medium", "selected problem"),
        ("FND-905", "ai_foundation", "medium", "selected problem"),
        ("FND-906", "ai_foundation", "medium", "selected problem"),
        ("CAP-FND-999", "ai_foundation", "medium", "selected problem"),
        ("FND-999", "ai_foundation", "medium", "unknown"),
    ],
)
def test_explicit_problem_must_be_real_recommendable_non_cap_and_match_request(
    tmp_path: Path,
    problem_id: str,
    track_id: str,
    difficulty: str,
    message: str,
) -> None:
    root, catalog = _initialized(tmp_path)

    with pytest.raises(InterviewError, match=message):
        _create(
            root,
            catalog,
            problem_id=problem_id,
            track_id=track_id,
            difficulty=difficulty,
        )


def test_catalog_selection_is_deterministic_and_never_selects_ineligible_nodes(
    tmp_path: Path,
) -> None:
    root, catalog = _initialized(tmp_path, "learner-one", "learner-two")

    first = _create(root, catalog, "learner-one", problem_id=None, seed=19)
    second = _create(root, catalog, "learner-two", problem_id=None, seed=19)

    assert (
        first["selected_problem"]["problem_id"]
        == second["selected_problem"]["problem_id"]
        == "FND-902"
    )
    assert first["questions"] == second["questions"]
    assert first["selected_problem"]["problem_id"] not in {
        "FND-904",
        "FND-905",
        "FND-906",
        "CAP-FND-999",
    }


def test_materials_require_explicit_ai_access_and_per_interview_consent(
    tmp_path: Path,
) -> None:
    root, catalog = _initialized(tmp_path)
    source = tmp_path / "synthetic-resume.md"
    source.write_text("SYNTHETIC RESUME TOKEN: ALPHA-ONLY", encoding="utf-8")
    allowed = add_material(
        root,
        "learner-one",
        source,
        kind="resume",
        title="Synthetic resume",
        ai_access=True,
        material_id="material-0001",
    )
    private = add_material(
        root,
        "learner-one",
        source,
        kind="resume",
        title="Private synthetic resume",
        ai_access=False,
        material_id="material-0002",
    )

    with pytest.raises(InterviewError, match="consent"):
        _create(root, catalog, material_ids=(allowed.id,))
    with pytest.raises(InterviewError, match="AI (?:access|use)"):
        _create(
            root,
            catalog,
            material_ids=(private.id,),
            consent_materials=True,
            mode="tailored",
        )

    session = _create(
        root,
        catalog,
        material_ids=(allowed.id,),
        consent_materials=True,
        mode="tailored",
    )
    serialized = _session_path(root, "learner-one", session["interview_id"]).read_text(
        encoding="utf-8"
    )
    assert session["material_refs"][0]["id"] == allowed.id
    assert session["material_refs"][0]["sha256"] == allowed.sha256
    assert session["material_refs"][0]["allowed_use"] == "mock_interview"
    assert "material_id" not in session["material_refs"][0]
    assert "ALPHA-ONLY" not in serialized
    assert str(source.resolve()) not in serialized


def test_tailored_focus_is_visible_in_experience_prompt_but_not_problem_selector(
    tmp_path: Path,
) -> None:
    root, catalog = _initialized(tmp_path, "learner-one", "learner-two")
    source = tmp_path / "synthetic-experience.md"
    source.write_text("A fully fictional project record.", encoding="utf-8")
    for profile_id in ("learner-one", "learner-two"):
        add_material(
            root,
            profile_id,
            source,
            kind="experience",
            ai_access=True,
            material_id="material-0001",
        )

    first = _create(
        root,
        catalog,
        "learner-one",
        problem_id=None,
        mode="tailored",
        material_ids=("material-0001",),
        consent_materials=True,
        focus="ownership and failed distributed-training experiments",
        seed=23,
    )
    second = _create(
        root,
        catalog,
        "learner-two",
        problem_id=None,
        mode="tailored",
        material_ids=("material-0001",),
        consent_materials=True,
        focus="reward hacking and verifier design",
        seed=23,
    )

    assert first["selected_problem"] == second["selected_problem"]
    first_experience = next(
        question for question in first["questions"] if question["kind"] == "experience"
    )
    second_experience = next(
        question for question in second["questions"] if question["kind"] == "experience"
    )
    assert first["configuration"]["focus"] in first_experience["prompt"]
    assert second["configuration"]["focus"] in second_experience["prompt"]
    assert first_experience["prompt"] != second_experience["prompt"]


def test_created_private_materials_and_sessions_never_change_git_status(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    catalog = _catalog(root)
    before = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    init_profile(root, "learner-one", ("ai_foundation",))
    source = tmp_path / "synthetic-paper.md"
    source.write_text("A fully fictional paper summary.", encoding="utf-8")
    material = add_material(
        root,
        "learner-one",
        source,
        kind="research",
        ai_access=True,
        material_id="material-0001",
    )
    session = _create(
        root,
        catalog,
        material_ids=(material.id,),
        consent_materials=True,
        mode="tailored",
    )
    after = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    assert before == after
    for candidate in (
        profile_paths(root, "learner-one").root / "materials" / "manifest.json",
        _session_path(root, "learner-one", session["interview_id"]),
    ):
        ignored = subprocess.run(
            ["git", "check-ignore", "-q", str(candidate.relative_to(root))],
            cwd=root,
            check=False,
        )
        assert ignored.returncode == 0


def test_start_is_idempotent_copies_starter_and_fixes_deadline(tmp_path: Path) -> None:
    root, catalog = _initialized(tmp_path)
    created = _create(root, catalog)
    interview_id = created["interview_id"]

    first = start_interview(root, "learner-one", interview_id, catalog, now=T0)
    submission = _coding_path(root, "learner-one", interview_id, "FND-902")
    assert first["status"] == "active"
    assert first["started_at"] == T0.isoformat()
    assert first["deadline"] == (T0 + timedelta(minutes=45)).isoformat()
    assert submission.read_bytes() == (catalog.get("FND-902").problem_dir / "starter.py").read_bytes()

    submission.write_text("# learner work must survive repeated start\n", encoding="utf-8")
    second = start_interview(
        root,
        "learner-one",
        interview_id,
        catalog,
        now=T0 + timedelta(minutes=5),
    )
    assert second["deadline"] == first["deadline"]
    assert submission.read_text(encoding="utf-8") == "# learner work must survive repeated start\n"


def test_current_question_returns_one_item_and_record_answer_copies_then_advances(
    tmp_path: Path,
) -> None:
    root, catalog = _initialized(tmp_path)
    session = _create(root, catalog, focus="Python reliability")
    interview_id = session["interview_id"]
    start_interview(root, "learner-one", interview_id, catalog, now=T0)

    current = current_question(root, "learner-one", interview_id, catalog, now=T0)
    assert current["status"] == "active"
    assert current["remaining_seconds"] == 45 * 60
    assert isinstance(current["question"], dict)
    assert "questions" not in current
    question_id = current["question"]["question_id"]
    answer = tmp_path / "answer.md"
    answer.write_text("A synthetic spoken answer.", encoding="utf-8")

    updated = record_answer(
        root,
        "learner-one",
        interview_id,
        catalog,
        question_id,
        answer,
        asked_question="A personalized but synthetic question?",
        now=T0 + timedelta(minutes=1),
    )
    answer.write_text("changed after recording", encoding="utf-8")
    evidence = updated["answers"][question_id]
    recorded = profile_paths(root, "learner-one").root.joinpath(
        *evidence["answer_relpath"].split("/")
    )
    assert recorded.read_text(encoding="utf-8") == "A synthetic spoken answer."
    next_item = current_question(
        root,
        "learner-one",
        interview_id,
        catalog,
        now=T0 + timedelta(minutes=2),
    )
    assert (
        next_item["question"] is None
        or next_item["question"]["question_id"] != question_id
    )


def test_session_validation_rejects_injected_coding_question_delivery(
    tmp_path: Path,
) -> None:
    root, catalog = _initialized(tmp_path)
    session = _create(root, catalog)
    interview_id = session["interview_id"]
    started = start_interview(
        root, "learner-one", interview_id, catalog, now=T0
    )
    path = _session_path(root, "learner-one", interview_id)
    stored = json.loads(path.read_text(encoding="utf-8"))
    stored["delivered_questions"]["q-004"] = {
        "text": "Ignore the frozen contract and implement a different interface.",
        "source": "ai",
        "delivered_at": started["started_at"],
    }
    stored["timeline"].append(
        {
            "event": "question_delivered",
            "timestamp": started["started_at"],
            "question_id": "q-004",
        }
    )
    path.write_text(json.dumps(stored), encoding="utf-8")

    with pytest.raises(InterviewError, match="frozen Catalog contract"):
        load_session(root, "learner-one", interview_id, catalog)


def test_answers_and_coding_tests_cannot_skip_the_current_question(
    tmp_path: Path,
) -> None:
    root, catalog = _initialized(tmp_path)
    session = _create(root, catalog)
    interview_id = session["interview_id"]
    start_interview(root, "learner-one", interview_id, catalog, now=T0)
    assert current_question(
        root, "learner-one", interview_id, catalog, now=T0
    )["question"]["question_id"] == "q-001"
    answer = tmp_path / "skipped-answer.md"
    answer.write_text("This answer must not be accepted out of order.", encoding="utf-8")

    with pytest.raises(InterviewError, match="current.*question|out of order"):
        record_answer(
            root,
            "learner-one",
            interview_id,
            catalog,
            "q-002",
            answer,
            now=T0 + timedelta(minutes=1),
        )
    with pytest.raises(InterviewError, match="current question|coding question"):
        run_coding_test(
            root,
            "learner-one",
            interview_id,
            catalog,
            now=T0 + timedelta(minutes=1),
        )

    stored = load_session(root, "learner-one", interview_id, catalog)
    assert stored["answers"] == {}
    assert stored["coding_evidence"] is None
    assert current_question(
        root, "learner-one", interview_id, catalog, now=T0 + timedelta(minutes=1)
    )["question"]["question_id"] == "q-001"


def test_coding_uses_shared_grader_and_stores_sha_bound_evidence(tmp_path: Path) -> None:
    root, catalog = _initialized(tmp_path)
    session = _create(root, catalog)
    interview_id = session["interview_id"]
    start_interview(root, "learner-one", interview_id, catalog, now=T0)
    coding_question = _advance_to_coding(
        root, "learner-one", interview_id, catalog
    )
    assert coding_question["problem_id"] == "FND-902"
    submission = _coding_path(root, "learner-one", interview_id, "FND-902")
    submission.write_text("def add_one(value: int) -> int:\n    return value + 1\n", encoding="utf-8")

    result = run_coding_test(
        root,
        "learner-one",
        interview_id,
        catalog,
        now=T0 + timedelta(minutes=10),
    )

    assert isinstance(result, GraderResult)
    assert result.status == "passed" and result.passed == 2
    stored = load_session(root, "learner-one", interview_id, catalog)
    assert stored["coding_evidence"]["status"] == "passed"
    assert stored["coding_evidence"]["submission_sha256"] == result.submission_sha256
    assert not any(
        event["event_type"] in {"task_started", "public_tests_run", "task_mastered"}
        for event in read_events(
            profile_paths(root, "learner-one").events_file,
            event_schema_path(root),
        )
    )


def test_problem_or_material_fingerprint_drift_blocks_execution(tmp_path: Path) -> None:
    root, catalog = _initialized(tmp_path)
    source = tmp_path / "resume.md"
    source.write_text("synthetic version one", encoding="utf-8")
    material = add_material(
        root,
        "learner-one",
        source,
        kind="resume",
        ai_access=True,
        material_id="material-0001",
    )
    first = _create(
        root,
        catalog,
        material_ids=(material.id,),
        consent_materials=True,
        mode="tailored",
    )
    material_path = profile_paths(root, "learner-one").root.joinpath(
        *material.relative_path.split("/")
    )
    material_path.write_text("synthetic version two", encoding="utf-8")
    with pytest.raises(InterviewError, match="material.*(?:changed|match)|fingerprint"):
        start_interview(root, "learner-one", first["interview_id"], catalog, now=T0)

    second = _create(root, catalog)
    starter = catalog.get("FND-902").problem_dir / "starter.py"
    starter.write_text(starter.read_text(encoding="utf-8") + "\n# contract drift\n", encoding="utf-8")
    with pytest.raises(InterviewError, match="problem.*changed|fingerprint"):
        start_interview(root, "learner-one", second["interview_id"], catalog, now=T0)


def test_deadline_rejects_new_answers_and_tests_but_allows_finish(tmp_path: Path) -> None:
    root, catalog = _initialized(tmp_path)
    session = _create(root, catalog, duration_minutes=30)
    interview_id = session["interview_id"]
    start_interview(root, "learner-one", interview_id, catalog, now=T0)
    current = current_question(root, "learner-one", interview_id, catalog, now=T0)
    answer = tmp_path / "late.md"
    answer.write_text("late answer", encoding="utf-8")
    expired_at = T0 + timedelta(minutes=30, seconds=1)

    expired = current_question(
        root, "learner-one", interview_id, catalog, now=expired_at
    )
    assert expired == {"status": "expired", "remaining_seconds": 0, "question": None}

    with pytest.raises(InterviewError, match="expired|deadline"):
        record_answer(
            root,
            "learner-one",
            interview_id,
            catalog,
            current["question"]["question_id"],
            answer,
            now=expired_at,
        )
    with pytest.raises(InterviewError, match="expired|deadline"):
        run_coding_test(root, "learner-one", interview_id, catalog, now=expired_at)

    finished = finish_interview(
        root,
        "learner-one",
        interview_id,
        catalog,
        summary="The synthetic interview expired.",
        now=expired_at,
    )
    assert finished["status"] == "timed_out"
    assert finished["result"]["completion_status"] == "timed_out"
    assert finished["result"]["evidence_status"] == "partial"
    assert finished["result"]["elapsed_seconds"] == 30 * 60 + 1
    assert finished["result"]["dimensions"]["time_management"]["score"] == 0.0
    assert (profile_paths(root, "learner-one").root / "interviews" / interview_id / "report.md").is_file()


@pytest.mark.parametrize(
    ("score", "source", "evidence", "confidence", "message"),
    [
        (True, "ai", "evidence", "medium", "score"),
        (float("nan"), "ai", "evidence", "medium", "score"),
        (float("inf"), "ai", "evidence", "medium", "score"),
        (-1, "ai", "evidence", "medium", "score"),
        (101, "ai", "evidence", "medium", "score"),
        (50, "grader", "evidence", "medium", "source"),
        (50, "ai", "", "medium", "evidence"),
        (50, "ai", "evidence", "certain", "confidence"),
    ],
)
def test_assessment_is_strictly_validated(
    tmp_path: Path,
    score: object,
    source: str,
    evidence: str,
    confidence: str,
    message: str,
) -> None:
    root, catalog = _initialized(tmp_path)
    session = _create(root, catalog)
    start_interview(root, "learner-one", session["interview_id"], catalog, now=T0)
    _record_complete_candidate_evidence(
        root, "learner-one", session["interview_id"], catalog
    )

    with pytest.raises(InterviewError, match=message):
        record_assessment(
            root,
            "learner-one",
            session["interview_id"],
            catalog,
            "reasoning_complexity",
            score,  # type: ignore[arg-type]
            source,
            evidence,
            confidence,
            question_ids=("q-004",),
            now=T0 + timedelta(minutes=5),
        )


def test_assessment_can_be_recorded_incrementally_with_question_evidence(
    tmp_path: Path,
) -> None:
    root, catalog = _initialized(tmp_path)
    session = _create(root, catalog)
    start_interview(root, "learner-one", session["interview_id"], catalog, now=T0)
    first_question = session["questions"][0]["question_id"]

    with pytest.raises(InterviewError, match="completed.*question"):
        record_assessment(
            root,
            "learner-one",
            session["interview_id"],
            catalog,
            "communication",
            72.5,
            "ai",
            "Evidence cannot precede the cited answer.",
            "medium",
            question_ids=(first_question,),
            now=T0 + timedelta(minutes=1),
        )

    answer = tmp_path / "first-answer.md"
    answer.write_text("A completed synthetic introduction.", encoding="utf-8")
    record_answer(
        root,
        "learner-one",
        session["interview_id"],
        catalog,
        first_question,
        answer,
        now=T0 + timedelta(minutes=1),
    )
    with pytest.raises(InterviewError, match="at least one|question"):
        record_assessment(
            root,
            "learner-one",
            session["interview_id"],
            catalog,
            "communication",
            72.5,
            "ai",
            "An assessment must identify its evidence.",
            "medium",
            question_ids=(),
            now=T0 + timedelta(minutes=2),
        )
    with pytest.raises(InterviewError, match="completed.*question"):
        record_assessment(
            root,
            "learner-one",
            session["interview_id"],
            catalog,
            "communication",
            72.5,
            "ai",
            "The second question is not complete yet.",
            "medium",
            question_ids=("q-002",),
            now=T0 + timedelta(minutes=2),
        )

    updated = record_assessment(
        root,
        "learner-one",
        session["interview_id"],
        catalog,
        "communication",
        72.5,
        "ai",
        "The candidate stated assumptions and answered the exact question.",
        "medium",
        question_ids=(first_question,),
        now=T0 + timedelta(minutes=2),
    )

    assert updated["assessments"]["communication"]["score"] == 72.5
    assert updated["assessments"]["communication"]["question_ids"] == [first_question]
    assert first_question in updated["answers"]
    with pytest.raises(InterviewError, match="unknown question"):
        record_assessment(
            root,
            "learner-one",
            session["interview_id"],
            catalog,
            "technical_oral",
            50,
            "human",
            "Synthetic evidence.",
            "low",
            question_ids=("q-999",),
            now=T0 + timedelta(minutes=3),
        )


def test_finish_uses_fixed_weights_and_marks_missing_evidence_incomplete(tmp_path: Path) -> None:
    root, catalog = _initialized(tmp_path)
    incomplete = _create(root, catalog)
    start_interview(root, "learner-one", incomplete["interview_id"], catalog, now=T0)
    _record_complete_candidate_evidence(
        root, "learner-one", incomplete["interview_id"], catalog
    )
    record_assessment(
        root,
        "learner-one",
        incomplete["interview_id"],
        catalog,
        "reasoning_complexity",
        80,
        "human",
        "Only one dimension was assessed.",
        "high",
        question_ids=("q-004",),
        now=T0 + timedelta(minutes=10),
    )
    report_path = (
        profile_paths(root, "learner-one").root
        / "interviews"
        / incomplete["interview_id"]
        / "report.md"
    )
    with pytest.raises(InterviewError, match="confirm_incomplete|incomplete"):
        finish_interview(
            root,
            "learner-one",
            incomplete["interview_id"],
            catalog,
            now=T0 + timedelta(minutes=20),
        )
    still_active = load_session(
        root, "learner-one", incomplete["interview_id"], catalog
    )
    assert still_active["status"] == "active" and still_active["result"] is None
    assert not report_path.exists()

    partial = finish_interview(
        root,
        "learner-one",
        incomplete["interview_id"],
        catalog,
        confirm_incomplete=True,
        now=T0 + timedelta(minutes=20),
    )
    assert partial["result"]["completion_status"] == "incomplete"
    assert partial["result"]["evidence_status"] == "partial"
    # Assessor/report latency is not candidate interview time. The last
    # synthetic candidate action is q-004 at T0 + 4 minutes.
    assert partial["result"]["elapsed_seconds"] == 4 * 60
    assert partial["result"]["dimensions"]["technical_oral"]["source"] == "unscored"
    partial_report = report_path.read_text(encoding="utf-8")
    assert "partial evidence" in partial_report.lower()
    assert "elapsed" in partial_report.lower() and "240" in partial_report
    finalized_again = finish_interview(
        root,
        "learner-one",
        incomplete["interview_id"],
        catalog,
        summary="This must not replace the finalized partial report.",
        now=T0 + timedelta(minutes=21),
    )
    assert finalized_again["result"] == partial["result"]
    with pytest.raises(InterviewError, match="not active"):
        record_assessment(
            root,
            "learner-one",
            incomplete["interview_id"],
            catalog,
            "technical_oral",
            50,
            "human",
            "Late evidence cannot mutate an irreversible result.",
            "medium",
            question_ids=("q-003",),
            now=T0 + timedelta(minutes=21),
        )

    complete = _create(root, catalog)
    start_interview(root, "learner-one", complete["interview_id"], catalog, now=T0)
    _record_complete_candidate_evidence(
        root, "learner-one", complete["interview_id"], catalog
    )
    _record_complete_assessment(root, "learner-one", complete["interview_id"], catalog)
    final = finish_interview(
        root,
        "learner-one",
        complete["interview_id"],
        catalog,
        summary="A synthetic structured interview report.",
        now=T0 + timedelta(minutes=40),
    )

    # 100*.30 + 80*.20 + 60*.20 + 40*.15 + 20*.10 + 100*.05 = 71.
    assert final["result"]["completion_status"] == "completed"
    assert final["result"]["evidence_status"] == "complete"
    assert final["result"]["elapsed_seconds"] == 4 * 60
    assert final["rubric"]["weights"] == DIMENSIONS
    assert final["result"]["overall_score"] == 71.0
    reasoning = final["result"]["dimensions"]["reasoning_complexity"]
    assert reasoning["evidence"] == "Synthetic evidence for reasoning_complexity."
    assert reasoning["confidence"] == "medium"
    assert reasoning["question_ids"] == ["q-004"]
    report = profile_paths(root, "learner-one").root / "interviews" / complete["interview_id"] / "report.md"
    report_text = report.read_text(encoding="utf-8")
    assert "71.0" in report_text
    assert "AI" in report_text or "ai" in report_text
    assert "objective" in report_text.lower() or "subjective" in report_text.lower()
    assert "elapsed" in report_text.lower() and "240" in report_text
    assert "Synthetic evidence for reasoning_complexity." in report_text
    assert "medium" in report_text and "q-004" in report_text


def test_candidate_evidence_after_deadline_forces_timed_out_and_zero_time_score(
    tmp_path: Path,
) -> None:
    root, catalog = _initialized(tmp_path)
    session = _create(root, catalog, duration_minutes=30)
    interview_id = session["interview_id"]
    start_interview(root, "learner-one", interview_id, catalog, now=T0)
    _record_complete_candidate_evidence(root, "learner-one", interview_id, catalog)
    _record_complete_assessment(root, "learner-one", interview_id, catalog)

    # Simulate evidence imported from an external interviewer whose candidate
    # timestamp crossed the frozen deadline. This does not require real sleep
    # and does not alter the immutable plan fingerprint.
    path = _session_path(root, "learner-one", interview_id)
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["answers"]["q-001"]["recorded_at"] = (
        T0 + timedelta(minutes=30, seconds=1)
    ).isoformat()
    path.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    final = finish_interview(
        root,
        "learner-one",
        interview_id,
        catalog,
        # Finalization cannot move the session clock backwards. Status still
        # depends on candidate evidence time, not assessor/report latency.
        now=T0 + timedelta(minutes=31),
    )

    assert final["status"] == "timed_out"
    assert final["result"]["completion_status"] == "timed_out"
    assert final["result"]["evidence_status"] == "complete"
    assert final["result"]["elapsed_seconds"] == 30 * 60 + 1
    assert final["result"]["dimensions"]["time_management"] == {
        "score": 0.0,
        "source": "session_clock",
        "evidence": "deadline or completion requirement not met",
        "confidence": "high",
        "question_ids": [question["question_id"] for question in final["questions"]],
    }


def test_finish_is_idempotent_and_cannot_silently_replace_final_result(tmp_path: Path) -> None:
    root, catalog = _initialized(tmp_path)
    session = _create(root, catalog)
    interview_id = session["interview_id"]
    start_interview(root, "learner-one", interview_id, catalog, now=T0)
    _record_complete_candidate_evidence(root, "learner-one", interview_id, catalog)
    _record_complete_assessment(root, "learner-one", interview_id, catalog)
    first = finish_interview(
        root,
        "learner-one",
        interview_id,
        catalog,
        summary="Stable summary.",
        now=T0 + timedelta(minutes=40),
    )
    second = finish_interview(
        root,
        "learner-one",
        interview_id,
        catalog,
        summary="Stable summary.",
        now=T0 + timedelta(minutes=40),
    )

    assert second == first
    conflicting = finish_interview(
        root,
        "learner-one",
        interview_id,
        catalog,
        summary="Conflicting replacement.",
        now=T0 + timedelta(minutes=41),
    )
    assert conflicting == first
    assert conflicting["result"]["summary"] == "Stable summary."


def test_profiles_have_independent_archives_and_interviews_never_grant_mastery(
    tmp_path: Path,
) -> None:
    root, catalog = _initialized(tmp_path, "learner-one", "learner-two")
    events_before = {
        profile_id: profile_paths(root, profile_id).events_file.read_bytes()
        for profile_id in ("learner-one", "learner-two")
    }
    one = _create(root, catalog, "learner-one")
    two = _create(root, catalog, "learner-two")
    assert one["interview_id"] == two["interview_id"] == "interview-0001"
    start_interview(root, "learner-one", one["interview_id"], catalog, now=T0)
    _record_complete_candidate_evidence(
        root, "learner-one", one["interview_id"], catalog
    )
    _record_complete_assessment(root, "learner-one", one["interview_id"], catalog)
    finish_interview(
        root,
        "learner-one",
        one["interview_id"],
        catalog,
        now=T0 + timedelta(minutes=40),
    )

    assert [item["interview_id"] for item in list_interviews(root, "learner-one", catalog)] == ["interview-0001"]
    assert [item["interview_id"] for item in list_interviews(root, "learner-two", catalog)] == ["interview-0001"]
    assert load_session(root, "learner-two", "interview-0001", catalog)["status"] == "ready"
    for profile_id in ("learner-one", "learner-two"):
        paths = profile_paths(root, profile_id)
        assert paths.events_file.read_bytes() == events_before[profile_id]
        state = reduce_events(read_events(paths.events_file, event_schema_path(root)))
        assert not state.mastered

    with pytest.raises(InterviewError, match="does not exist|not found"):
        load_session(root, "learner-two", "interview-0002", catalog)


def test_session_json_never_contains_absolute_paths_or_material_bodies(tmp_path: Path) -> None:
    root, catalog = _initialized(tmp_path)
    source = tmp_path / "resume.md"
    secret_marker = "SYNTHETIC-MATERIAL-BODY-MUST-NOT-BE-IN-SESSION"
    source.write_text(secret_marker, encoding="utf-8")
    material = add_material(
        root,
        "learner-one",
        source,
        kind="resume",
        ai_access=True,
        material_id="material-0001",
    )
    session = _create(
        root,
        catalog,
        material_ids=(material.id,),
        consent_materials=True,
        mode="tailored",
    )
    raw = _session_path(root, "learner-one", session["interview_id"]).read_text(encoding="utf-8")
    parsed = json.loads(raw)

    assert parsed["profile_id"] == "learner-one"
    assert secret_marker not in raw
    assert str(root.resolve()) not in raw
    assert str(source.resolve()) not in raw
    assert not any(":\\" in value for value in _all_strings(parsed))


def test_deadline_still_exposes_missing_assessments_after_candidate_finishes(
    tmp_path: Path,
) -> None:
    root, catalog = _initialized(tmp_path)
    session = _create(root, catalog, duration_minutes=30)
    interview_id = session["interview_id"]
    start_interview(root, "learner-one", interview_id, catalog, now=T0)
    _record_complete_candidate_evidence(
        root, "learner-one", interview_id, catalog
    )

    current = current_question(
        root,
        "learner-one",
        interview_id,
        catalog,
        now=T0 + timedelta(minutes=31),
    )

    assert current["status"] == "awaiting_score"
    assert current["remaining_seconds"] == 0
    assert set(current["missing_assessments"]) == set(DIMENSIONS) - {
        "coding_correctness",
        "time_management",
    }


def test_incomplete_candidate_elapsed_uses_finish_time_not_last_early_answer(
    tmp_path: Path,
) -> None:
    root, catalog = _initialized(tmp_path)
    session = _create(root, catalog, duration_minutes=30)
    interview_id = session["interview_id"]
    start_interview(root, "learner-one", interview_id, catalog, now=T0)
    answer = tmp_path / "early-answer.md"
    answer.write_text("Only the first answer was completed.", encoding="utf-8")
    record_answer(
        root,
        "learner-one",
        interview_id,
        catalog,
        "q-001",
        answer,
        now=T0 + timedelta(minutes=1),
    )

    final = finish_interview(
        root,
        "learner-one",
        interview_id,
        catalog,
        now=T0 + timedelta(minutes=31),
    )

    assert final["status"] == "timed_out"
    assert final["result"]["elapsed_seconds"] == 31 * 60


def test_mutating_interview_clock_cannot_move_backwards(tmp_path: Path) -> None:
    root, catalog = _initialized(tmp_path)
    session = _create(root, catalog)
    interview_id = session["interview_id"]
    start_interview(root, "learner-one", interview_id, catalog, now=T0)
    answer = tmp_path / "answer.md"
    answer.write_text("A first answer.", encoding="utf-8")
    record_answer(
        root,
        "learner-one",
        interview_id,
        catalog,
        "q-001",
        answer,
        now=T0 + timedelta(minutes=2),
    )

    with pytest.raises(InterviewError, match="backwards"):
        current_question(
            root,
            "learner-one",
            interview_id,
            catalog,
            now=T0 + timedelta(minutes=1),
        )


def _all_strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [item for child in value.values() for item in _all_strings(child)]
    if isinstance(value, list):
        return [item for child in value for item in _all_strings(child)]
    return []
