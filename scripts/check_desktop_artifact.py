"""Fail release builds that are unusable or contain private workspace paths."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

from PySide6.QtGui import QImage


FORBIDDEN_REPORT_FRAGMENTS = (
    "workspace/profiles/maintainer",
    "workspace\\profiles\\maintainer",
    "oracle_submission.py",
    "private_tests",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("--bundle-root", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    executable = args.executable.resolve()
    if not executable.is_file() or executable.suffix.lower() != ".exe":
        raise SystemExit("desktop executable is missing")
    bundle_root = (args.bundle_root or executable.parent).resolve()
    if not bundle_root.is_dir():
        raise SystemExit("standalone desktop bundle is missing")
    try:
        executable.relative_to(bundle_root)
    except ValueError as error:
        raise SystemExit("desktop executable must be inside the standalone bundle") from error
    for relative in (
        "runtime_assets/curriculum",
        "runtime_assets/coach",
        "runtime_assets/workspace/schema",
        "runtime_assets/workspace/templates",
    ):
        if not (bundle_root / relative).exists():
            raise SystemExit(f"standalone desktop bundle is missing {relative}")
    report = args.report.read_text(encoding="utf-8", errors="replace").lower()
    for fragment in FORBIDDEN_REPORT_FRAGMENTS:
        if fragment.lower() in report:
            raise SystemExit(f"desktop build report contains forbidden content: {fragment}")
    if args.archive:
        with zipfile.ZipFile(args.archive) as archive:
            names = [name.replace("\\", "/").lower() for name in archive.namelist()]
        for required in (
            "llminterviewlab/llminterviewlab.exe",
            "llminterviewlab/runtime_assets/curriculum/",
            "llminterviewlab/runtime_assets/coach/",
        ):
            if not any(name == required or name.startswith(required) for name in names):
                raise SystemExit(f"desktop archive is missing standalone content: {required}")
        for fragment in (
            *FORBIDDEN_REPORT_FRAGMENTS,
            "events.jsonl",
            "submission.py",
            ".git/",
            ".env",
        ):
            if any(fragment.replace("\\", "/").lower() in name for name in names):
                raise SystemExit(f"desktop archive contains forbidden content: {fragment}")
    scratch_parent_value = os.environ.get("LLM_LAB_BUILD_TEMP")
    scratch_parent = (
        Path(scratch_parent_value).resolve()
        if scratch_parent_value
        else Path(tempfile.gettempdir()).resolve()
    )
    scratch_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="llm-lab-desktop-smoke-", dir=scratch_parent
    ) as directory:
        root = Path(directory)
        environment = {
            **os.environ,
            "LOCALAPPDATA": str(root / "local-app-data"),
            # This test directory can itself live below the source checkout.
            # Force the executable through its standalone path so the smoke
            # cannot accidentally reuse repository-local public assets.
            "LLM_LAB_DESKTOP_DATA_ROOT": str(
                root / "local-app-data" / "LLMInterviewLab"
            ),
            "TEMP": str(root),
            "TMP": str(root),
            "QT_QPA_PLATFORM": "offscreen",
            "QT_QUICK_BACKEND": "software",
        }
        version = subprocess.run(
            [str(executable), "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=root,
            env=environment,
        )
        if version.returncode or "llm-lab-gui" not in version.stdout:
            raise SystemExit(
                f"desktop --version failed: {version.stdout}{version.stderr}"
            )
        smoke_cycle = subprocess.run(
            [str(executable), "--smoke-test"],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=root,
            env=environment,
        )
        if smoke_cycle.returncode or '"status": "ok"' not in smoke_cycle.stdout:
            raise SystemExit(
                f"desktop event-loop smoke failed: {smoke_cycle.stdout}{smoke_cycle.stderr}"
            )
        screenshot = root / "onboarding.png"
        smoke = subprocess.run(
            [
                str(executable),
                "--screenshot",
                str(screenshot),
                "--screenshot-page",
                "onboarding",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
            env=environment,
            cwd=root,
        )
        screenshot_size = screenshot.stat().st_size if screenshot.is_file() else 0
        image = QImage(str(screenshot)) if screenshot.is_file() else QImage()
        sampled_colors = {
            image.pixelColor(x, y).rgba()
            for x in range(0, image.width(), max(1, image.width() // 8))
            for y in range(0, image.height(), max(1, image.height() // 8))
        }
        screenshot_valid = (
            not image.isNull()
            and image.width() >= 1100
            and image.height() >= 700
            and len(sampled_colors) >= 2
        )
        if smoke.returncode or not screenshot_valid:
            raise SystemExit(
                "desktop GUI smoke failed: "
                f"returncode={smoke.returncode} screenshot_bytes={screenshot_size} "
                f"dimensions={image.width()}x{image.height()} "
                f"sampled_colors={len(sampled_colors)}\n"
                + smoke.stdout
                + smoke.stderr
            )
        profiles = root / "local-app-data/LLMInterviewLab/workspace/profiles"
        if not profiles.is_dir() or any(profiles.iterdir()):
            raise SystemExit("desktop smoke unexpectedly packaged or created a real Profile")
        bootstrap = root / "local-app-data/LLMInterviewLab/logs/bootstrap.log"
        if not bootstrap.is_file():
            raise SystemExit("desktop bootstrap log was not created")
        events = bootstrap.read_text(encoding="utf-8")
        if '"startup_stage": "first_window"' not in events:
            raise SystemExit("desktop bootstrap log did not record the first window")
    print(f"desktop standalone artifact OK: {bundle_root.name}/{executable.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
