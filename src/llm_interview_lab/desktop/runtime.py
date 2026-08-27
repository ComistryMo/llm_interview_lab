"""Locate or provision the writable repository used by the desktop app."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys

from llm_interview_lab import __version__
from llm_interview_lab.workspace import WorkspaceError, find_repository_root


PUBLIC_DIRECTORIES = ("curriculum", "coach")
WORKSPACE_PUBLIC_DIRECTORIES = ("schema", "templates")
PUBLIC_FILES = ("AGENTS.md", ".gitignore")


def _bundle_root() -> Path:
    override = os.environ.get("LLM_LAB_BUNDLE_ROOT")
    if override:
        return Path(override).resolve()
    return Path(__file__).resolve().parent / "runtime_assets"


def _local_data_root() -> Path:
    override = os.environ.get("LLM_LAB_DESKTOP_DATA_ROOT")
    if override:
        return Path(override).resolve()
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        base = str(Path.home() / "AppData/Local")
    return Path(base).resolve() / "LLMInterviewLab"


def _copy_public_assets(bundle: Path, destination: Path) -> None:
    for name in PUBLIC_DIRECTORIES:
        source = bundle / name
        if not source.is_dir():
            raise WorkspaceError(f"desktop bundle is missing {name}")
        shutil.copytree(source, destination / name, dirs_exist_ok=True)
    workspace = destination / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    for name in WORKSPACE_PUBLIC_DIRECTORIES:
        source = bundle / "workspace" / name
        if not source.is_dir():
            raise WorkspaceError(f"desktop bundle is missing workspace/{name}")
        shutil.copytree(source, workspace / name, dirs_exist_ok=True)
    (workspace / "profiles").mkdir(exist_ok=True)
    for name in PUBLIC_FILES:
        source = bundle / name
        if not source.is_file():
            raise WorkspaceError(f"desktop bundle is missing {name}")
        shutil.copy2(source, destination / name)


def prepare_desktop_repository() -> Path:
    """Use a checkout when available, otherwise seed LocalAppData safely.

    Updates replace only bundled public assets.  ``workspace/profiles`` is
    never copied, removed, enumerated, or migrated by this function.
    """

    # An explicit desktop data root is authoritative. This keeps tests,
    # portable launches, and advanced deployments deterministic even when the
    # process happens to start below a source checkout.
    if "LLM_LAB_DESKTOP_DATA_ROOT" not in os.environ:
        try:
            return find_repository_root()
        except WorkspaceError:
            pass
    bundle = _bundle_root()
    destination = _local_data_root()
    marker = destination / ".llm-lab-standalone.json"
    installed_version = None
    if marker.is_file():
        try:
            installed_version = json.loads(marker.read_text(encoding="utf-8")).get(
                "version"
            )
        except (OSError, UnicodeError, json.JSONDecodeError):
            installed_version = None
    if installed_version != __version__:
        destination.mkdir(parents=True, exist_ok=True)
        _copy_public_assets(bundle, destination)
        marker.write_text(
            json.dumps(
                {"schema_version": 1, "version": __version__, "synthetic": True},
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    if getattr(sys, "frozen", False) or "__compiled__" in globals():
        os.environ["LLM_LAB_GRADER_EXECUTABLE"] = str(Path(sys.executable).resolve())
    return find_repository_root(destination)
