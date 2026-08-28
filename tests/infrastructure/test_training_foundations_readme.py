from __future__ import annotations

import hashlib
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import unquote

import pytest

from llm_interview_lab.catalog import load_catalog
from llm_interview_lab.events import append_event, read_events, reduce_events
from llm_interview_lab.lifecycle import ReviewInput, record_review
from llm_interview_lab.workspace import event_schema_path, init_profile, profile_paths, start_problem


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]

TENSOR_LOSS_SEQUENCE = (
    "TNS-002",
    "TNS-003",
    "TNS-006",
    "TNS-010",
    "TNS-011",
    "TNS-013",
    "LOSS-007",
    "LOSS-008",
    "LOSS-014",
    "CAP-LOSS-001",
)
OPTIMIZER_TRAINER_SEQUENCE = (
    "NNL-001",
    "NNL-002",
    "OPT-001",
    "OPT-002",
    "OPT-004",
    "OPT-005",
    "CAP-TRN-001",
)
RETAINED_PROBLEMS = TENSOR_LOSS_SEQUENCE[:-1] + OPTIMIZER_TRAINER_SEQUENCE[:-1]

HARD_PREREQUISITES = {
    "TNS-003": {"TNS-002"},
    "TNS-006": {"TNS-003"},
    "TNS-010": {"TNS-003"},
    "TNS-011": {"TNS-006", "TNS-010"},
    "TNS-013": {"TNS-003"},
    "LOSS-007": {"TNS-003"},
    "LOSS-008": {"LOSS-007"},
    "LOSS-014": {"TNS-006", "TNS-010", "LOSS-008"},
    "NNL-001": {"TNS-003", "TNS-013"},
    "NNL-002": {"TNS-006", "TNS-013"},
    "OPT-001": {"TNS-013"},
    "OPT-002": {"OPT-001"},
    "OPT-004": {"TNS-013", "OPT-001"},
    "OPT-005": {"OPT-004"},
    "CAP-LOSS-001": {"TNS-011", "TNS-013", "LOSS-014"},
    "CAP-TRN-001": {
        "FND-006",
        "TNS-010",
        "TNS-013",
        "LOSS-014",
        "NNL-001",
        "NNL-002",
        "OPT-002",
        "OPT-005",
    },
}


def test_training_foundations_quests_have_the_public_sequences() -> None:
    catalog = load_catalog(REPO_ROOT)

    tensor_loss = catalog.quests["tensor_and_autograd"]
    optimizer_trainer = catalog.quests["optimizer_training_loop"]
    assert tensor_loss.title == "Tensor & Stable Loss"
    assert tensor_loss.problem_ids == TENSOR_LOSS_SEQUENCE
    assert optimizer_trainer.title == "Optimizer & Training Loop"
    assert optimizer_trainer.problem_ids == OPTIMIZER_TRAINER_SEQUENCE


def test_training_foundations_prerequisites_only_encode_hard_dependencies() -> None:
    catalog = load_catalog(REPO_ROOT)

    for problem_id, expected in HARD_PREREQUISITES.items():
        assert set(catalog.get(problem_id).prerequisites) == expected, problem_id

    # Quest order is pedagogical: these earlier nodes are intentionally not hard gates.
    assert "TNS-013" not in catalog.get("LOSS-007").prerequisites
    assert "NNL-001" not in catalog.get("NNL-002").prerequisites
    assert "OPT-002" not in catalog.get("OPT-004").prerequisites
    assert all(
        "LOSS-014" not in catalog.get(problem_id).prerequisites
        for problem_id in ("OPT-001", "OPT-002", "OPT-004", "OPT-005")
    )


def test_all_required_problem_nodes_are_oracle_validated_and_retention_ready() -> None:
    catalog = load_catalog(REPO_ROOT)

    assert len(RETAINED_PROBLEMS) == 15
    for problem_id in RETAINED_PROBLEMS:
        problem = catalog.get(problem_id)
        assert problem.ready, problem_id
        assert problem.validation_level == "oracle", problem_id
        fingerprint = problem.raw["validation"].get("fingerprint", "")
        assert re.fullmatch(r"[0-9a-f]{64}", fingerprint), problem_id
        for stage in ("d2", "d7"):
            assert problem.retention_variant(REPO_ROOT, stage) is not None, (
                problem_id,
                stage,
            )


