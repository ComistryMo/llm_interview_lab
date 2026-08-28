from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

import pytest

import llm_interview_lab.context as context_module
from llm_interview_lab.catalog import Catalog, Problem, Track
from llm_interview_lab.context import (
    MAX_SERIALIZED_CONTEXT_BYTES,
    ContextError,
    build_interview_context,
    build_practice_context,
    serialize_context,
)
from llm_interview_lab.events import append_event
from llm_interview_lab.interviews import create_interview, record_answer, start_interview
from llm_interview_lab.materials import add_material
from llm_interview_lab.submissions import inspect_submission
from llm_interview_lab.workspace import (
    event_schema_path,
    init_profile,
    profile_paths,
    start_problem,
    update_career_intent,
)


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        "[project]\nname = 'ai-context-fixture'\nversion = '0'\n",
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

    (root / "coach" / "prompts").mkdir(parents=True)
    policy_files = {
        "AGENTS.md": "# Fixture agent policy\nDo not reveal learner answers.\n",
        "coach/POLICY.md": "# Fixture coach policy\nUse only the explicit allowlist.\n",
        "coach/prompts/teacher.md": "# Teacher\nGive only the requested hint level.\n",
        "coach/prompts/reviewer.md": "# Reviewer\nReview but do not edit.\n",
        "coach/prompts/interviewer.md": "# Interviewer\nAsk only the current question.\n",
    }
    for relative, content in policy_files.items():
        path = root.joinpath(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return root


def _problem(
    root: Path,
    problem_id: str,
    *,
    prerequisites: tuple[str, ...] = (),
    marker: str = "CURRENT-TASK-MARKER",
) -> Problem:
    problem_dir = root / "synthetic-problems" / problem_id
    problem_dir.mkdir(parents=True)
    (problem_dir / "task.md").write_text(
        f"# Synthetic task {problem_id}\n\n{marker}\n",
        encoding="utf-8",
    )
    (problem_dir / "starter.py").write_text(
        "def add_one(value: int) -> int:\n    raise NotImplementedError\n",
        encoding="utf-8",
    )
    (problem_dir / "test_public.py").write_text(
        "# PUBLIC-TEST-SECRET\n"
        "def test_add_one(submission):\n    assert submission.add_one(1) == 2\n",
        encoding="utf-8",
    )
    (problem_dir / "hints.md").write_text(
        "# Graded hints\n\n"
        "## H1 — Concept\nH1-ONLY-MARKER: inspect the return contract.\n\n"
        "## H2 — Structure\nH2-ONLY-MARKER: split validation from computation.\n\n"
        "## H3 — Pseudocode\nH3-ONLY-MARKER: validate, calculate, then return.\n",
        encoding="utf-8",
    )
    raw: dict[str, Any] = {
        "id": problem_id,
        "title": f"Synthetic {problem_id}",
        "status": "ready",
        "domain": "foundation",
        "tracks": ["ai_foundation"],
        "tier": "core",
        "difficulty": {"concept": 1, "coding": 1, "debugging": 1},
        "prerequisites": list(prerequisites),
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
                "description": "Exact values for a synthetic infrastructure task.",
            },
            "oral_questions": [
                "ORAL-CURRENT: explain the contract.",
                "ORAL-FUTURE: explain a transfer case.",
                "Which invalid inputs matter?",
                "How would you test this?",
            ],
        },
        "variant_axes": ["integer_value"],
        "invariants": ["result_is_incremented"],
        "common_bugs": ["returns_input"],
        "retention": {
            "d2": "not part of this context fixture",
            "d7": "not part of this context fixture",
        },
        "sources": [
            {"type": "documentation", "title": "Synthetic infrastructure fixture"}
        ],
    }
    return Problem(
        problem_id,
        raw["title"],
        "ready",
        prerequisites,
        problem_dir,
        "add_one",
        "pytest",
        problem_dir / "test_public.py",
        "fixture_expected",
        raw,
        2_000,
        32,
    )


def _initialized(
    tmp_path: Path, *profile_ids: str
) -> tuple[Path, Catalog]:
    root = _repository(tmp_path)
    problems = {
        "FND-901": _problem(root, "FND-901"),
        "FND-902": _problem(root, "FND-902", marker="FUTURE-TASK-SECRET"),
        "FND-903": _problem(root, "FND-903"),
        "FND-904": _problem(root, "FND-904"),
        "FND-905": _problem(root, "FND-905"),
    }
    catalog = Catalog(
        problems=problems,
        order=tuple(problems),
        tracks={
            "ai_foundation": Track(
                "ai_foundation", "AI Foundation", "Synthetic context track"
            )
        },
        quests={},
        capstones={},
    )
    for profile_id in profile_ids or ("learner-one",):
        init_profile(root, profile_id, ("ai_foundation",))
    return root, catalog


