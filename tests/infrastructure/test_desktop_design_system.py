from __future__ import annotations

import math
from pathlib import Path
import re

import pytest


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]
QML_ROOT = REPO_ROOT / "src/llm_interview_lab/desktop/qml"
THEME_PATH = QML_ROOT / "components/AppTheme.qml"
MAIN_QML_PATH = QML_ROOT / "Main.qml"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _conditional_colors(source: str, name: str) -> tuple[str, str]:
    match = re.search(
        rf"readonly\s+property\s+color\s+{re.escape(name)}\s*:\s*"
        r'darkMode\s*\?\s*"(#[0-9a-fA-F]{6})"\s*:\s*'
        r'"(#[0-9a-fA-F]{6})"',
        source,
    )
    assert match is not None, f"{name} must define explicit dark/light colors"
    return match.group(1), match.group(2)


def _relative_luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        value / 12.92
        if value <= 0.04045
        else math.pow((value + 0.055) / 1.055, 2.4)
        for value in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(first: str, second: str) -> float:
    first_luminance = _relative_luminance(first)
    second_luminance = _relative_luminance(second)
    light = max(first_luminance, second_luminance)
    dark = min(first_luminance, second_luminance)
    return (light + 0.05) / (dark + 0.05)


def _deploy_qml_files(path: Path) -> set[str]:
    source = _read(path)
    match = re.search(r"(?m)^qml_files\s*=\s*(.+)$", source)
    assert match is not None, f"missing qml_files in {path.name}"
    return {item.strip().replace("\\", "/") for item in match.group(1).split(",")}


def _qml_files_on_disk() -> set[str]:
    return {
        path.relative_to(REPO_ROOT).as_posix()
        for path in QML_ROOT.rglob("*.qml")
    }


def test_app_theme_exposes_semantic_and_legacy_palette_contracts() -> None:
    source = _read(THEME_PATH)
    semantic_colors = {
        "canvas",
        "chrome",
        "surface",
        "surfaceRaised",
        "surfaceSunken",
        "surfaceHover",
        "textStrong",
        "text",
        "muted",
        "subtle",
        "accentForeground",
        "dangerForeground",
        "borderSubtle",
        "borderDefault",
        "borderStrong",
        "controlBorder",
        "focusRing",
        "accent",
        "accentHover",
        "accentPressed",
        "accentSoft",
        "toastBackground",
        "toastForeground",
        "success",
        "warning",
        "danger",
    }
    for name in semantic_colors:
        assert re.search(
            rf"readonly\s+property\s+color\s+{re.escape(name)}\s*:", source
        ), f"missing semantic theme color: {name}"

    legacy_match = re.search(
        r"readonly\s+property\s+QtObject\s+legacyPalette\s*:\s*QtObject\s*"
        r"\{(?P<body>.*?)\n\s*\}\n\n\s*function\s+scaledPx",
        source,
        flags=re.DOTALL,
    )
    assert legacy_match is not None
    legacy_source = legacy_match.group("body")
    for name in {
        "background",
        "surface",
        "surfaceAlt",
        "border",
        "text",
        "muted",
        "accent",
        "accentForeground",
        "success",
        "warning",
        "danger",
    }:
        assert re.search(
            rf"readonly\s+property\s+color\s+{re.escape(name)}\s*:",
            legacy_source,
        ), f"legacy page palette lost key: {name}"
    assert "readonly property color text: theme.textStrong" in legacy_source


@pytest.mark.parametrize(
    ("foreground", "background", "minimum"),
    [
        ("textStrong", "canvas", 7.0),
        ("text", "surface", 4.5),
        ("muted", "canvas", 4.5),
        ("accentForeground", "accent", 4.5),
        ("dangerForeground", "danger", 4.5),
        ("focusRing", "surface", 3.0),
        ("controlBorder", "surface", 3.0),
    ],
)
def test_key_theme_pairs_keep_readable_contrast(
    foreground: str, background: str, minimum: float
) -> None:
    source = _read(THEME_PATH)
    foreground_colors = _conditional_colors(source, foreground)
    background_colors = _conditional_colors(source, background)
    for mode, foreground_color, background_color in zip(
        ("dark", "light"), foreground_colors, background_colors, strict=True
    ):
        ratio = _contrast(foreground_color, background_color)
        assert ratio >= minimum, (
            f"{mode} {foreground}/{background} contrast is {ratio:.2f}; "
            f"expected at least {minimum:.1f}"
        )


