from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest

import llm_interview_lab.cli as cli_module
from llm_interview_lab.catalog import Catalog, Problem, Track
from llm_interview_lab.events import read_events, reduce_events
from llm_interview_lab.workspace import event_schema_path, profile_paths


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILE_ID = "synthetic-candidate"
PROBLEM_ID = "FND-990"


def _synthetic_problem(root: Path) -> Problem:
    """Build an infrastructure-only problem unrelated to the public curriculum."""

    problem_dir = root / "synthetic-problems" / PROBLEM_ID
    problem_dir.mkdir(parents=True)
    (problem_dir / "task.md").write_text(
        "# Synthetic increment\n\nReturn the supplied integer plus one.\n",
        encoding="utf-8",
    )
    (problem_dir / "starter.py").write_text(
        "def increment(value: int) -> int:\n"
        "    raise NotImplementedError\n",
        encoding="utf-8",
    )
    (problem_dir / "test_public.py").write_text(
        "def test_positive(submission):\n"
        "    assert submission.increment(4) == 5\n\n"
        "def test_negative(submission):\n"
        "    assert submission.increment(-3) == -2\n",
        encoding="utf-8",
    )
    (problem_dir / "hints.md").write_text(
        "This file is a synthetic infrastructure fixture.\n",
        encoding="utf-8",
    )
    raw = {
        "id": PROBLEM_ID,
        "title": "Synthetic Increment",
        "status": "ready",
        "domain": "foundation",
        "tracks": ["llm_algorithm"],
        "tier": "core",
        "difficulty": {"concept": 2, "coding": 3, "debugging": 2},
        "prerequisites": [],
        "skills": ["python.functions"],
        "validation": {"level": "oracle", "field_runs": 0},
        "assets": {
            "problem_dir": problem_dir.relative_to(root).as_posix(),
        },
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
                "description": "Exact expected integers for a synthetic helper.",
            },
            "oral_questions": [
                "State the synthetic function contract.",
                "Explain the synthetic time and space complexity.",
                "Name one invalid-input policy.",
                "Describe two independent synthetic tests.",
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
            {
                "type": "documentation",
                "title": "Synthetic CLI infrastructure fixture",
            }
        ],
    }
    return Problem(
        PROBLEM_ID,
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


def _synthetic_repository(tmp_path: Path) -> tuple[Path, Catalog]:
    root = tmp_path / "repository"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        "[project]\nname = 'mock-interview-cli-fixture'\nversion = '0'\n",
        encoding="utf-8",
    )
    (root / "curriculum").mkdir()
    (root / ".gitignore").write_text(
        "/workspace/profiles/*\n!/workspace/profiles/.gitkeep\n",
        encoding="utf-8",
    )
    for name in ("schema", "templates"):
        shutil.copytree(REPO_ROOT / "workspace" / name, root / "workspace" / name)
    profiles = root / "workspace" / "profiles"
    profiles.mkdir(parents=True)
    (profiles / ".gitkeep").write_text("", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)

    problem = _synthetic_problem(root)
    catalog = Catalog(
        problems={problem.id: problem},
        order=(problem.id,),
        tracks={
            "llm_algorithm": Track(
                "llm_algorithm",
                "Synthetic LLM Algorithm",
                "Infrastructure-only CLI track.",
            )
        },
        quests={},
        capstones={},
    )
    return root, catalog


@pytest.fixture
def cli_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Catalog]:
    root, catalog = _synthetic_repository(tmp_path)
    monkeypatch.chdir(root)
    monkeypatch.setattr(cli_module, "load_catalog", lambda _root: catalog)
    return root, catalog


def _run(
    capsys: pytest.CaptureFixture[str],
    *arguments: str,
) -> tuple[int, str, str]:
    code = cli_module.main(list(arguments))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _material_id(output: str) -> str:
    match = re.search(r"(?m)^MATERIAL (material-[0-9a-f]{12}): stored$", output)
    assert match is not None, output
    return match.group(1)


def _sha256(output: str) -> str:
    match = re.search(r"(?m)^SHA256 ([0-9a-f]{64})$", output)
    assert match is not None, output
    return match.group(1)