def test_training_foundations_retention_assets_do_not_reuse_base_or_each_other() -> None:
    catalog = load_catalog(REPO_ROOT)
    for problem_id in RETAINED_PROBLEMS:
        problem = catalog.get(problem_id)
        d2 = problem.retention_variant(REPO_ROOT, "d2")
        d7 = problem.retention_variant(REPO_ROOT, "d7")
        assert d2 is not None and d7 is not None
        starters = (problem.problem_dir / "starter.py", d2[0], d7[0])
        public_tests = (problem.public_tests, d2[1], d7[1])
        assert len({path.read_bytes() for path in starters}) == 3, problem_id
        assert len({path.read_bytes() for path in public_tests}) == 3, problem_id


@pytest.mark.parametrize("capstone_id", ["CAP-LOSS-001", "CAP-TRN-001"])
def test_capstone_unlock_requires_every_hard_prerequisite(capstone_id: str) -> None:
    catalog = load_catalog(REPO_ROOT)
    capstone = catalog.get(capstone_id)
    expected = HARD_PREREQUISITES[capstone_id]

    assert capstone.ready
    assert capstone.validation_level == "oracle"
    assert set(capstone.prerequisites) == expected

    track_ids = set(capstone.raw["tracks"])
    unlocked = {problem.id for problem in catalog.unlocked(expected, track_ids)}
    assert capstone_id in unlocked
    for omitted in expected:
        incomplete = expected - {omitted}
        unlocked = {problem.id for problem in catalog.unlocked(incomplete, track_ids)}
        assert capstone_id not in unlocked, omitted


