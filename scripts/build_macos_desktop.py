"""Build and validate the unsigned Apple Silicon desktop Alpha artifacts."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import plistlib
import platform
import shutil
import subprocess
import sys
import sysconfig
import tempfile


APP_NAME = "LLMInterviewLab"
VERSION = "0.4.0-alpha.3"
MINIMUM_MACOS = "12.0"


def run(*arguments: str | Path, **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(argument) for argument in arguments],
        check=True,
        text=True,
        **kwargs,
    )


def _deployment_environment() -> dict[str, str]:
    """Make the PySide deployment entry points visible without machine paths."""

    environment = dict(os.environ)
    scripts = Path(sysconfig.get_path("scripts"))
    environment["PATH"] = os.pathsep.join(
        item for item in (str(scripts), environment.get("PATH", "")) if item
    )
    # Nuitka otherwise puts a large cache under a user-specific location.  A
    # runner-local temporary directory keeps the build reproducible and avoids
    # filling a small home volume.  Callers may override this explicitly.
    environment.setdefault(
        "NUITKA_CACHE_DIR", str(Path(tempfile.gettempdir()) / "llm-lab-nuitka-cache")
    )
    Path(environment["NUITKA_CACHE_DIR"]).mkdir(parents=True, exist_ok=True)
    return environment


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    if sys.platform != "darwin" or platform.machine() != "arm64":
        raise SystemExit("macOS Apple Silicon build must run on an arm64 macOS host")
    root = Path(__file__).resolve().parents[1]
    output = root / "dist/desktop-macos"
    release = root / "dist/release-macos"
    shutil.rmtree(output, ignore_errors=True)
    shutil.rmtree(release, ignore_errors=True)
    output.mkdir(parents=True)
    release.mkdir(parents=True)

    run(
        sys.executable,
        root / "scripts/generate_desktop_icons.py",
        "--output",
        root / "dist/icons",
        "--macos",
        cwd=root,
    )
    deploy_environment = _deployment_environment()
    deploy = shutil.which("pyside6-deploy", path=deploy_environment["PATH"])
    if deploy is None:
        raise RuntimeError("pyside6-deploy is not available in the Python environment")
    # pyside6-deploy updates an existing spec with resolved local paths and
    # discovered plugins.  Run against an ignored copy so a normal local build
    # never dirties the checkout or leaks a developer path into a commit.
    spec_copy = root / "dist/.pysidedeploy-macos.spec"
    shutil.copy2(root / "scripts/pysidedeploy-macos.spec", spec_copy)
    try:
        run(
            deploy,
            "-c",
            spec_copy,
            "-f",
            cwd=root,
            env=deploy_environment,
        )
    finally:
        spec_copy.unlink(missing_ok=True)
    apps = list(output.glob("*.app"))
    if len(apps) != 1:
        raise RuntimeError(f"expected one .app bundle, found {len(apps)}")
    app = apps[0]
    expected_app = output / f"{APP_NAME}.app"
    if app != expected_app:
        app.rename(expected_app)
        app = expected_app

    plist_path = app / "Contents/Info.plist"
    with plist_path.open("rb") as stream:
        info = plistlib.load(stream)
    resources = app / "Contents/Resources"
    icon_candidates = sorted(resources.glob("*.icns"))
    if not icon_candidates:
        raise RuntimeError("application bundle does not contain an .icns icon")
    info.update(
        {
            "CFBundleName": "LLM Interview Lab",
            "CFBundleDisplayName": "LLM Interview Lab",
            "CFBundleIdentifier": "io.github.comistrymo.llminterviewlab",
            "CFBundleShortVersionString": "0.4.0",
            "CFBundleVersion": "3",
            "LSMinimumSystemVersion": MINIMUM_MACOS,
            "NSHighResolutionCapable": True,
            "LSMultipleInstancesProhibited": True,
            "CFBundleIconFile": icon_candidates[0].name,
        }
    )
    with plist_path.open("wb") as stream:
        plistlib.dump(info, stream, sort_keys=True)
    executable = app / "Contents/MacOS" / info["CFBundleExecutable"]

    run("plutil", "-lint", plist_path)
    architecture = run("file", executable, capture_output=True).stdout
    if "arm64" not in architecture:
        raise RuntimeError(f"application executable is not arm64: {architecture.strip()}")
    run("codesign", "--force", "--deep", "--sign", "-", app)
    run("codesign", "--verify", "--deep", "--strict", "--verbose=2", app)

    environment = {
        **os.environ,
        "LLM_LAB_PACKAGED": "1",
        "QT_QPA_PLATFORM": "offscreen",
        "QT_QUICK_BACKEND": "software",
    }
    with tempfile.TemporaryDirectory(prefix="llm-lab-macos-smoke-") as directory:
        environment["LLM_LAB_DESKTOP_DATA_ROOT"] = str(Path(directory) / "应用 数据")
        version = run(executable, "--version", capture_output=True, env=environment)
        if VERSION.replace("-alpha.", "a") not in version.stdout:
            raise RuntimeError(f"unexpected packaged version: {version.stdout.strip()}")
        run(executable, "--smoke-test", capture_output=True, env=environment, timeout=120)

    zip_path = release / "LLMInterviewLab-macOS-arm64.app.zip"
    run("ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", app, zip_path)
    dmg_path = release / "LLMInterviewLab-macOS-arm64.dmg"
    with tempfile.TemporaryDirectory(prefix="llm-lab-dmg-") as directory:
        staging = Path(directory) / "LLM Interview Lab"
        staging.mkdir()
        shutil.copytree(app, staging / app.name, symlinks=True)
        (staging / "Applications").symlink_to("/Applications", target_is_directory=True)
        run(
            "hdiutil",
            "create",
            "-volname",
            "LLM Interview Lab",
            "-srcfolder",
            staging,
            "-ov",
            "-format",
            "UDZO",
            dmg_path,
        )

    checksums = release / "SHA256SUMS.txt"
    checksums.write_text(
        "".join(
            f"{sha256(path)}  {path.name}\n" for path in (zip_path, dmg_path)
        ),
        encoding="utf-8",
    )
    print(f"app={app}")
    print(f"zip={zip_path}")
    print(f"dmg={dmg_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
