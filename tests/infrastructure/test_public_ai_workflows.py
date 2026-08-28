from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

import pytest

import llm_interview_lab.cli as cli_module
from llm_interview_lab.catalog import Catalog, Problem, Quest, Track
from llm_interview_lab.events import append_event
from llm_interview_lab.interviews import interview_candidates
from llm_interview_lab.materials import add_material
from llm_interview_lab.submissions import inspect_submission
from llm_interview_lab.workspace import (
    event_schema_path,
    profile_paths,
    start_problem,
)


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILE_ID = "synthetic-candidate"


def _problem(
    root: Path,
    problem_id: str,
    *,
    track: str = "llm_algorithm",
    coding_difficulty: int = 3,
    validation: str = "oracle",
    marker: str = "SYNTHETIC CURRENT CONTRACT",
) -> Problem:
    problem_dir = root / "synthetic-problems" / problem_id
    problem_dir.mkdir(parents=True)
    (problem_dir / "task.md").write_text(
        f"# Synthetic increment\n\n{marker}\n",
        encoding="utf-8",
    )
    (problem_dir / "starter.py").write_text(
        "def increment(value: int) -> int:\n    raise NotImplementedError\n",
        encoding="utf-8",
    )
    (problem_dir / "test_public.py").write_text(
        "# PUBLIC-TEST-BODY-MUST-STAY-PRIVATE\n"
        "def test_positive(submission):\n"
        "    assert submission.increment(4) == 5\n\n"
        "def test_negative(submission):\n"
        "    assert submission.increment(-3) == -2\n",
        encoding="utf-8",
    )
    (problem_dir / "hints.md").write_text(
        "## H1 — Concept\nH1-CURRENT-ONLY\n\n"
        "## H2 — Structure\nH2-NOT-REQUESTED\n\n"
        "## H3 — Pseudocode\nH3-NOT-REQUESTED\n",
        encoding="utf-8",
    )
    raw: dict[str, Any] = {
        "id": problem_id,
        "title": f"Synthetic {problem_id}",
        "status": "ready",
        "domain": "foundation",
        "tracks": [track],
        "tier": "core",
        "difficulty": {
            "concept": coding_difficulty,
            "coding": coding_difficulty,
            "debugging": coding_difficulty,
        },
        "prerequisites": [],
        "skills": ["python.functions"],
        "validation": {"level": validation, "field_runs": 0},
        "assets": {"problem_dir": problem_dir.relative_to(root).as_posix()},
        "interface": {
            "language": "python",
            "framework": "stdlib",
            "symbol": "increment",
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
                "target": "synthetic infrastructure fixture",
                "description": "Exact outputs for a tiny synthetic function.",
            },
            "oral_questions": [
                "State the synthetic function contract.",
                "Explain the time and space complexity.",
                "Name one invalid-input policy.",
                "Describe two independent tests.",
            ],
        },
        "variant_axes": ["integer_sign"],
        "invariants": ["output_is_one_greater"],
        "common_bugs": ["returns_input"],
        "retention": {
            "d2": "not used by this infrastructure fixture",
            "d7": "not used by this infrastructure fixture",
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
        "increment",
        "pytest",
        problem_dir / "test_public.py",
        "fixture_expected",
        raw,
        2_000,
        32,
    )


