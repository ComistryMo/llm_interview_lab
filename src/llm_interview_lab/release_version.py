"""One version convention for source, desktop updates and build metadata."""
from __future__ import annotations

import re

from . import __version__

VERSION_PATTERN = re.compile(r"v?(\d+)\.(\d+)\.(\d+)(?:(?:-?)(alpha|a|beta|b|rc)[.-]?(\d+))?\Z")


def version_key(value: str) -> tuple[int, int, int, int, int]:
    match = VERSION_PATTERN.fullmatch(value)
    if not match:
        raise ValueError(f"unsupported release version: {value}")
    major, minor, patch, phase, number = match.groups()
    return (int(major), int(minor), int(patch),
            {"a": 0, "alpha": 0, "b": 1, "beta": 1, "rc": 2, None: 3}[phase], int(number or 0))


def release_metadata(version: str = __version__) -> dict[str, str | bool]:
    major, minor, patch, phase, number = version_key(version)
    base = f"{major}.{minor}.{patch}"
    suffix = ("alpha", "beta", "rc", "")[phase]
    tag = f"v{base}-{suffix}.{number}" if suffix else f"v{base}"
    # Apple's CFBundleVersion permits the a/b/fc development suffixes.
    # CFBundleVersion's first component is positive even while the marketing
    # version is 0.x. The fixed +1 mapping also preserves upgrade ordering.
    bundle_base = f"{major + 1}.{minor}.{patch}"
    bundle = bundle_base + (("a", "b", "fc")[phase] + str(number) if phase < 3 else "")
    return {"version": version, "tag": tag, "short_version": base,
            "bundle_version": bundle, "prerelease": phase < 3,
            "notes": f"docs/release-notes-{tag}.md"}
