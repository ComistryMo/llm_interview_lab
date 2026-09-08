"""Check source/tag conventions and verify the exact cross-platform asset set."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

from llm_interview_lab.release_version import release_metadata


ASSETS = ("LLMInterviewLab-Windows-x64-portable.zip",
          "LLMInterviewLab-macOS-arm64.app.zip", "LLMInterviewLab-macOS-arm64.dmg")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_source(root: Path, tag: str | None = None) -> dict:
    metadata = release_metadata()
    declared = re.search(r'^version = "([^"]+)"$', (root / "pyproject.toml").read_text(encoding="utf-8"), re.M)
    if not declared or declared[1] != metadata["version"]:
        raise RuntimeError("pyproject and source versions differ")
    if not (root / metadata["notes"]).is_file():
        raise RuntimeError("release notes for this source version are missing")
    if tag is not None and tag != metadata["tag"]:
        raise RuntimeError("requested tag does not match the source version")
    return metadata


def write_build_metadata(root: Path, bundle_assets: Path, *, source_commit: str | None = None) -> None:
    metadata = check_source(root)
    if source_commit is None:
        source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        tracked_dirty = subprocess.check_output(["git", "diff", "HEAD", "--name-only"], cwd=root, text=True).strip()
        if tracked_dirty:
            raise RuntimeError("commit tracked source changes before producing a candidate bundle")
    # Windows passes the exact commit archived into its immutable public-only
    # source snapshot. Later worktree edits cannot change the snapshot's origin.
    metadata["source_commit"] = source_commit
    public_files = []
    for directory in ("curriculum", "coach", "workspace/schema", "workspace/templates"):
        public_files.extend(path for path in (root / directory).rglob("*")
                            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc")
    public_files += [root / name for name in ("AGENTS.md", ".gitignore", "pyproject.toml")]
    manifest = {path.relative_to(root).as_posix(): sha256(path) for path in sorted(public_files)}
    for relative, digest in manifest.items():
        if not (bundle_assets / relative).is_file() or sha256(bundle_assets / relative) != digest:
            raise RuntimeError(f"bundled public asset missing or changed: {relative}")
    metadata["public_files"] = manifest
    (bundle_assets / "BUILD-METADATA.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def assemble(downloads: Path, output: Path) -> None:
    """Refuse missing/duplicate/stale files instead of blessing new checksums."""
    files = {}
    manifests = {}
    for name in ASSETS:
        matches = list(downloads.rglob(name))
        if len(matches) != 1:
            raise RuntimeError(f"expected exactly one artifact: {name}")
        path = matches[0]
        manifest_name = "SHA256SUMS-Windows.txt" if "Windows" in name else "SHA256SUMS.txt"
        text = (path.parent / manifest_name).read_text(encoding="utf-8-sig")
        hashes = [line.split()[0].lower() for line in text.splitlines()
                  if len(line.split()) == 2 and line.split()[1] == name]
        if hashes != [sha256(path)]:
            raise RuntimeError(f"artifact checksum mismatch: {name}")
        files[name] = path
        manifests["SHA256SUMS-Windows.txt" if "Windows" in name else "SHA256SUMS-macOS.txt"] = path.parent / manifest_name
    output.mkdir(parents=True, exist_ok=False)
    for name, source in {**files, **manifests}.items():
        shutil.copy2(source, output / name)
    (output / "SHA256SUMS.txt").write_text("".join(f"{sha256(path)}  {name}\n" for name, path in files.items()), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag")
    parser.add_argument("--github-output", type=Path)
    parser.add_argument("--downloads", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--bundle-assets", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    metadata = check_source(root, args.tag)
    if args.downloads:
        if not args.output:
            parser.error("--downloads requires --output")
        assemble(args.downloads, args.output)
    if args.bundle_assets:
        write_build_metadata(root, args.bundle_assets)
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as stream:
            for name, value in metadata.items():
                stream.write(f"{name}={str(value).lower() if isinstance(value, bool) else value}\n")
    print(json.dumps(metadata, ensure_ascii=False))


if __name__ == "__main__":
    main()