def test_material_commands_and_tailored_consent_expose_only_frozen_metadata(
    cli_repo: tuple[Path, Catalog],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, _ = cli_repo
    assert (
        _run(capsys, "init", "--profile", PROFILE_ID, "--track", "llm_algorithm")[0]
        == 0
    )
    events_before = profile_paths(root, PROFILE_ID).events_file.read_bytes()
    material_body = "SYNTHETIC RESUME BODY MUST NOT BE PRINTED"
    source = tmp_path / "synthetic-resume.md"
    source.write_text(material_body, encoding="utf-8")

    code, output, error = _run(
        capsys,
        "material",
        "add",
        "--profile",
        PROFILE_ID,
        "--kind",
        "resume",
        "--file",
        str(source),
        "--title",
        "Synthetic resume",
        "--tag",
        "synthetic",
        "--allow-ai",
    )
    assert code == 0 and not error
    material_id = _material_id(output)
    digest = _sha256(output)
    assert material_body not in output

    code, output, error = _run(
        capsys, "material", "list", "--profile", PROFILE_ID
    )
    assert code == 0 and not error
    assert material_id in output and "kind=resume" in output
    assert "ai_access=yes" in output and "Synthetic resume" in output
    assert material_body not in output

    code, output, error = _run(
        capsys, "material", "show", material_id, "--profile", PROFILE_ID
    )
    assert code == 0 and not error
    assert material_id in output and digest in output
    assert "CONTENT not printed" in output and material_body not in output

    create = (
        "interview",
        "create",
        "--profile",
        PROFILE_ID,
        "--mode",
        "tailored",
        "--track",
        "llm_algorithm",
        "--difficulty",
        "medium",
        "--duration",
        "30",
        "--problem",
        PROBLEM_ID,
        "--material",
        material_id,
        "--focus",
        "synthetic ownership evidence",
        "--seed",
        "17",
    )
    code, _, error = _run(capsys, *create)
    assert code == 2 and "consent" in error.lower()

    code, output, error = _run(capsys, *create, "--consent-materials")
    assert code == 0 and not error
    assert "INTERVIEW interview-0001: ready" in output
    assert material_id in output and f"sha256={digest}" in output
    assert "use=mock_interview" in output
    assert material_body not in output and str(source.resolve()) not in output

    code, output, error = _run(
        capsys,
        "interview",
        "show",
        "interview-0001",
        "--profile",
        PROFILE_ID,
    )
    assert code == 0 and not error
    assert material_id in output and f"sha256={digest}" in output
    assert "use=mock_interview" in output
    assert "FOCUS synthetic ownership evidence" in output
    assert material_body not in output and str(source.resolve()) not in output

    assert profile_paths(root, PROFILE_ID).events_file.read_bytes() == events_before


def test_cli_enforces_current_question_scores_evidence_and_keeps_practice_unchanged(
    cli_repo: tuple[Path, Catalog],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, _ = cli_repo
    assert _run(capsys, "init", "--profile", PROFILE_ID, "--track", "llm_algorithm")[0] == 0
    events_file = profile_paths(root, PROFILE_ID).events_file
    events_before = events_file.read_bytes()

    code, output, error = _run(
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
        PROBLEM_ID,
        "--seed",
        "23",
    )
    assert code == 0 and not error and "interview-0001" in output

    code, output, error = _run(
        capsys,
        "interview",
        "start",
        "interview-0001",
        "--profile",
        PROFILE_ID,
    )
    assert code == 0 and not error
    submission_relpath = (
        f"workspace/profiles/{PROFILE_ID}/interviews/"
        "interview-0001/coding/submission.py"
    )
    assert f"SUBMISSION {submission_relpath}" in output
    submission = root / submission_relpath
    assert submission.is_file()
    assert "NotImplementedError" in submission.read_text(encoding="utf-8")

    answer = tmp_path / "answer.md"
    answer.write_text("Synthetic answer with explicit evidence.", encoding="utf-8")

    code, output, error = _run(
        capsys,
        "interview",
        "current",
        "interview-0001",
        "--profile",
        PROFILE_ID,
    )
    assert code == 0 and not error and "QUESTION q-001" in output

    code, _, error = _run(
        capsys,
        "interview",
        "answer",
        "interview-0001",
        "--profile",
        PROFILE_ID,
        "--question",
        "q-002",
        "--file",
        str(answer),
    )
    assert code == 2 and "current interview question" in error

    for question_id in ("q-001", "q-002", "q-003"):
        code, output, error = _run(
            capsys,
            "interview",
            "current",
            "interview-0001",
            "--profile",
            PROFILE_ID,
        )
        assert code == 0 and not error and f"QUESTION {question_id}" in output
        code, output, error = _run(
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
            "--asked",
            f"Synthetic personalized wording for {question_id}",
        )
        assert code == 0 and not error
        assert f"ANSWER {question_id}: recorded" in output

    code, output, error = _run(
        capsys,
        "interview",
        "current",
        "interview-0001",
        "--profile",
        PROFILE_ID,
    )
    assert code == 0 and not error and "QUESTION q-004 kind=coding" in output
    assert f"SUBMISSION {submission_relpath}" in output

    # This is an answer only to the synthetic infrastructure problem above.
    submission.write_text(
        "def increment(value: int) -> int:\n"
        "    return value + 1\n",
        encoding="utf-8",
    )
    code, output, error = _run(
        capsys,
        "interview",
        "test",
        "interview-0001",
        "--profile",
        PROFILE_ID,
    )
    assert code == 0 and not error
    assert "INTERVIEW CODING TESTS: PASSED" in output
    assert "PRACTICE MASTERY: UNCHANGED" in output

    code, output, error = _run(
        capsys,
        "interview",
        "current",
        "interview-0001",
        "--profile",
        PROFILE_ID,
    )
    assert code == 0 and not error and "awaiting_score" in output
    for dimension in (
        "reasoning_complexity",
        "technical_oral",
        "project_evidence",
        "communication",
    ):
        assert dimension in output

    with pytest.raises(SystemExit) as missing_reference:
        cli_module.main(
            [
                "interview",
                "score",
                "interview-0001",
                "--profile",
                PROFILE_ID,
                "--dimension",
                "communication",
                "--score",
                "80",
                "--source",
                "ai",
                "--evidence",
                "Synthetic evidence.",
                "--confidence",
                "medium",
            ]
        )
    assert missing_reference.value.code == 2
    capsys.readouterr()

    assessments = {
        "reasoning_complexity": ("82", "q-004"),
        "technical_oral": ("78", "q-003"),
        "project_evidence": ("74", "q-002"),
        "communication": ("80", "q-001"),
    }
    for dimension, (score, question_id) in assessments.items():
        code, output, error = _run(
            capsys,
            "interview",
            "score",
            "interview-0001",
            "--profile",
            PROFILE_ID,
            "--dimension",
            dimension,
            "--score",
            score,
            "--source",
            "ai",
            "--evidence",
            f"Synthetic evidence for {dimension}.",
            "--confidence",
            "medium",
            "--question",
            question_id,
        )
        assert code == 0 and not error
        assert f"ASSESSMENT {dimension}" in output

    code, output, error = _run(
        capsys,
        "interview",
        "finish",
        "interview-0001",
        "--profile",
        PROFILE_ID,
        "--summary",
        "Synthetic evidence-based overall evaluation.",
    )
    assert code == 0 and not error
    assert "INTERVIEW interview-0001: completed" in output
    assert "SCORE" in output and "PARTIAL EVIDENCE SCORE" not in output
    assert re.search(r"(?m)^ELAPSED \d+ seconds$", output)
    assert "PRACTICE MASTERY: UNCHANGED" in output

    code, report, error = _run(
        capsys,
        "interview",
        "report",
        "interview-0001",
        "--profile",
        PROFILE_ID,
        "--format",
        "markdown",
    )
    assert code == 0 and not error
    assert "Objective and subjective evidence" in report
    assert "Candidate elapsed time" in report
    assert "Synthetic evidence for reasoning_complexity." in report
    assert "medium" in report and "q-004" in report
    assert "Synthetic evidence-based overall evaluation." in report

    code, report_json, error = _run(
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
    parsed = json.loads(report_json)
    assert parsed["completion_status"] == "completed"
    assert parsed["mastery_changed"] is False
    assert parsed["dimensions"]["reasoning_complexity"]["question_ids"] == ["q-004"]

    assert events_file.read_bytes() == events_before
    state = reduce_events(read_events(events_file, event_schema_path(root)))
    assert not state.mastered


def test_incomplete_finish_and_report_use_an_explicit_partial_evidence_label(
    cli_repo: tuple[Path, Catalog],
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, _ = cli_repo
    assert _run(capsys, "init", "--profile", PROFILE_ID, "--track", "llm_algorithm")[0] == 0
    events_before = profile_paths(root, PROFILE_ID).events_file.read_bytes()
    assert _run(
        capsys,
        "interview",
        "create",
        "--profile",
        PROFILE_ID,
        "--track",
        "llm_algorithm",
        "--difficulty",
        "medium",
        "--duration",
        "30",
        "--problem",
        PROBLEM_ID,
    )[0] == 0
    assert _run(
        capsys,
        "interview",
        "start",
        "interview-0001",
        "--profile",
        PROFILE_ID,
    )[0] == 0

    code, output, error = _run(
        capsys,
        "interview",
        "finish",
        "interview-0001",
        "--profile",
        PROFILE_ID,
    )
    assert code == 2 and not output
    assert "--confirm-incomplete" in error

    code, output, error = _run(
        capsys,
        "interview",
        "finish",
        "interview-0001",
        "--profile",
        PROFILE_ID,
        "--confirm-incomplete",
    )
    assert code == 1 and not error
    assert "INTERVIEW interview-0001: incomplete" in output
    assert "PARTIAL EVIDENCE SCORE" in output
    assert re.search(r"(?m)^ELAPSED \d+ seconds$", output)

    code, report, error = _run(
        capsys,
        "interview",
        "report",
        "interview-0001",
        "--profile",
        PROFILE_ID,
    )
    assert code == 0 and not error
    assert "Partial evidence score" in report
    assert "not a complete interview score" in report
    assert "Objective and subjective evidence" in report
    assert profile_paths(root, PROFILE_ID).events_file.read_bytes() == events_before


def _help(
    capsys: pytest.CaptureFixture[str],
    *arguments: str,
) -> str:
    with pytest.raises(SystemExit) as result:
        cli_module.main([*arguments, "--help"])
    assert result.value.code == 0
    captured = capsys.readouterr()
    return captured.out + captured.err


def test_cli_answer_accepts_personalized_question_from_utf8_file(
    cli_repo: tuple[Path, Catalog],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, _ = cli_repo
    assert _run(capsys, "init", "--profile", PROFILE_ID, "--track", "llm_algorithm")[0] == 0
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
        PROBLEM_ID,
        "--seed",
        "31",
    )[0] == 0
    assert _run(
        capsys,
        "interview",
        "start",
        "interview-0001",
        "--profile",
        PROFILE_ID,
    )[0] == 0

    answer = tmp_path / "answer.md"
    answer.write_text("Synthetic candidate answer.\n", encoding="utf-8")
    asked = tmp_path / "asked.md"
    personalized_question = "请解释这个完全虚构的项目决策，并给出可核验的证据。"
    asked.write_text(personalized_question + "\n", encoding="utf-8")

    code, output, error = _run(
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
        "--asked-file",
        str(asked),
    )

    assert code == 0 and not error
    assert "ANSWER q-001: recorded" in output
    session_path = (
        profile_paths(root, PROFILE_ID).interviews_root
        / "interview-0001"
        / "session.json"
    )
    session = json.loads(session_path.read_text(encoding="utf-8"))
    assert session["answers"]["q-001"]["asked_question"] == personalized_question


def test_cli_help_readme_and_interview_guide_share_one_command_contract(
    capsys: pytest.CaptureFixture[str],
) -> None:
    material_help = _help(capsys, "material", "add")
    create_help = _help(capsys, "interview", "create")
    answer_help = _help(capsys, "interview", "answer")
    score_help = _help(capsys, "interview", "score")
    finish_help = _help(capsys, "interview", "finish")
    material_help = " ".join(material_help.split())
    create_help = " ".join(create_help.split())
    answer_help = " ".join(answer_help.split())
    score_help = " ".join(score_help.split())
    finish_help = " ".join(finish_help.split())

    assert "--allow-ai" in material_help and "not permanent consent" in material_help
    assert "--mode {catalog,tailored}" in create_help
    assert "--consent-materials" in create_help and "current SHA-256" in create_help
    assert "not an automatic selector" in create_help
    assert "--question QUESTION" in answer_help and "--asked ASKED" in answer_help
    assert "--asked-file ASKED_FILE" in answer_help
    assert "completed q-NNN evidence reference" in score_help
    assert "--confirm-incomplete" in finish_help
    assert "required evidence is missing" in finish_help

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    guide = (REPO_ROOT / "docs/interviews.md").read_text(encoding="utf-8")
    policy = (REPO_ROOT / "coach/POLICY.md").read_text(encoding="utf-8")

    for command in (
        "llm-lab material add --profile default --kind resume",
        "llm-lab material list --profile default",
        "llm-lab interview create --profile default --mode catalog",
        "--material MATERIAL_ID --consent-materials",
    ):
        assert command in re.sub(r"\\\s*\n\s*", "", readme), command

    normalized_guide = re.sub(r"\\\s*\n\s*", "", guide)
    assert re.search(
        r"llm-lab interview answer INTERVIEW_ID --profile default "
        r"--question q-001 --file workspace/profiles/default/cache/answer-q001\.md",
        normalized_guide,
    )
    assert "--asked-file workspace/profiles/default/cache/asked-question.txt" in guide
    assert re.search(
        r"llm-lab interview score INTERVIEW_ID --profile default .*"
        r"--question q-003",
        normalized_guide,
        flags=re.DOTALL,
    )
    assert "--difficulty hard --duration 45 --problem LOSS-014" not in normalized_guide
    assert "finish --confirm-incomplete" in guide
    assert "INTERVIEWER" in policy
    assert "untrusted evidence" in policy
    assert "mastery" in policy
