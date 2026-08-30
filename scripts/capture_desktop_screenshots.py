"""Capture deterministic synthetic desktop screenshots and their provenance."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

from llm_interview_lab import __version__


REPO_ROOT = Path(__file__).resolve().parents[1]
IMAGE_ROOT = REPO_ROOT / "docs/images"
# Keep the original nine entries stable for downstream release checks.  The
# expanded matrix below is additive: old links remain valid while reviewers
# get every requested page, viewport, and theme in one manifest.
LEGACY_SPECS = (
    ("desktop-onboarding.png", "onboarding", "1280x800", "role-selected"),
    ("desktop-home.png", "home", "1280x800", "current-practice"),
    ("desktop-learn.png", "learn", "1280x800", "recommended-filter"),
    ("desktop-exercise.png", "exercise", "1280x800", "latest-submission"),
    ("desktop-interview.png", "interview", "1280x800", "active-question"),
    ("desktop-connections.png", "connections", "1280x800", "no-ai-default"),
    ("onboarding-hotfix-1080x680.png", "onboarding", "1080x680", "role-selected"),
    ("onboarding-hotfix-1280x800.png", "onboarding", "1280x800", "role-selected"),
    ("onboarding-hotfix-1440x900.png", "onboarding", "1440x900", "role-selected"),
)

PAGES = (
    "onboarding",
    "home",
    "learn",
    "exercise",
    "interview",
    "coach",
    "connections",
    "settings",
)
SIZES = ("900x620", "1080x680", "1280x800", "1440x900")
THEMES = ("light", "dark")


def _matrix_filename(page: str, size: str, theme: str) -> str:
    """Return a stable, descriptive path for one matrix cell."""

    # Preserve the six historical 1280px names in the authoritative matrix;
    # the remaining legacy onboarding names are materialized as aliases after
    # the 8x4x2 matrix is captured.  This keeps coverage exactly 64 cells.
    legacy_names = {
        ("onboarding", "1280x800", "light"): "desktop-onboarding.png",
        ("home", "1280x800", "light"): "desktop-home.png",
        ("learn", "1280x800", "light"): "desktop-learn.png",
        ("exercise", "1280x800", "light"): "desktop-exercise.png",
        ("interview", "1280x800", "light"): "desktop-interview.png",
        ("connections", "1280x800", "light"): "desktop-connections.png",
    }
    if (page, size, theme) in legacy_names:
        return legacy_names[(page, size, theme)]
    return f"desktop-{page}-{size}-{theme}.png"


def _expanded_specs() -> tuple[tuple[str, str, str, str], ...]:
    values: list[tuple[str, str, str, str]] = []
    states = {
        "onboarding": "role-selected",
        "home": "current-practice",
        "learn": "recommended-filter",
        "exercise": "latest-submission",
        "interview": "active-question",
        "coach": "resumable-session",
        "connections": "no-ai-default",
        "settings": "local-first-settings",
    }
    for theme in THEMES:
        for size in SIZES:
            for page in PAGES:
                filename = _matrix_filename(page, size, theme)
                values.append((filename, page, size, states[page]))
    return tuple(values)


# Public for screenshot-contract tests and release tooling.
SPECS = _expanded_specs()


def _git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture synthetic desktop screenshots for every target page and viewport."
    )
    parser.add_argument(
        "--theme",
        choices=("light", "dark", "all"),
        default="all",
        help="theme matrix to capture (default: all)",
    )
    parser.add_argument(
        "--delay-ms",
        type=int,
        default=350,
        help="offscreen settle delay per window (default: 350; minimum 50)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    selected_themes = THEMES if args.theme == "all" else (args.theme,)
    if args.delay_ms < 50:
        raise SystemExit("--delay-ms must be at least 50 ms")
    source_commit = _git_commit()
    environment = os.environ.copy()
    environment["QT_QUICK_BACKEND"] = "software"
    # Native Windows rendering is required for the real CJK font fallback;
    # the offscreen plugin renders tofu glyphs on the maintainer workstation.
    environment["QT_QPA_PLATFORM"] = "windows" if sys.platform == "win32" else "offscreen"
    environment["LLM_LAB_SCREENSHOT_DELAY_MS"] = str(args.delay_ms)
    captured: list[dict[str, object]] = []
    IMAGE_ROOT.mkdir(parents=True, exist_ok=True)

    for filename, page, size, state in SPECS:
        theme = "dark" if filename.endswith("-dark.png") else "light"
        if theme not in selected_themes:
            continue
        destination = IMAGE_ROOT / filename
        command = [
            sys.executable,
            "-m",
            "llm_interview_lab.desktop.main",
            "--screenshot",
            str(destination),
            "--screenshot-page",
            page,
            "--window-size",
            size,
            "--screenshot-font-scale",
            "1.0",
            "--screenshot-motion-scale",
            "0.0",
        ]
        if page == "onboarding":
            command.extend(
                [
                    "--onboarding-step",
                    "1",
                    "--onboarding-role",
                    "post_training_engineer",
                ]
            )
        command.extend(["--screenshot-theme", theme])
        subprocess.run(command, cwd=REPO_ROOT, env=environment, check=True)
        image = QImage(str(destination))
        expected_width, expected_height = (int(value) for value in size.split("x"))
        if image.isNull():
            raise RuntimeError(f"invalid screenshot geometry: {destination}")
        if image.width() != expected_width or image.height() != expected_height:
            expected_ratio = expected_width / expected_height
            actual_ratio = image.width() / image.height()
            if abs(expected_ratio - actual_ratio) > 0.01:
                raise RuntimeError(f"invalid screenshot aspect ratio: {destination}")
            image = image.scaled(
                expected_width,
                expected_height,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            if not image.save(str(destination)):
                raise RuntimeError(f"failed to normalize screenshot geometry: {destination}")
        if image.width() != expected_width or image.height() != expected_height:
            raise RuntimeError(f"invalid screenshot geometry: {destination}")
        captured.append(
            {
                "path": destination.relative_to(REPO_ROOT).as_posix(),
                "page": page,
                "state": state,
                "size": size,
                "source_commit": source_commit,
                "platform": sys.platform,
                "theme": theme,
                "font_scale": 1.0,
                "motion_scale": 0.0,
                "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                "synthetic": True,
            }
        )

    # A single-theme invocation is useful while iterating, but must not erase
    # the other half of an already-complete release matrix.  If the existing
    # manifest belongs to another source commit, leave it untouched: mixing
    # screenshots from two UI revisions would be less truthful than reporting
    # that a full capture is still required.
    existing: dict[str, object] | None = None
    manifest_path = IMAGE_ROOT / "screenshot-manifest.json"
    if args.theme != "all" and manifest_path.is_file():
        try:
            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
            if (
                isinstance(loaded, dict)
                and loaded.get("source_commit") == source_commit
                and isinstance(loaded.get("all_screenshots"), list)
            ):
                existing = loaded
        except (OSError, ValueError):
            existing = None
    if args.theme != "all" and existing is None:
        # Keep any existing authoritative manifest intact until both themes
        # have been captured from the same source revision.
        return 0

    all_screenshots = list(existing.get("all_screenshots", [])) if existing else []
    by_key = {
        (item["page"], item["size"], item["theme"]): item
        for item in all_screenshots
        if isinstance(item, dict)
    }
    for item in captured:
        by_key[(item["page"], item["size"], item["theme"])] = item
    all_screenshots = [
        by_key[(page, size, theme)]
        for theme in THEMES
        for size in SIZES
        for page in PAGES
        if (page, size, theme) in by_key
    ]
    complete_matrix = len(all_screenshots) == len(PAGES) * len(SIZES) * len(THEMES)

    # Keep the original nine links in a stable, explicit list.  The historical
    # onboarding aliases are materialized from matrix cells and must not
    # inflate the authoritative coverage count.
    legacy_screenshots: list[dict[str, object]] = []
    if complete_matrix:
        for filename, page, size, state in LEGACY_SPECS:
            source = by_key.get((page, size, "light"))
            if source is None:
                continue
            destination = IMAGE_ROOT / filename
            source_path = REPO_ROOT / str(source["path"])
            if destination.resolve() != source_path.resolve():
                shutil.copyfile(source_path, destination)
            alias = dict(source)
            alias["path"] = destination.relative_to(REPO_ROOT).as_posix()
            alias["state"] = state
            alias["alias_of"] = source["path"]
            alias["sha256"] = hashlib.sha256(destination.read_bytes()).hexdigest()
            legacy_screenshots.append(alias)
    elif existing:
        # This branch is defensive (the early return above handles incomplete
        # manifests without a same-revision baseline), and preserves aliases
        # if a future caller stores a partial matrix explicitly.
        legacy_screenshots = list(existing.get("screenshots", []))
    manifest = {
        "version": __version__,
        "source_commit": source_commit if complete_matrix else str(existing.get("source_commit", source_commit)),
        "language": "zh-CN",
        "synthetic": True,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        # ``screenshots`` is intentionally backward-compatible with the nine
        # original release artifacts.  ``all_screenshots`` is the authoritative
        # review matrix for this release.
        "screenshots": legacy_screenshots,
        "all_screenshots": all_screenshots,
        "coverage": {
            "pages": list(PAGES),
            "sizes": list(SIZES),
            "themes": list(THEMES),
            "count": len(all_screenshots),
            "expected_count": len(PAGES) * len(SIZES) * len(THEMES),
            "legacy_alias_count": len(legacy_screenshots),
        },
    }
    (IMAGE_ROOT / "screenshot-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