def _repository(tmp_path: Path) -> tuple[Path, Catalog]:
    root = tmp_path / "repository"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        "[project]\nname = 'public-ai-workflow-fixture'\nversion = '0'\n",
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
    for relative, content in {
        "AGENTS.md": "# Synthetic agent policy\nRead only the explicit context.\n",
        "coach/POLICY.md": "# Synthetic coach policy\nNever grant mastery.\n",
        "coach/prompts/teacher.md": "# Teacher\nUse the selected hint only.\n",
        "coach/prompts/reviewer.md": "# Reviewer\nDo not edit submissions.\n",
        "coach/prompts/interviewer.md": "# Interviewer\nAsk one question at a time.\n",
    }.items():
        path = root.joinpath(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)

    problems = {
        "FND-990": _problem(root, "FND-990", coding_difficulty=3),
        "FND-991": _problem(root, "FND-991", coding_difficulty=1),
        "FND-992": _problem(
            root, "FND-992", coding_difficulty=3, validation="contract"
        ),
        "FND-993": _problem(
            root, "FND-993", track="systems", coding_difficulty=3
        ),
        "CAP-FND-999": _problem(root, "CAP-FND-999", coding_difficulty=3),
        "FND-994": _problem(
            root,
            "FND-994",
            coding_difficulty=3,
            marker="FUTURE-PROBLEM-BODY-MUST-NOT-LEAK",
        ),
    }
    catalog = Catalog(
        problems=problems,
        order=tuple(problems),
        tracks={
            "llm_algorithm": Track(
                "llm_algorithm", "Synthetic LLM Algorithm", "Synthetic track"
            ),
            "systems": Track("systems", "Synthetic Systems", "Synthetic track"),
        },
        quests={
            "synthetic-foundation": Quest(
                "synthetic-foundation",
                "Synthetic Foundation",
                ("FND-990", "FND-991"),
                "A synthetic recommended order.",
            )
        },
        capstones={},
    )
    return root, catalog


@pytest.fixture
def cli_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Catalog]:
    root, catalog = _repository(tmp_path)
    monkeypatch.chdir(root)
    monkeypatch.setattr(cli_module, "load_catalog", lambda _root: catalog)
    return root, catalog


def _run(
    capsys: pytest.CaptureFixture[str], *arguments: str
) -> tuple[int, str, str]:
    code = cli_module.main(list(arguments))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _init(capsys: pytest.CaptureFixture[str]) -> None:
    code, _, error = _run(
        capsys,
        "init",
        "--profile",
        PROFILE_ID,
        "--track",
        "llm_algorithm",
    )
    assert code == 0 and not error


