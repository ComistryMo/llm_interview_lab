"""Capture deterministic synthetic desktop screenshots and their provenance."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from PySide6.QtGui import QImage

from llm_interview_lab import __version__


REPO_ROOT = Path(__file__).resolve().parents[1]
IMAGE_ROOT = REPO_ROOT / "docs/images"
SPECS = (
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


def _git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def main() -> int:
    source_commit = _git_commit()
    environment = os.environ.copy()
    environment["QT_QUICK_BACKEND"] = "software"
    # Native Windows rendering is required for the real CJK font fallback;
    # the offscreen plugin renders tofu glyphs on the maintainer workstation.
    environment["QT_QPA_PLATFORM"] = "windows" if sys.platform == "win32" else "offscreen"
    screenshots: list[dict[str, object]] = []
    IMAGE_ROOT.mkdir(parents=True, exist_ok=True)

    for filename, page, size, state in SPECS:
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
        subprocess.run(command, cwd=REPO_ROOT, env=environment, check=True)
        image = QImage(str(destination))
        expected_width, expected_height = (int(value) for value in size.split("x"))
        if image.isNull() or image.width() != expected_width or image.height() != expected_height:
            raise RuntimeError(f"invalid screenshot geometry: {destination}")
        screenshots.append(
            {
                "path": destination.relative_to(REPO_ROOT).as_posix(),
                "page": page,
                "state": state,
                "size": size,
                "source_commit": source_commit,
                "platform": sys.platform,
                "theme": "light",
                "font_scale": 1.0,
                "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                "synthetic": True,
            }
        )

    manifest = {
        "version": __version__,
        "source_commit": source_commit,
        "language": "zh-CN",
        "synthetic": True,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "screenshots": screenshots,
    }
    (IMAGE_ROOT / "screenshot-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
