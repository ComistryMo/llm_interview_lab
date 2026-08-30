"""Inspect both macOS release formats for bundle contracts and private data."""

from __future__ import annotations

import argparse
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import zipfile


FORBIDDEN = (
    "workspace/profiles/",
    "maintainer-v1",
    "oracle_submission.py",
    "private_tests",
    "events.jsonl",
    "submission.py",
    ".git/",
    ".env",
)


def assert_names_are_public(names: list[str]) -> None:
    normalized = [name.replace("\\", "/").lower() for name in names]
    for fragment in FORBIDDEN:
        if any(fragment.lower() in name for name in normalized):
            raise RuntimeError(f"artifact contains forbidden private path: {fragment}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("app_zip", type=Path)
    parser.add_argument("dmg", type=Path)
    args = parser.parse_args()
    with zipfile.ZipFile(args.app_zip) as archive:
        names = archive.namelist()
        assert_names_are_public(names)
        plist_name = next(
            name for name in names if name.endswith(".app/Contents/Info.plist")
        )
        info = plistlib.loads(archive.read(plist_name))
    expected = {
        "CFBundleIdentifier": "io.github.comistrymo.llminterviewlab",
        "CFBundleShortVersionString": "0.4.0",
        "CFBundleVersion": "3",
        "LSMinimumSystemVersion": "12.0",
    }
    for key, value in expected.items():
        if info.get(key) != value:
            raise RuntimeError(f"unexpected {key}: {info.get(key)!r}")
    icon_name = info.get("CFBundleIconFile")
    if not isinstance(icon_name, str) or not icon_name.endswith(".icns"):
        raise RuntimeError("application bundle does not declare an .icns icon")
    if not any(
        name.endswith(f".app/Contents/Resources/{icon_name}")
        for name in names
    ):
        raise RuntimeError("application bundle icon file is missing")

    with tempfile.TemporaryDirectory(prefix="llm-lab-dmg-check-") as directory:
        mount = Path(directory) / "mount"
        mount.mkdir()
        subprocess.run(
            ["hdiutil", "attach", str(args.dmg), "-mountpoint", str(mount), "-nobrowse", "-readonly"],
            check=True,
            capture_output=True,
            text=True,
        )
        try:
            assert_names_are_public(
                [path.relative_to(mount).as_posix() for path in mount.rglob("*")]
            )
            if not any(mount.glob("*.app")):
                raise RuntimeError("DMG does not contain an application bundle")
        finally:
            subprocess.run(
                ["hdiutil", "detach", str(mount)], check=True, capture_output=True, text=True
            )
    print("macOS artifact privacy and bundle contracts: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
