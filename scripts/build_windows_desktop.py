"""Build the existing PySide standalone spec from a public-only Git snapshot.

No worktree cleanup or private Profile enumeration. Each output directory is
new; failed builds remain available for diagnosis instead of being erased.
"""
from __future__ import annotations

import argparse
import configparser
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import sysconfig
import tarfile
import xml.etree.ElementTree as ET
import zipfile

from llm_interview_lab.release_version import version_key
from release_metadata import check_source, sha256, write_build_metadata


def run(*args, **kwargs):
    return subprocess.run([str(value) for value in args], check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("dist/release"))
    parser.add_argument("--mingw", action="store_true", help="Use the existing MinGW toolchain instead of MSVC")
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    if os.name != "nt" or platform.machine().lower() not in {"amd64", "x86_64"}:
        parser.error("Windows x64 build host required")
    root = Path(__file__).resolve().parents[1]
    metadata = check_source(root)
    if subprocess.check_output(["git", "diff", "HEAD", "--name-only"], cwd=root, text=True).strip():
        raise RuntimeError("commit tracked changes before building a candidate")
    source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    snapshot = output / "source-snapshot"
    snapshot.mkdir()
    archive = output / "source.tar"
    public_paths = ("src", "curriculum", "coach", "workspace/schema", "workspace/templates",
                    "AGENTS.md", ".gitignore", "pyproject.toml", "LICENSE", "scripts/pysidedeploy.spec",
                    "scripts/generate_desktop_icons.py", "docs/desktop-app.md", "docs/third-party-notices.md", metadata["notes"])
    run("git", "archive", "--format=tar", f"--output={archive}", source_commit, *public_paths, cwd=root)
    # Archive is produced above from explicit repository-owned public paths.
    with tarfile.open(archive) as source:
        source.extractall(snapshot, filter="data")
    deployment = snapshot / "src/llm_interview_lab/desktop/deployment"
    if deployment.exists():
        raise RuntimeError("unexpected deployment files in the Git source snapshot")
    (snapshot / "dist").mkdir()
    config = configparser.ConfigParser()
    config.read(snapshot / "scripts/pysidedeploy.spec", encoding="utf-8")
    major, minor, patch, _, number = version_key(metadata["version"])
    config["nuitka"]["extra_args"] += f" --jobs={args.jobs} --file-version={major}.{minor}.{patch}.{number} --product-version={major}.{minor}.{patch}.{number}"
    # Keep PySide's finalizer and Nuitka's long-command entrypoint in agreement.
    config["nuitka"]["extra_args"] += " --output-folder-name=main --output-filename=LLMInterviewLab.exe"
    if args.mingw:
        config["nuitka"]["extra_args"] += " --mingw64"
    config_path = snapshot / "dist/pysidedeploy-candidate.spec"
    with config_path.open("w", encoding="utf-8") as stream:
        config.write(stream)
    environment = {**os.environ, "PYTHONUTF8": "1", "PYTHONPATH": str(snapshot / "src")}
    environment["PATH"] = str(Path(sysconfig.get_path("scripts"))) + os.pathsep + environment.get("PATH", "")
    environment.setdefault("NUITKA_CACHE_DIR", str(root / "dist/nuitka-cache"))
    run(sys.executable, snapshot / "scripts/generate_desktop_icons.py", "--output", "dist/icons", cwd=snapshot, env=environment)
    deploy = shutil.which("pyside6-deploy", path=environment["PATH"])
    if not deploy:
        raise RuntimeError("pyside6-deploy is unavailable")
    # PySide 6.11 compiles long Windows commands as deploy_main.py, but its
    # finalizer still looks for main.dist. Retain our private staging directory
    # and consume the actual Nuitka result; never let that mismatch erase it.
    run(deploy, "-c", config_path, "-f", "--keep-deployment-files", cwd=snapshot, env=environment)
    # pyside6-deploy can log a compiler exception and still return exit code 0.
    # An executable left before DLL/data collection is not a standalone bundle.
    report = snapshot / "desktop-nuitka-report.xml"
    if not report.is_file() or ET.parse(report).getroot().get("completion") != "yes":
        raise RuntimeError("Nuitka did not complete; inspect the retained build report and log")
    candidates = [deployment / name for name in ("main.dist", "deploy_main.dist")
                  if (deployment / name).is_dir()]
    if len(candidates) != 1:
        raise RuntimeError("build did not produce exactly one standalone directory; inspect retained deployment files")
    bundle_source = candidates[0]
    executables = list(bundle_source.glob("*.exe"))
    if len(executables) != 1:
        raise RuntimeError("build did not produce exactly one standalone executable; inspect the retained snapshot")
    bundle = output / "LLMInterviewLab"
    shutil.copytree(bundle_source, bundle)
    if executables[0].name != "LLMInterviewLab.exe":
        (bundle / executables[0].name).rename(bundle / "LLMInterviewLab.exe")
    for source, name in (("LICENSE", "LICENSE"), ("docs/third-party-notices.md", "THIRD_PARTY_NOTICES.md"), ("docs/desktop-app.md", "README.md")):
        shutil.copy2(snapshot / source, bundle / name)
    write_build_metadata(snapshot, bundle / "runtime_assets", source_commit=source_commit)
    shutil.copy2(snapshot / "desktop-nuitka-report.xml", output / "desktop-nuitka-report.xml")
    portable = output / "LLMInterviewLab-Windows-x64-portable.zip"
    with zipfile.ZipFile(portable, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for file in sorted(bundle.rglob("*")):
            if file.is_file():
                archive.write(file, file.relative_to(output))
    (output / "SHA256SUMS-Windows.txt").write_text(f"{sha256(portable)}  {portable.name}\n", encoding="utf-8")
    print(f"Candidate bundle: {bundle}\nPortable archive: {portable}")


if __name__ == "__main__":
    main()