def _profile_snapshot(root: Path, profile_id: str) -> dict[str, str]:
    profile_root = profile_paths(root, profile_id).root
    return {
        path.relative_to(profile_root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(profile_root.rglob("*"))
        if path.is_file()
    }


def _all_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [item for child in value.values() for item in _all_strings(child)]
    if isinstance(value, (list, tuple)):
        return [item for child in value for item in _all_strings(child)]
    return []


def _record_public_test_failure(
    root: Path,
    catalog: Catalog,
    profile_id: str,
    problem_id: str,
    *,
    failed_at: datetime,
    recovered: bool = False,
) -> None:
    # Build explicit historical fixtures without weakening the production
    # single-active-task guard. Event streams can legitimately predate that guard.
    problem = catalog.get(problem_id)
    assert problem.problem_dir is not None
    attempt_id = "attempt-0001"
    submission_path = (
        profile_paths(root, profile_id).submissions_root
        / problem_id
        / attempt_id
        / "submission.py"
    )
    submission_path.parent.mkdir(parents=True)
    starter_bytes = (problem.problem_dir / "starter.py").read_bytes()
    submission_path.write_bytes(starter_bytes)
    inspected = inspect_submission(
        submission_path, profile_paths(root, profile_id).submissions_root
    )
    events_file = profile_paths(root, profile_id).events_file
    schema = event_schema_path(root)
    append_event(
        events_file,
        schema,
        profile_id=profile_id,
        event_type="task_started",
        problem_id=problem_id,
        attempt_id=attempt_id,
        payload={
            "submission_relpath": submission_path.relative_to(root).as_posix(),
            "starter_sha256": hashlib.sha256(starter_bytes).hexdigest(),
        },
        timestamp=failed_at - timedelta(seconds=1),
    )
    failed_payload = {
        "submission_sha256": inspected.sha256,
        "exit_code": 1,
        "status": "failed",
        "passed": 0,
        "failed": 1,
        "duration_ms": 10,
        "output_truncated": False,
    }
    append_event(
        events_file,
        schema,
        profile_id=profile_id,
        event_type="public_tests_run",
        problem_id=problem_id,
        attempt_id=attempt_id,
        payload=failed_payload,
        timestamp=failed_at,
    )
    if recovered:
        append_event(
            events_file,
            schema,
            profile_id=profile_id,
            event_type="public_tests_run",
            problem_id=problem_id,
            attempt_id=attempt_id,
            payload={
                **failed_payload,
                "exit_code": 0,
                "status": "passed",
                "passed": 1,
                "failed": 0,
            },
            timestamp=failed_at + timedelta(days=1),
        )
    append_event(
        events_file,
        schema,
        profile_id=profile_id,
        event_type="task_implemented",
        problem_id=problem_id,
        attempt_id=attempt_id,
        payload={"submission_sha256": inspected.sha256},
        timestamp=failed_at + timedelta(days=2),
    )


def test_teacher_context_slices_one_hint_and_hides_future_assets(tmp_path: Path) -> None:
    root, catalog = _initialized(tmp_path)
    start_problem(root, "learner-one", catalog.get("FND-901"))

    context = build_practice_context(root, catalog, "learner-one", "teacher", "H2")
    rendered = serialize_context(context)

    assert context["scope"] == "practice"
    assert context["mode"] == "TEACHER"
    assert context["current"]["problem"]["id"] == "FND-901"
    assert context["current"]["help"]["level"] == "H2"
    assert "H2-ONLY-MARKER" in rendered
    assert "H1-ONLY-MARKER" not in rendered
    assert "H3-ONLY-MARKER" not in rendered
    assert "FUTURE-TASK-SECRET" not in rendered
    assert "PUBLIC-TEST-SECRET" not in rendered
    assert len(context["unlocks"]) == 3
    assert len(rendered.encode("utf-8")) <= MAX_SERIALIZED_CONTEXT_BYTES

    with pytest.raises(ContextError, match="requires one explicit"):
        build_practice_context(root, catalog, "learner-one", "teacher")
    for forbidden in ("H4", "H5"):
        with pytest.raises(ContextError, match="only H1, H2, or H3"):
            build_practice_context(
                root, catalog, "learner-one", "teacher", forbidden
            )


def test_teacher_context_rejects_a_link_or_reparse_hint_asset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, catalog = _initialized(tmp_path)
    start_problem(root, "learner-one", catalog.get("FND-901"))
    protected = (catalog.get("FND-901").problem_dir / "hints.md").resolve()
    original = context_module._is_obvious_link
    monkeypatch.setattr(
        context_module,
        "_is_obvious_link",
        lambda path: path.resolve() == protected or original(path),
    )

    with pytest.raises(ContextError, match="symlink or reparse point"):
        build_practice_context(root, catalog, "learner-one", "teacher", "H1")


def test_context_does_not_follow_a_policy_symlink_into_a_profile(
    tmp_path: Path,
) -> None:
    root, catalog = _initialized(tmp_path)
    secret = profile_paths(root, "learner-one").root / "cache/private-note.md"
    secret.write_text("PRIVATE-PROFILE-BODY", encoding="utf-8")
    policy = root / "coach/POLICY.md"
    policy.unlink()
    try:
        policy.symlink_to(secret)
    except OSError as error:
        pytest.skip(f"symlink creation is unavailable on this platform: {error}")

    with pytest.raises(ContextError, match="symlink or reparse point"):
        build_practice_context(root, catalog, "learner-one", "coach")


def test_reviewer_context_exposes_current_evidence_without_source_or_events(
    tmp_path: Path,
) -> None:
    root, catalog = _initialized(tmp_path)
    started = start_problem(root, "learner-one", catalog.get("FND-901"))
    started.submission_path.write_text(
        "# SUBMISSION-BODY-SECRET\ndef add_one(value):\n    return value + 1\n",
        encoding="utf-8",
    )
    inspected = inspect_submission(
        started.submission_path, profile_paths(root, "learner-one").submissions_root
    )
    append_event(
        profile_paths(root, "learner-one").events_file,
        event_schema_path(root),
        profile_id="learner-one",
        event_type="public_tests_run",
        problem_id="FND-901",
        attempt_id=started.attempt_id,
        payload={
            "submission_sha256": inspected.sha256,
            "exit_code": 0,
            "status": "passed",
            "passed": 1,
            "failed": 0,
            "duration_ms": 12,
            "output_truncated": False,
        },
    )

    context = build_practice_context(root, catalog, "learner-one", "reviewer")
    rendered = serialize_context(context)

    assert context["current"]["submission"]["sha256"] == inspected.sha256
    assert context["current"]["last_public_test"] == {
        "submission_sha256": inspected.sha256,
        "exit_code": 0,
        "status": "passed",
        "passed": 1,
        "failed": 0,
        "duration_ms": 12,
        "output_truncated": False,
        "current_submission": True,
    }
    assert "SUBMISSION-BODY-SECRET" not in rendered
    assert "PUBLIC-TEST-SECRET" not in rendered
    assert '"event_type"' not in rendered
    assert "events.jsonl" not in rendered
    assert context["read_allowlist"][-1]["purpose"] == "current_submission"


def test_context_is_deterministic_read_only_repo_relative_and_profile_isolated(
    tmp_path: Path,
) -> None:
    root, catalog = _initialized(tmp_path, "learner-one", "learner-two")
    start_problem(root, "learner-one", catalog.get("FND-901"))
    other_secret = profile_paths(root, "learner-two").root / "reviews" / "private.md"
    other_secret.write_text("OTHER-PROFILE-SECRET", encoding="utf-8")
    before = _profile_snapshot(root, "learner-one")

    first = build_practice_context(root, catalog, "learner-one", "coach")
    second = build_practice_context(root, catalog, "learner-one", "coach")

    assert first == second
    assert serialize_context(first) == serialize_context(second)
    assert before == _profile_snapshot(root, "learner-one")
    rendered = serialize_context(first)
    assert str(root) not in rendered
    assert "OTHER-PROFILE-SECRET" not in rendered
    assert all("\\" not in value for value in _all_strings(first) if "/" in value)
    assert first["state_fingerprint"] != "0" * 64
    for ref in first["policy_refs"].values():
        if ref is not None:
            assert len(ref["sha256"]) == 64
            assert not Path(ref["path"]).is_absolute()


def test_coach_context_has_bounded_career_intent_and_derived_mistakes_only(
    tmp_path: Path,
) -> None:
    root, catalog = _initialized(tmp_path, "learner-one", "learner-two")
    update_career_intent(
        root,
        "learner-one",
        {
            "target_job_titles": ["VLM", "LLM", "Agent", "Systems"],
            "employment_stage": "internship",
            "preferred_locations": ["Hong Kong", "Shenzhen", "Beijing", "Shanghai"],
            "interview_languages": ["zh-CN", "en", "ja", "de"],
            "priorities": ["post-training", "evaluation", "alignment", "inference"],
        },
    )
    source = root / "private-career-material.md"
    source.write_text("MATERIAL-BODY-SECRET", encoding="utf-8")
    add_material(
        root,
        "learner-one",
        source,
        kind="resume",
        material_id="private-resume",
        ai_access=True,
    )
    for index, problem_id in enumerate(
        ("FND-901", "FND-902", "FND-903", "FND-904"), start=1
    ):
        _record_public_test_failure(
            root,
            catalog,
            "learner-one",
            problem_id,
            # Deliberately reverse timestamps: physical event order, not the
            # clock value, defines which failures are recent.
            failed_at=datetime(2030, 1, 5 - index, tzinfo=timezone.utc),
            recovered=problem_id == "FND-904",
        )
    update_career_intent(
        root,
        "learner-two",
        {
            "target_job_titles": ["OTHER-PROFILE-SECRET"],
            "employment_stage": "experienced",
            "preferred_locations": [],
            "interview_languages": ["en"],
            "priorities": [],
        },
    )
    before = _profile_snapshot(root, "learner-one")

    first = build_practice_context(root, catalog, "learner-one", "coach")
    second = build_practice_context(root, catalog, "learner-one", "coach")
    rendered = serialize_context(first)

    assert first == second
    assert first["personalization"]["career_intent"] == {
        "target_job_titles": ["VLM", "LLM", "Agent"],
        "employment_stage": "internship",
        "preferred_locations": ["Hong Kong", "Shenzhen", "Beijing"],
        "interview_languages": ["zh-CN", "en", "ja"],
        "priorities": ["post-training", "evaluation", "alignment"],
        "truncated": True,
    }
    assert [
        item["problem_id"]
        for item in first["personalization"]["recent_mistakes"]
    ] == ["FND-903", "FND-902", "FND-901"]
    assert all(
        item["current_evidence_recovered"] is False
        for item in first["personalization"]["recent_mistakes"]
    )
    assert all(
        set(item)
        == {
            "problem_id",
            "failure_count",
            "last_failure_kind",
            "last_failed_at",
            "current_evidence_recovered",
        }
        for item in first["personalization"]["recent_mistakes"]
    )
    assert len(rendered.encode("utf-8")) <= MAX_SERIALIZED_CONTEXT_BYTES
    assert "MATERIAL-BODY-SECRET" not in rendered
    assert "OTHER-PROFILE-SECRET" not in rendered
    assert '"event_type"' not in rendered
    assert "events.jsonl" not in rendered
    assert "submission.py" not in rendered
    assert str(root) not in rendered
    assert before == _profile_snapshot(root, "learner-one")


def test_career_and_mistake_personalization_is_coach_only(tmp_path: Path) -> None:
    root, catalog = _initialized(tmp_path)
    update_career_intent(
        root,
        "learner-one",
        {
            "target_job_titles": ["Private target"],
            "employment_stage": "new_grad",
            "preferred_locations": [],
            "interview_languages": ["zh-CN"],
            "priorities": [],
        },
    )
    _record_public_test_failure(
        root,
        catalog,
        "learner-one",
        "FND-901",
        failed_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
    )

    teacher = build_practice_context(
        root, catalog, "learner-one", "teacher", "H1"
    )
    reviewer = build_practice_context(root, catalog, "learner-one", "reviewer")

    assert "personalization" not in teacher
    assert "personalization" not in reviewer
    assert "Private target" not in serialize_context(teacher)
    assert "Private target" not in serialize_context(reviewer)


def test_maximum_valid_career_intent_is_capped_below_context_budget(
    tmp_path: Path,
) -> None:
    root, catalog = _initialized(tmp_path)
    update_career_intent(
        root,
        "learner-one",
        {
            "target_job_titles": [
                f"{index:02d}" + "t" * 98 for index in range(10)
            ],
            "employment_stage": "flexible",
            "preferred_locations": [
                f"{index:02d}" + "l" * 98 for index in range(10)
            ],
            "interview_languages": ["zh-CN", "en", "fr", "de", "ja"],
            "priorities": [
                f"{index:02d}" + "p" * 118 for index in range(10)
            ],
        },
    )

    context = build_practice_context(root, catalog, "learner-one", "coach")
    intent = context["personalization"]["career_intent"]
    rendered = serialize_context(context)

    assert intent["truncated"] is True
    for field in (
        "target_job_titles",
        "preferred_locations",
        "interview_languages",
        "priorities",
    ):
        assert len(intent[field]) == 3
    assert len(rendered.encode("utf-8")) <= MAX_SERIALIZED_CONTEXT_BYTES


def test_interview_context_discloses_only_current_prompt_and_consented_reference(
    tmp_path: Path,
) -> None:
    root, catalog = _initialized(tmp_path)
    source = root / "synthetic-resume.md"
    source.write_text("MATERIAL-BODY-SECRET", encoding="utf-8")
    material = add_material(
        root,
        "learner-one",
        source,
        kind="resume",
        title="Synthetic resume",
        ai_access=True,
        material_id="resume-main",
    )
    created = create_interview(
        root,
        "learner-one",
        catalog,
        difficulty="easy",
        duration_minutes=30,
        track_id="ai_foundation",
        mode="tailored",
        material_ids=(material.id,),
        consent_materials=True,
        problem_id="FND-901",
        focus="ownership evidence",
        seed=7,
    )
    interview_id = created["interview_id"]

    ready = build_interview_context(root, catalog, "learner-one", interview_id)
    ready_text = serialize_context(ready)
    assert ready["current"]["status"] == "ready"
    assert all("prompt" not in item for item in ready["current"]["question_plan"])
    assert "Give a concise introduction" not in ready_text
    assert "MATERIAL-BODY-SECRET" not in ready_text
    assert ready["read_allowlist"] == []

    start_interview(root, "learner-one", interview_id, catalog)
    introduction = build_interview_context(root, catalog, "learner-one", interview_id)
    introduction_text = serialize_context(introduction)
    assert introduction["current"]["question"]["question_id"] == "q-001"
    assert introduction["current"]["question"]["prompt_source"] == "fixed"
    assert "interview ask" in introduction["commands"]["deliver_question"]
    assert "Give a concise introduction" in introduction_text
    assert "ownership evidence" not in introduction_text
    assert "ORAL-CURRENT" not in introduction_text
    assert introduction["read_allowlist"] == []

    answer = root / "answer.md"
    answer.write_text("A synthetic introduction.", encoding="utf-8")
    record_answer(
        root,
        "learner-one",
        interview_id,
        catalog,
        "q-001",
        answer,
    )
    experience = build_interview_context(root, catalog, "learner-one", interview_id)
    experience_text = serialize_context(experience)
    assert experience["current"]["question"]["question_id"] == "q-002"
    assert "ownership evidence" in experience_text
    assert "Give a concise introduction" not in experience_text
    assert "ORAL-CURRENT" not in experience_text
    assert "MATERIAL-BODY-SECRET" not in experience_text
    assert experience["read_allowlist"] == [
        {
            "path": (
                "workspace/profiles/learner-one/"
                f"{material.relative_path}"
            ),
            "purpose": "consented_interview_material",
            "sha256": material.sha256,
            "material_id": material.id,
            "allowed_use": "mock_interview",
        }
    ]


def test_interview_context_is_profile_scoped_and_read_only(tmp_path: Path) -> None:
    root, catalog = _initialized(tmp_path, "learner-one", "learner-two")
    first_session = create_interview(
        root,
        "learner-one",
        catalog,
        difficulty="easy",
        duration_minutes=30,
        track_id="ai_foundation",
        problem_id="FND-901",
        seed=1,
    )
    second_session = create_interview(
        root,
        "learner-two",
        catalog,
        difficulty="easy",
        duration_minutes=30,
        track_id="ai_foundation",
        problem_id="FND-902",
        seed=2,
    )
    assert first_session["interview_id"] == second_session["interview_id"]
    before = _profile_snapshot(root, "learner-one")

    first = build_interview_context(
        root, catalog, "learner-one", first_session["interview_id"]
    )
    again = build_interview_context(
        root, catalog, "learner-one", first_session["interview_id"]
    )

    assert first == again
    assert first["current"]["selected_problem"]["problem_id"] == "FND-901"
    assert "FND-902" not in serialize_context(first)
    assert before == _profile_snapshot(root, "learner-one")


def test_serialize_context_has_a_hard_byte_limit() -> None:
    small = {"schema_version": 1, "value": "ok"}
    assert serialize_context(small).endswith("\n")

    with pytest.raises(ContextError, match="8192-byte limit"):
        serialize_context({"value": "x" * MAX_SERIALIZED_CONTEXT_BYTES})

    with pytest.raises(ContextError, match="JSON-serializable"):
        serialize_context({"value": object()})