def _temp_repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir(parents=True)
    for name in ("pyproject.toml", ".gitignore"):
        shutil.copy2(REPO_ROOT / name, root / name)
    for name in ("schema", "catalog", "problems", "retention"):
        shutil.copytree(REPO_ROOT / "curriculum" / name, root / "curriculum" / name)
    for name in ("schema", "templates", "demo"):
        shutil.copytree(REPO_ROOT / "workspace" / name, root / "workspace" / name)
    (root / "workspace/profiles").mkdir(parents=True)
    (root / "workspace/profiles/.gitkeep").write_text("", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return root


def _record_mastery(root: Path, profile_id: str, problem_id: str) -> None:
    paths = profile_paths(root, profile_id)
    schema = event_schema_path(root)
    attempt_id = "attempt-0001"
    digest = hashlib.sha256(problem_id.encode()).hexdigest()
    append_event(
        paths.events_file, schema, profile_id=profile_id, event_type="task_started",
        problem_id=problem_id, attempt_id=attempt_id,
        payload={"submission_relpath": f"workspace/profiles/{profile_id}/submissions/{problem_id}/evidence.py"},
    )
    append_event(
        paths.events_file, schema, profile_id=profile_id, event_type="task_mastered",
        problem_id=problem_id, attempt_id=attempt_id,
        payload={"submission_sha256": digest},
    )


@pytest.mark.parametrize(
    ("quest_id", "external_mastery"),
    [
        ("tensor_and_autograd", set()),
        (
            "optimizer_training_loop",
            {"FND-006", "TNS-003", "TNS-006", "TNS-010", "TNS-013", "LOSS-014"},
        ),
    ],
)
def test_each_training_foundations_quest_unlocks_continuously_and_completes_after_capstone_review(
    tmp_path: Path,
    quest_id: str,
    external_mastery: set[str],
) -> None:
    root = _temp_repository(tmp_path)
    catalog = load_catalog(root)
    quest = catalog.quests[quest_id]
    required, capstone_id = quest.problem_ids[:-1], quest.problem_ids[-1]
    init_profile(root, "quest-learner", ("ai_foundation",))
    for problem_id in sorted(external_mastery):
        _record_mastery(root, "quest-learner", problem_id)
    mastered = set(external_mastery)
    for problem_id in required:
        unlocked = {problem.id for problem in catalog.unlocked(mastered, {"ai_foundation"})}
        assert problem_id in unlocked, (quest_id, problem_id)
        assert capstone_id not in unlocked
        _record_mastery(root, "quest-learner", problem_id)
        mastered.add(problem_id)
    assert capstone_id in {
        problem.id for problem in catalog.unlocked(mastered, {"ai_foundation"})
    }

    capstone = catalog.get(capstone_id)
    attempt = start_problem(root, "quest-learner", capstone)
    digest = hashlib.sha256(attempt.submission_path.read_bytes()).hexdigest()
    append_event(
        profile_paths(root, "quest-learner").events_file,
        event_schema_path(root),
        profile_id="quest-learner",
        event_type="task_implemented",
        problem_id=capstone_id,
        attempt_id=attempt.attempt_id,
        payload={"submission_sha256": digest},
    )
    review = record_review(
        root,
        "quest-learner",
        capstone_id,
        ReviewInput(
            contract_status="passed",
            oral_status="passed",
            code_explanation="Explained the complete capstone data flow.",
            complexity="Derived time and auxiliary-space costs.",
            boundary_conditions="Defended shape, mask, dtype, and invalid-input behavior.",
        ),
    )
    state = reduce_events(
        read_events(
            profile_paths(root, "quest-learner").events_file,
            event_schema_path(root),
        )
    )
    assert review.status == "reviewed" and not review.mastered
    assert all(problem_id in state.mastered for problem_id in required)
    assert state.problem_status(capstone_id) == "reviewed"


def _readme() -> str:
    return (REPO_ROOT / "README.md").read_text(encoding="utf-8")


def _heading_position(readme: str, aliases: tuple[str, ...]) -> int:
    headings = [
        (match.start(), match.group(1).strip().lower())
        for match in re.finditer(r"(?m)^##\s+(.+?)\s*$", readme)
    ]
    for position, heading in headings:
        if any(alias.lower() in heading for alias in aliases):
            return position
    raise AssertionError(f"README section is missing: {aliases}")


def test_readme_is_a_concise_product_page_with_required_section_order() -> None:
    readme = _readme()
    assert 250 <= len(readme.splitlines()) <= 450

    groups = (
        ("why this project", "这是什么项目"),
        ("choose a track", "适合哪些 AI 岗位"),
        ("start in 5 minutes", "下载与三分钟开始"),
        ("gui", "GUI 使用流程"),
        ("learning loop", "如何开始训练"),
        ("interview", "如何进行模拟面试"),
        ("use with ai", "如何接入 ai"),
        ("what makes it different", "项目的差异化"),
        ("workspace", "个人数据与隐私"),
        ("project status", "项目状态"),
        ("contributing", "参与贡献"),
        ("roadmap",),
    )
    positions = [_heading_position(readme, aliases) for aliases in groups]
    assert positions == sorted(positions)

    for entry in ("Start in 5 Minutes", "Browse Curriculum", "Use with AI"):
        assert entry in readme


def test_readme_quick_start_uses_real_clone_first_commands() -> None:
    readme = _readme()
    commands = (
        "git clone https://github.com/ComistryMo/llm_interview_lab.git",
        "cd llm_interview_lab",
        "python -m venv .venv",
        ".venv\\Scripts\\Activate.ps1",
        ". .venv/bin/activate",
        'python -m pip install -e ".[dev]"',
        "llm-lab init --profile default --track ai_foundation",
        "llm-lab doctor",
        "llm-lab next --profile default",
        "llm-lab start FND-001 --profile default",
        "llm-lab test FND-001 --profile default",
    )
    for command in commands:
        assert command in readme, command

    assert re.search(r"(?i)(starter|起始代码).{0,80}(预期|expected).{0,30}(失败|fail)", readme)
    assert 'python -m pip install -e ".[torch,dev]"' in readme


def test_readme_ai_prompt_and_boundaries_match_the_coach_policy() -> None:
    readme = _readme()
    policy = (REPO_ROOT / "coach/POLICY.md").read_text(encoding="utf-8")
    normalized_readme = readme.replace("–", "-").replace("—", "-")
    normalized_policy = policy.replace("–", "-").replace("—", "-")

    prompt_contract = (
        "Read AGENTS.md and coach/POLICY.md.",
        'Act in COACH mode for profile "default".',
        "llm-lab next --profile default",
        "Do not modify my submission.",
        "Do not reveal a complete solution.",
        "Do not mark a problem as mastered yourself.",
    )
    for text in prompt_contract:
        assert text in readme, text

    for term in ("TEACHER", "REVIEWER", "COACH", "H0-H5", "mastery"):
        assert term.lower() in normalized_readme.lower(), term
        assert term.lower() in normalized_policy.lower(), term

    assert "workspace/profiles/<id>/" in readme
    assert "Bring Your Own AI" in readme or "自带 AI" in readme


def test_readme_status_is_derived_from_the_current_catalog() -> None:
    catalog = load_catalog(REPO_ROOT)
    ready = [problem for problem in catalog.problems.values() if problem.ready]
    statistics = {
        "Ready": len(ready),
        "Oracle-validated": sum(
            problem.validation_level in {"oracle", "field", "stable"}
            for problem in ready
        ),
        "Retention-ready": sum(
            all(problem.retention_variant(REPO_ROOT, stage) for stage in ("d2", "d7"))
            for problem in ready
        ),
        "Field-tested": sum(problem.field_runs for problem in ready),
    }
    readme = _readme()

    for label, value in statistics.items():
        assert re.search(
            rf"(?im){re.escape(label)}[^\n]*\b{value}\b", readme
        ), f"README does not report {label}={value}"
    version = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert statistics["Field-tested"] == 0


def _assert_exact_case(path: Path) -> None:
    relative = path.relative_to(REPO_ROOT)
    current = REPO_ROOT
    for part in relative.parts:
        assert part in {child.name for child in current.iterdir()}, (
            f"README link casing does not match tracked path: {relative.as_posix()}"
        )
        current /= part


def _github_heading_anchors(markdown: str) -> set[str]:
    anchors: set[str] = set()
    occurrences: dict[str, int] = {}
    for heading in re.findall(r"(?m)^#{1,6}\s+(.+?)\s*$", markdown):
        plain = re.sub(r"[`*_~]", "", heading).lower()
        plain = re.sub(r"<[^>]+>", "", plain)
        slug = re.sub(r"[^\w\- ]", "", plain, flags=re.UNICODE)
        slug = re.sub(r"\s+", "-", slug.strip())
        suffix = occurrences.get(slug, 0)
        occurrences[slug] = suffix + 1
        anchors.add(slug if suffix == 0 else f"{slug}-{suffix}")
    return anchors


def test_readme_relative_links_and_anchors_resolve_with_exact_case() -> None:
    source = REPO_ROOT / "README.md"
    readme = source.read_text(encoding="utf-8")
    targets = re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", readme)
    assert targets

    for raw_target in targets:
        target = unquote(raw_target.strip().split(maxsplit=1)[0].strip("<>"))
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        path_text, _, fragment = target.partition("#")
        resolved = source if not path_text else (source.parent / path_text).resolve()
        assert resolved.exists(), f"broken README link: {target}"
        _assert_exact_case(resolved)
        if fragment and resolved.suffix.lower() == ".md":
            anchors = _github_heading_anchors(resolved.read_text(encoding="utf-8"))
            assert fragment in anchors, f"broken README anchor: {target}"


def test_readme_mermaid_and_release_markers_are_github_compatible() -> None:
    readme = _readme()
    diagrams = re.findall(r"```mermaid\s*\n(.*?)```", readme, flags=re.DOTALL)
    assert readme.count("```mermaid") == len(diagrams)
    assert 1 <= len(diagrams) <= 2
    assert all(re.match(r"\s*flowchart\s+(LR|TD)\b", diagram) for diagram in diagrams)

    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version = "(\d+\.\d+\.\d+)a(\d+)"$', pyproject)
    assert match is not None
    release = f"v{match.group(1)}-alpha.{match.group(2)}"
    assert release in readme
    assert "actions/workflows/ci.yml/badge.svg?branch=main" in readme
    assert "img.shields.io/github/v/release/ComistryMo/llm_interview_lab" in readme


def test_readme_is_honest_about_field_evidence_tests_and_local_execution() -> None:
    readme = _readme()
    assert re.search(r"(?i)grader.{0,100}(not a hostile-code security sandbox|不构成恶意代码安全沙箱)", readme)
    assert re.search(r"(?i)(field-tested runs|field runs|field-tested).{0,20}\b0\b|实际 field runs.{0,20}\b0\b", readme)
    assert re.search(r"(?i)(public tests passed|公开测试).{0,40}(mastered|已掌握)", readme)
    assert "workspace/profiles/maintainer" not in readme