def test_interview_candidates_filter_track_difficulty_quality_and_capstones(
    cli_repo: tuple[Path, Catalog],
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, catalog = cli_repo
    _init(capsys)

    assert [
        problem.id
        for problem in interview_candidates(
            catalog, track_id="llm_algorithm", difficulty="medium"
        )
    ] == ["FND-990", "FND-994"]

    code, output, error = _run(
        capsys,
        "interview",
        "candidates",
        "--profile",
        PROFILE_ID,
        "--track",
        "llm_algorithm",
        "--difficulty",
        "medium",
        "--json",
    )
    assert code == 0 and not error
    values = json.loads(output)
    assert [item["problem_id"] for item in values] == ["FND-990", "FND-994"]
    assert all(item["validation_level"] == "oracle" for item in values)
    assert all(item["difficulty"]["coding"] in {2, 3} for item in values)


def test_interview_ask_freezes_current_question_and_report_archives_evidence(
    cli_repo: tuple[Path, Catalog],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, _ = cli_repo
    _init(capsys)
    events_before = profile_paths(root, PROFILE_ID).events_file.read_bytes()
    assert _run(
        capsys,
        "interview",
        "create",
        "--profile",
        PROFILE_ID,
        "--mode",
        "catalog",
        "--track",
        "llm_algorithm",
        "--difficulty",
        "medium",
        "--duration",
        "30",
        "--problem",
        "FND-990",
        "--seed",
        "11",
    )[0] == 0
    assert _run(
        capsys,
        "interview",
        "start",
        "interview-0001",
        "--profile",
        PROFILE_ID,
    )[0] == 0

    delivered = "Explain one synthetic decision and give verifiable evidence."
    ask = (
        "interview",
        "ask",
        "interview-0001",
        "--profile",
        PROFILE_ID,
        "--question",
        "q-001",
        "--source",
        "ai",
        "--text",
        delivered,
    )
    code, output, error = _run(capsys, *ask)
    assert code == 0 and not error and "delivered and archived" in output
    assert _run(capsys, *ask)[0] == 0
    session_path = (
        profile_paths(root, PROFILE_ID).interviews_root
        / "interview-0001"
        / "session.json"
    )
    session = json.loads(session_path.read_text(encoding="utf-8"))
    assert session["delivered_questions"]["q-001"]["text"] == delivered
    assert sum(
        item["event"] == "question_delivered" for item in session["timeline"]
    ) == 1
    code, context_output, error = _run(
        capsys,
        "context",
        "--profile",
        PROFILE_ID,
        "--mode",
        "interviewer",
        "--interview",
        "interview-0001",
    )
    assert code == 0 and not error
    interviewer_context = json.loads(context_output)
    assert interviewer_context["current"]["question"]["prompt"] == delivered
    assert interviewer_context["current"]["question"]["prompt_source"] == "ai"
    assert "deliver_question" not in interviewer_context["commands"]

    mismatch = list(ask)
    mismatch[-1] = "A different question must be rejected."
    code, _, error = _run(capsys, *mismatch)
    assert code == 2 and "different text" in error

    answer = tmp_path / "answer.md"
    answer.write_text("Synthetic candidate evidence.\n", encoding="utf-8")
    code, _, error = _run(
        capsys,
        "interview",
        "answer",
        "interview-0001",
        "--profile",
        PROFILE_ID,
        "--question",
        "q-001",
        "--file",
        str(answer),
        "--asked",
        "A mismatched delivered question.",
    )
    assert code == 2 and "must match" in error
    assert _run(
        capsys,
        "interview",
        "answer",
        "interview-0001",
        "--profile",
        PROFILE_ID,
        "--question",
        "q-001",
        "--file",
        str(answer),
    )[0] == 0
    for question_id in ("q-002", "q-003"):
        assert _run(
            capsys,
            "interview",
            "answer",
            "interview-0001",
            "--profile",
            PROFILE_ID,
            "--question",
            question_id,
            "--file",
            str(answer),
        )[0] == 0

    code, _, error = _run(
        capsys,
        "interview",
        "ask",
        "interview-0001",
        "--profile",
        PROFILE_ID,
        "--question",
        "q-004",
        "--source",
        "ai",
        "--text",
        "Use a different coding interface.",
    )
    assert code == 2
    assert "frozen Catalog contract" in error

    coding = (
        profile_paths(root, PROFILE_ID).interviews_root
        / "interview-0001"
        / "coding"
        / "submission.py"
    )
    coding.write_text(
        "def increment(value: int) -> int:\n    return value + 1\n",
        encoding="utf-8",
    )
    assert _run(
        capsys,
        "interview",
        "test",
        "interview-0001",
        "--profile",
        PROFILE_ID,
    )[0] == 0

    for dimension, question_id in (
        ("reasoning_complexity", "q-003"),
        ("technical_oral", "q-003"),
        ("project_evidence", "q-002"),
        ("communication", "q-001"),
    ):
        scoring = _run(
            capsys,
            "interview",
            "score",
            "interview-0001",
            "--profile",
            PROFILE_ID,
            "--dimension",
            dimension,
            "--score",
            "80",
            "--source",
            "human",
            "--evidence",
            f"Specific synthetic evidence for {dimension}.",
            "--confidence",
            "high",
            "--question",
            question_id,
        )
        assert scoring[0] == 0, scoring

    code, output, error = _run(
        capsys,
        "interview",
        "finish",
        "interview-0001",
        "--profile",
        PROFILE_ID,
        "--summary",
        "Synthetic completed interview.",
    )
    assert code == 0 and not error and "PRACTICE MASTERY: UNCHANGED" in output

    code, output, error = _run(
        capsys,
        "interview",
        "report",
        "interview-0001",
        "--profile",
        PROFILE_ID,
        "--format",
        "json",
    )
    assert code == 0 and not error
    report = json.loads(output)
    archived = {item["question_id"]: item for item in report["questions"]}
    assert archived["q-001"] == {
        "question_id": "q-001",
        "kind": "introduction",
        "asked_question": delivered,
        "source": "ai",
        "completion": "answered",
    }
    assert report["objective_evidence"]["coding"]["status"] == "passed"
    assert report["objective_evidence"]["coding"]["passed"] == 2
    assert report["mastery_changed"] is False

    code, markdown, error = _run(
        capsys,
        "interview",
        "report",
        "interview-0001",
        "--profile",
        PROFILE_ID,
    )
    assert code == 0 and not error
    assert delivered in markdown
    assert "## Objective grader evidence" in markdown
    assert "2 passed, 0 failed" in markdown
    assert profile_paths(root, PROFILE_ID).events_file.read_bytes() == events_before


def test_context_mistakes_quest_and_profile_json_are_minimal_derived_views(
    cli_repo: tuple[Path, Catalog],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, catalog = cli_repo
    _init(capsys)
    started = start_problem(root, PROFILE_ID, catalog.get("FND-990"))
    inspected = inspect_submission(
        started.submission_path, profile_paths(root, PROFILE_ID).submissions_root
    )
    append_event(
        profile_paths(root, PROFILE_ID).events_file,
        event_schema_path(root),
        profile_id=PROFILE_ID,
        event_type="public_tests_run",
        problem_id="FND-990",
        attempt_id=started.attempt_id,
        payload={
            "submission_sha256": inspected.sha256,
            "exit_code": 1,
            "status": "failed",
            "passed": 0,
            "failed": 2,
            "duration_ms": 9,
        },
    )
    source = tmp_path / "private-resume.md"
    source.write_text("MATERIAL-BODY-MUST-NOT-LEAK", encoding="utf-8")
    add_material(root, PROFILE_ID, source, kind="resume", ai_access=True)

    code, output, error = _run(
        capsys,
        "context",
        "--profile",
        PROFILE_ID,
        "--mode",
        "teacher",
        "--help-level",
        "H1",
    )
    assert code == 0 and not error
    assert len(output.encode("utf-8")) <= 8 * 1024
    context = json.loads(output)
    assert context["current"]["problem"]["id"] == "FND-990"
    assert "H1-CURRENT-ONLY" in output
    assert "H2-NOT-REQUESTED" not in output
    assert "FUTURE-PROBLEM-BODY-MUST-NOT-LEAK" not in output
    assert "PUBLIC-TEST-BODY-MUST-STAY-PRIVATE" not in output
    assert "MATERIAL-BODY-MUST-NOT-LEAK" not in output
    assert "events.jsonl" not in output

    code, output, error = _run(
        capsys, "mistakes", "--profile", PROFILE_ID, "--json"
    )
    assert code == 0 and not error
    assert json.loads(output) == [
        {
            "problem_id": "FND-990",
            "title": "Synthetic FND-990",
            "failure_count": 1,
            "last_failed_at": json.loads(
                profile_paths(root, PROFILE_ID).events_file.read_text(encoding="utf-8").splitlines()[-1]
            )["timestamp"],
            "last_failure_kind": "public_tests_failed",
            "recovered": False,
            "practice_status": "in_progress",
        }
    ]
    assert not (profile_paths(root, PROFILE_ID).root / "mistakes.json").exists()

    code, output, error = _run(
        capsys, "graph", "--quest", "synthetic-foundation"
    )
    assert code == 0 and not error
    assert "QUEST synthetic-foundation" in output
    assert output.index("FND-990") < output.index("FND-991")
    code, output, error = _run(
        capsys,
        "next",
        "--profile",
        PROFILE_ID,
        "--quest",
        "synthetic-foundation",
    )
    assert code == 0 and not error and "QUEST" in output
    assert "synthetic-foundation" in output

    career = tmp_path / "career.yaml"
    career.write_text(
        "target_job_titles:\n  - LLM Algorithm Engineer\n"
        "employment_stage: new_grad\n"
        "preferred_locations:\n  - Remote\n"
        "interview_languages:\n  - zh-CN\n"
        "priorities:\n  - Training algorithms\n",
        encoding="utf-8",
    )
    events_before = profile_paths(root, PROFILE_ID).events_file.read_bytes()
    code, output, error = _run(
        capsys,
        "profile",
        "configure",
        PROFILE_ID,
        "--career-file",
        str(career),
    )
    assert code == 0 and not error and "PRACTICE EVENTS: UNCHANGED" in output
    assert profile_paths(root, PROFILE_ID).events_file.read_bytes() == events_before
    code, output, error = _run(
        capsys, "profile", "show", PROFILE_ID, "--json"
    )
    assert code == 0 and not error
    profile_view = json.loads(output)
    assert profile_view["profile"]["career_intent"]["target_job_titles"] == [
        "LLM Algorithm Engineer"
    ]
    assert profile_view["practice_status_counts"]["in_progress"] == 1
