"""Promote an already-tested desktop build; documentation changes need no rebuild."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from llm_interview_lab.release_version import release_metadata

ROOT = Path(__file__).resolve().parents[1]
REPO = "ComistryMo/llm_interview_lab"
REQUIRED_JOBS = {
    *(f"{os} / Python {version}" for os in ("ubuntu-latest", "windows-latest")
      for version in ("3.10", "3.11", "3.12")),
    "Ubuntu / Python 3.11 / CPU PyTorch", "中文文档契约 / Python 3.11",
    "Windows Desktop / Python 3.11", "macOS 15 arm64 Desktop / Python 3.11",
}
PUBLICATION_FILES = {
    "README.md", "README.en.md", "CHANGELOG.md", "CONTRIBUTING.md",
    "SECURITY.md", "CODE_OF_CONDUCT.md", "PLANS.md",
    "HOTFIX_FINAL_ZH.md", "REAL_USER_ITERATION_FINAL_ZH.md",
    ".github/workflows/publish.yml", ".github/release-manifest.json",
    "scripts/verify_release_promotion.py",
}


def check_changed_paths(paths: list[str]) -> None:
    blocked = [p for p in paths if p not in PUBLICATION_FILES
               and not p.startswith(("docs/", "plans/", "tests/"))]
    if blocked:
        raise RuntimeError(f"Build inputs changed; a new verified build is required: {blocked}")


def check_ci(manifest: dict, run: dict, jobs: dict, artifacts: dict) -> None:
    if (run["id"] != manifest["run_id"] or run["head_sha"] != manifest["source_commit"]
            or run["repository"]["full_name"] != REPO
            or run["path"] != ".github/workflows/ci.yml"
            or run["event"] not in {"push", "workflow_dispatch"}
            or run["status"] != "completed" or run["conclusion"] != "success"):
        raise RuntimeError("The pinned source CI did not pass")
    results = {job["name"]: job["conclusion"] for job in jobs["jobs"]}
    if any(results.get(name) != "success" for name in REQUIRED_JOBS):
        raise RuntimeError("Every core, documentation and desktop gate must pass")
    available = {str(item["id"]): item for item in artifacts["artifacts"]}
    for artifact_id, name in manifest["artifacts"].items():
        item = available.get(artifact_id, {})
        if item.get("name") != name or item.get("expired", True):
            raise RuntimeError(f"Verified artifact missing or expired: {name}")


def check_assets(manifest: dict, directory: Path) -> None:
    for name, expected in manifest["assets"].items():
        digest = hashlib.sha256()
        with (directory / name).open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != expected:
            raise RuntimeError(f"Published asset differs from the accepted build: {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--check-ci", action="store_true")
    parser.add_argument("--assets", type=Path)
    args = parser.parse_args()
    manifest = json.loads((ROOT / ".github/release-manifest.json").read_text("utf-8"))
    if args.tag != manifest["tag"] or args.tag != release_metadata()["tag"]:
        raise RuntimeError("Tag, source version and accepted build do not match")
    subprocess.run(["git", "merge-base", "--is-ancestor", manifest["source_commit"], "HEAD"], cwd=ROOT, check=True)
    changes = subprocess.check_output(
        ["git", "diff", "--name-only", "--no-renames", manifest["source_commit"], "HEAD"],
        cwd=ROOT, text=True, encoding="utf-8").splitlines()
    check_changed_paths(changes)
    if args.check_ci:
        def api(suffix: str) -> dict:
            return json.loads(subprocess.check_output(
                ["gh", "api", f"repos/{REPO}/actions/runs/{manifest['run_id']}{suffix}"],
                text=True, encoding="utf-8"))
        check_ci(manifest, api(""), api("/jobs?filter=latest&per_page=100"), api("/artifacts?per_page=100"))
    if args.assets:
        check_assets(manifest, args.assets)
    print(json.dumps({"tag": args.tag, "build_source": manifest["source_commit"],
                      "ci_checked": args.check_ci, "assets_checked": bool(args.assets)}))


if __name__ == "__main__":
    main()
