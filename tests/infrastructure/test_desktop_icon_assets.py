"""Contracts for the canonical Quiet Forge project and application icon."""

from __future__ import annotations

from pathlib import Path
import struct

import pytest


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]
ICON_PATH = REPO_ROOT / "src/llm_interview_lab/desktop/resources/app-icon.png"


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def test_quiet_forge_png_is_the_canonical_transparent_brand_asset() -> None:
    payload = ICON_PATH.read_bytes()
    assert payload[:8] == b"\x89PNG\r\n\x1a\n"
    assert payload[12:16] == b"IHDR"
    assert struct.unpack(">II", payload[16:24]) == (1024, 1024)
    assert payload[25] == 6, "canonical icon must retain RGBA transparency"
    assert not (ICON_PATH.parent / "app-icon.svg").exists()


def test_runtime_qml_build_and_readme_use_the_same_icon() -> None:
    main = _read("src/llm_interview_lab/desktop/main.py")
    main_qml = _read("src/llm_interview_lab/desktop/qml/Main.qml")
    onboarding = _read(
        "src/llm_interview_lab/desktop/qml/pages/OnboardingPage.qml"
    )
    generator = _read("scripts/generate_desktop_icons.py")
    readme = _read("README.md")
    notices = _read("docs/third-party-notices.md")

    assert 'QIcon(str(Path(__file__).parent / "resources/app-icon.png"))' in main
    assert "app.setWindowIcon(app_icon)" in main
    assert "app-icon.png" in main_qml
    assert onboarding.count("app-icon.png") == 2
    assert 'source = root / "src/llm_interview_lab/desktop/resources/app-icon.png"' in generator
    assert "QSvgRenderer" not in generator
    assert "src/llm_interview_lab/desktop/resources/app-icon.png" in readme
    assert "src/llm_interview_lab/desktop/resources/app-icon.png" in notices
    assert "app-icon.svg" not in "\n".join((main_qml, onboarding, generator, notices))


def test_platform_deploy_specs_consume_generated_icons() -> None:
    windows = _read("scripts/pysidedeploy.spec")
    macos = _read("scripts/pysidedeploy-macos.spec")
    pyproject = _read("pyproject.toml")

    assert "icon = dist/icons/LLMInterviewLab.ico" in windows
    assert "icon = dist/icons/LLMInterviewLab.icns" in macos
    assert '"desktop/resources/*"' in pyproject
    assert '"desktop/resources/**/*"' in pyproject
