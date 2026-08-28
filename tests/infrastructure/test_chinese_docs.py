"""Small, deterministic contracts for the Chinese-first Alpha surface."""

from __future__ import annotations

from pathlib import Path
import re
from urllib.parse import unquote

import pytest

from llm_interview_lab.catalog import load_catalog


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")

USER_DOCUMENTS = (
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "CHANGELOG.md",
    "docs/desktop-app.md",
    "docs/ai-connections.md",
    "docs/role-profiles.md",
    "docs/workspace.md",
    "docs/best-practices.md",
    "docs/curriculum-authoring.md",
    "docs/beta-golden-quest.md",
    "docs/interviews.md",
    "docs/architecture.md",
    "docs/macos.md",
    "docs/windows.md",
    "docs/terminology.md",
    "workspace/README.md",
)


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _han_count(value: str) -> int:
    return len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", value))


def _assert_exact_case(path: Path) -> None:
    current = REPO_ROOT
    for part in path.relative_to(REPO_ROOT).parts:
        assert part in {child.name for child in current.iterdir()}
        current /= part


def test_user_surface_is_chinese_first_and_english_is_a_translation() -> None:
    readme = _read("README.md")
    assert _han_count(readme[:1600]) >= 20
    assert "README.en.md" in readme[:300]
    english = _read("README.en.md")
    assert "README.md" in english[:300]
    assert "canonical" in english[:600].lower()

    for path in USER_DOCUMENTS:
        text = _read(path)
        assert _han_count(text) >= 20, f"user document is not Chinese-first: {path}"


def test_all_readme_relative_links_exist_with_case() -> None:
    for document in ("README.md", "README.en.md"):
        source = REPO_ROOT / document
        for raw_target in MARKDOWN_LINK.findall(source.read_text(encoding="utf-8")):
            target = unquote(raw_target.strip().split(maxsplit=1)[0].strip("<>"))
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            relative = target.split("#", 1)[0]
            if not relative:
                continue
            resolved = (source.parent / relative).resolve()
            assert resolved.exists(), f"broken README link: {document}: {target}"
            _assert_exact_case(resolved)


def test_download_names_and_platform_job_are_consistent() -> None:
    readme = _read("README.md")
    workflow = _read(".github/workflows/ci.yml")
    expected = (
        "LLMInterviewLab-Windows-x64.exe",
        "LLMInterviewLab-Windows-x64-portable.zip",
        "LLMInterviewLab-macOS-arm64.app.zip",
        "LLMInterviewLab-macOS-arm64.dmg",
    )
    for name in expected:
        assert name in readme and name in workflow, name
    assert "SHA256SUMS.txt" in workflow
    assert "desktop-macos-arm64:" in workflow
    assert "runs-on: macos-15" in workflow
    assert "uname -m" in workflow
    assert "macOS-x86_64" not in workflow
    assert "macOS-x86_64" not in readme


def test_readme_statistics_are_derived_from_the_catalog() -> None:
    catalog = load_catalog(REPO_ROOT)
    ready = [problem for problem in catalog.problems.values() if problem.ready]
    values = {
        "Ready Problems": len(ready),
        "Planned Problems": len(catalog.problems) - len(ready),
        "Oracle-validated Problems": sum(
            problem.validation_level in {"oracle", "field", "stable"}
            for problem in ready
        ),
        "Retention-ready Problems": sum(
            all(problem.retention_variant(REPO_ROOT, stage) for stage in ("d2", "d7"))
            for problem in ready
        ),
        "Field-tested runs": sum(problem.field_runs for problem in ready),
    }
    readme = _read("README.md")
    for label, value in values.items():
        assert re.search(rf"{re.escape(label)}[^\n]*\b{value}\b", readme), label
    assert values["Field-tested runs"] == 0
    assert "不是 Beta 或 Stable" in readme
    assert "公开测试也不是隐藏的防作弊测试" in readme


def test_readme_is_honest_about_unsigned_macos_and_no_sandbox() -> None:
    readme = _read("README.md")
    assert "未使用 Apple Developer ID" in readme
    assert "未经过 Notarization" in readme
    assert "不构成恶意代码安全沙箱" in readme
    assert "Intel Mac" in readme and "不提供" in readme
    assert "保证 Offer" not in readme
    assert "完全防作弊" not in readme


def test_gui_and_provider_user_terms_are_present() -> None:
    main = _read("src/llm_interview_lab/desktop/qml/Main.qml")
    for label in ("首页", "刷题", "模拟面试", "AI 教练", "进度", "设置"):
        assert label in main
    onboarding = _read("src/llm_interview_lab/desktop/qml/pages/OnboardingPage.qml")
    for label in ("创建学习档案", "选择目标岗位", "能力自评", "暂不连接 AI"):
        assert label in onboarding
    connections = _read(
        "src/llm_interview_lab/desktop/qml/pages/ConnectionsPage.qml"
    )
    assert "app.providerOptions" in connections
    assert "无需 AI" in connections
    assert "测试连接" in connections
    provider = _read("src/llm_interview_lab/ai/providers.py")
    for value in ("openai", "openai-compatible", "ollama"):
        assert value in provider
    assert "系统密钥环" in _read("docs/ai-connections.md")


def test_screenshots_are_real_png_assets_and_documented() -> None:
    readme = _read("README.md")
    for name in (
        "desktop-home.png",
        "desktop-onboarding.png",
        "desktop-exercise.png",
        "desktop-interview.png",
        "desktop-connections.png",
    ):
        path = REPO_ROOT / "docs/images" / name
        assert path.is_file(), name
        assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
        assert name in readme


def test_community_templates_are_chinese_and_preserve_privacy_fields() -> None:
    for path in (
        ".github/ISSUE_TEMPLATE/bug.yml",
        ".github/ISSUE_TEMPLATE/curriculum.yml",
        ".github/ISSUE_TEMPLATE/beta.yml",
        ".github/ISSUE_TEMPLATE/config.yml",
        ".github/pull_request_template.md",
    ):
        text = _read(path)
        assert _han_count(text) >= 10, path
    beta = _read(".github/ISSUE_TEMPLATE/beta.yml")
    for field in (
        "background",
        "install_time",
        "first_task_time",
        "completed",
        "quest_completion",
        "contract_confusion",
        "misleading_test",
        "hint_leakage",
        "d2_usefulness",
        "d7_usefulness",
        "blocker",
        "free_text",
    ):
        assert f"id: {field}" in beta


def test_macos_document_matches_supported_release_boundary() -> None:
    document = _read("docs/macos.md")
    for term in ("Apple Silicon", "macOS 12", ".app.zip", ".dmg", "Keychain", "未公证"):
        assert term in document
    assert "Intel" in document and "不提供" in document
