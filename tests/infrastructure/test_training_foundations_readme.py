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
from llm_interview_lab.release_version import release_metadata
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
    # A product page should not need filler to reach a minimum line count.
    assert len(readme.splitlines()) <= 200

    groups = (
        ("下载",),
        ("能用它做什么", "功能"),
        ("第一次使用", "开始使用"),
        ("从源码运行", "源码安装"),
        ("文档", "反馈"),
    )
    positions = [_heading_position(readme, aliases) for aliases in groups]
    assert positions == sorted(positions)

    for guide in ("docs/desktop-app.md", "docs/interviews.md", "docs/local-stt.md"):
        assert guide in readme


def test_readme_quick_start_uses_real_clone_first_commands() -> None:
    readme = _readme()
    commands = (
        "git clone https://github.com/ComistryMo/llm_interview_lab.git",
        "cd llm_interview_lab",
        "python -m venv .venv",
        ".venv\\Scripts\\Activate.ps1",
        ". .venv/bin/activate",
        'python -m pip install -e ".[desktop,ai,dev]"',
        "llm-lab-gui",
    )
    for command in commands:
        assert command in readme, command

    assert 'python -m pip install -e ".[torch,dev]"' in readme


def test_readme_ai_is_interview_only_and_keeps_safety_boundaries() -> None:
    readme = _readme()
    assert "一次只生成下一问" in readme
    assert 'Act in COACH mode' not in readme
    assert "确认" in readme and "上下文" in readme
    assert "系统密钥环" in readme
    assert "云端额度" in readme and "计费" in readme
    assert "不连接 AI" in readme


def test_readme_links_to_content_scope_and_explains_optional_dependencies() -> None:
    readme = _readme()
    assert "docs/content/release-candidate-coverage-20260909.zh.md" in readme
    assert "PyTorch" in readme and "未内置" in readme
    assert "前置练习" in readme


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


@pytest.mark.parametrize("document", ["README.md", "README.en.md", "docs/README.md"])
def test_readme_relative_links_and_anchors_resolve_with_exact_case(document) -> None:
    source = REPO_ROOT / document
    readme = source.read_text(encoding="utf-8")
    targets = re.findall(r"!?\[[^\]]+\]\(([^)]+)\)", readme)
    targets += re.findall(r'<img\s[^>]*src="([^"]+)"', readme)
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


def test_readme_diagrams_and_release_links_are_github_compatible() -> None:
    readme = _readme()
    diagrams = re.findall(r"```mermaid\s*\n(.*?)```", readme, flags=re.DOTALL)
    assert readme.count("```mermaid") == len(diagrams)
    assert all(re.match(r"\s*flowchart\s+(LR|TD)\b", diagram) for diagram in diagrams)
    release = release_metadata()["tag"]
    assert f"/releases/tag/{release}" in readme
    assert f"/releases/download/{release}/SHA256SUMS.txt" in readme


def test_readme_distinguishes_practice_evidence_and_safe_local_execution() -> None:
    readme = _readme()
    assert "只运行你信任的代码" in readme
    assert "不提供恶意代码安全沙箱" in readme
    assert re.search(r"公开测试.{0,40}不等于.{0,20}掌握", readme)
    assert "AI" in readme and "实际跑通" in readme
    assert "workspace/profiles/maintainer" not in readme
