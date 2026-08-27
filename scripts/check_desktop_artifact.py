"""Fail release builds that are unusable or contain private workspace paths."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile


FORBIDDEN_REPORT_FRAGMENTS = (
    "workspace/profiles/maintainer",
    "workspace\\profiles\\maintainer",
    "oracle_submission.py",
    "private_tests",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    executable = args.executable.resolve()
    if not executable.is_file() or executable.suffix.lower() != ".exe":
        raise SystemExit("desktop executable is missing")
    report = args.report.read_text(encoding="utf-8", errors="replace").lower()
    for fragment in FORBIDDEN_REPORT_FRAGMENTS:
        if fragment.lower() in report:
            raise SystemExit(f"desktop build report contains forbidden content: {fragment}")
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
        screenshot = root / "home.png"
        smoke = subprocess.run(
            [
                str(executable),
                "--screenshot",
                str(screenshot),
                "--screenshot-page",
                "home",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
            env=environment,
            cwd=root,
        )
        if smoke.returncode or not screenshot.is_file() or screenshot.stat().st_size < 10_000:
            raise SystemExit(
                "desktop GUI smoke failed: " + smoke.stdout + smoke.stderr
            )
        profiles = root / "local-app-data/LLMInterviewLab/workspace/profiles"
        if not profiles.is_dir() or any(profiles.iterdir()):
            raise SystemExit("desktop smoke unexpectedly packaged or created a real Profile")
    print(f"desktop artifact OK: {executable.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