def test_screenshot_theme_font_and_motion_are_ephemeral_display_overrides() -> None:
    entrypoint = _read(REPO_ROOT / "src/llm_interview_lab/desktop/main.py")
    controller = _read(REPO_ROOT / "src/llm_interview_lab/desktop/controller.py")
    capture = _read(REPO_ROOT / "scripts/capture_desktop_screenshots.py")
    main_qml = _read(MAIN_QML_PATH)

    for argument in {
        "--screenshot-theme",
        "--screenshot-font-scale",
        "--screenshot-motion-scale",
    }:
        assert argument in entrypoint
    assert "demo_theme=args.screenshot_theme" in entrypoint
    assert re.search(
        r'window\.setProperty\(\s*"displayFontScaleOverride"\s*,\s*'
        r"args\.screenshot_font_scale\s*\)",
        entrypoint,
    )
    assert re.search(
        r'window\.setProperty\(\s*"displayMotionScaleOverride"\s*,\s*'
        r"args\.screenshot_motion_scale\s*\)",
        entrypoint,
    )
    override_block = entrypoint.split(
        "# These are presentation-only overrides for deterministic evidence.", 1
    )[1].split("if args.window_size is not None:", 1)[0]
    assert "controller." not in override_block
    assert ".setValue(" not in override_block
    assert "_settings" not in override_block

    assert "if not self._demo_mode:" in controller
    assert 'self._settings.setValue("theme", value)' in controller
    assert 'self._settings.setValue("fontScale", self._font_scale)' in controller
    assert "property real displayFontScaleOverride: 0.0" in main_qml
    assert "property real displayMotionScaleOverride: -1.0" in main_qml

    assert '"--screenshot-font-scale"' in capture
    assert '"--screenshot-motion-scale"' in capture
    assert '"font_scale": 1.0' in capture
    assert '"motion_scale": 0.0' in capture


def test_shell_breakpoints_and_exercise_route_are_permanent() -> None:
    source = _read(MAIN_QML_PATH)
    assert 'width < 1040 ? "compact"' in source
    assert 'width < 1400 ? "standard" : "wide"' in source
    assert 'layoutMode === "wide" ? 224' in source
    assert 'layoutMode === "standard" ? 72 : 64' in source
    assert source.count('{id: "exercise"') >= 2
    assert "ExercisePage { app: backend; palette: window.colors }" in source
    assert 'if (actionId === "run-tests")' in source
    assert "backend.navigate(actionId)" in source


def test_shell_and_legacy_home_actions_use_accessible_theme_foregrounds() -> None:
    theme_source = _read(THEME_PATH)
    home_source = _read(QML_ROOT / "pages/HomePage.qml")
    shell_source = _read(MAIN_QML_PATH)

    assert "readonly property color accentForeground: theme.accentForeground" in theme_source
    assert home_source.count("root.palette.accentForeground") >= 3
    assert 'id: retentionActionButton' in home_source
    assert 'variant: "secondary"' in shell_source
    assert 'highlighted: true' in shell_source


def test_non_macos_shell_keeps_native_equivalent_actions_discoverable() -> None:
    source = _read(MAIN_QML_PATH)
    assert 'visible: Qt.platform.os === "osx"' in source
    assert '{id: "about"' in source
    assert '{id: "quit"' in source
    assert 'actionId === "about"' in source
    assert 'actionId === "quit"' in source
    assert "aboutDialog.open()" in source
    assert "Qt.quit()" in source
    assert "sequence: StandardKey.Preferences" in source
    assert "sequence: StandardKey.Quit" in source
    assert 'backend.navigate("settings")' in source
    assert 'objectName: "shellRouteTitle"' in source
    assert "window.pageTitle(backend.currentPage)" in source


def test_deploy_specs_exactly_cover_the_qml_tree() -> None:
    disk_files = _qml_files_on_disk()
    windows_files = _deploy_qml_files(REPO_ROOT / "scripts/pysidedeploy.spec")
    macos_files = _deploy_qml_files(REPO_ROOT / "scripts/pysidedeploy-macos.spec")
    assert windows_files == disk_files
    assert macos_files == disk_files
    assert windows_files == macos_files


def test_deploy_specs_explicitly_include_desktop_resources() -> None:
    include = (
        "--include-data-dir=src/llm_interview_lab/desktop/resources="
        "llm_interview_lab/desktop/resources"
    )
    for path in {
        REPO_ROOT / "scripts/pysidedeploy.spec",
        REPO_ROOT / "scripts/pysidedeploy-macos.spec",
    }:
        assert include in _read(path)


def test_connecting_status_is_notified_after_the_future_is_published() -> None:
    controller = _read(REPO_ROOT / "src/llm_interview_lab/desktop/controller.py")
    assert controller.count(
        "self._codex_connect_future = future\n"
        "                    self.aiStateChanged.emit()"
    ) == 1
    assert controller.count(
        "self._codex_connect_future = future\n"
        "            self.aiStateChanged.emit()"
    ) == 1


def test_recursive_resources_and_icon_license_are_packaged() -> None:
    pyproject = _read(REPO_ROOT / "pyproject.toml")
    assert '"desktop/resources/*"' in pyproject
    assert '"desktop/resources/**/*"' in pyproject

    icon_root = REPO_ROOT / "src/llm_interview_lab/desktop/resources/icons"
    assert (icon_root / "LICENSE.md").is_file()
    assert {
        "home.svg",
        "book-open.svg",
        "code.svg",
        "interview.svg",
        "messages.svg",
        "briefcase.svg",
        "chart.svg",
        "plug.svg",
        "settings.svg",
        "search.svg",
        "more.svg",
        "user.svg",
    }.issubset({path.name for path in icon_root.glob("*.svg")})


def test_shell_automation_object_names_remain_stable() -> None:
    source = _read(MAIN_QML_PATH)
    required = {
        "commandPalette",
        "commandPaletteSearch",
        "commandPaletteList",
        "globalToast",
        "codexApprovalBanner",
        "codexApprovalViewButton",
        "codexApprovalDetails",
        "codexApprovalClose",
        "codexApprovalDecline",
        "codexApprovalApprove",
        "moreNavigationButton",
        "aboutDialog",
    }
    for object_name in required:
        assert f'objectName: "{object_name}"' in source
