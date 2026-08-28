"""Locate or provision writable, platform-native desktop application data."""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import shutil
import sys
from datetime import datetime, timezone
from uuid import uuid4

from llm_interview_lab import __version__
from llm_interview_lab.workspace import WorkspaceError, find_repository_root


PUBLIC_DIRECTORIES = ("curriculum", "coach")
WORKSPACE_PUBLIC_DIRECTORIES = ("schema", "templates")
PUBLIC_FILES = ("AGENTS.md", ".gitignore")
STANDALONE_MARKER = ".llm-lab-standalone.json"
MIGRATION_MARKER = ".llm-lab-desktop-migration.json"


def _bundle_root() -> Path:
    override = os.environ.get("LLM_LAB_BUNDLE_ROOT")
    if override:
        return Path(override).resolve()
    # Nuitka/PySide can place data beside the executable (standalone app) or
    # under ``Contents/Resources`` (macOS bundle).  Do not assume that the
    # compiled module's ``__file__`` points at either location.
    module_root = Path(__file__).resolve().parent
    executable_root = Path(sys.executable).resolve().parent
    candidates = (
        module_root / "runtime_assets",
        executable_root / "runtime_assets",
        executable_root.parent / "Resources" / "runtime_assets",
        executable_root.parent / "Resources",
    )
    for candidate in candidates:
        if (candidate / "curriculum").is_dir() and (candidate / "coach").is_dir():
            return candidate
    return module_root / "runtime_assets"


def is_packaged_desktop() -> bool:
    """Return whether the process is a deployed desktop executable."""

    override = os.environ.get("LLM_LAB_PACKAGED")
    if override is not None:
        return override.strip().lower() in {"1", "true", "yes"}
    return bool(getattr(sys, "frozen", False) or "__compiled__" in globals())


def _qt_app_data_root() -> Path:
    """Use Qt's platform data location after QGuiApplication is configured."""

    try:
        from PySide6.QtCore import QStandardPaths
    except ImportError as error:  # pragma: no cover - desktop extra owns this path
        raise WorkspaceError("desktop data location requires the desktop extra") from error
    value = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    if not value:
        raise WorkspaceError("the operating system did not provide an application data location")
    return Path(value).expanduser().resolve()


def desktop_data_root() -> Path:
    """Return the writable root used by a packaged desktop application."""

    override = os.environ.get("LLM_LAB_DESKTOP_DATA_ROOT")
    if override:
        return Path(override).resolve()
    return _qt_app_data_root()


def desktop_log_root(repository_root: Path) -> Path:
    """Keep diagnostic logs local and outside tracked source files."""

    override = os.environ.get("LLM_LAB_DESKTOP_LOG_ROOT")
    root = Path(override).resolve() if override else repository_root.resolve() / "logs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def configure_desktop_logging(repository_root: Path) -> Path:
    """Configure a small rotating local log without payloads or absolute paths."""

    root = desktop_log_root(repository_root)
    path = root / "desktop.log"
    logger = logging.getLogger("llm_interview_lab.desktop")
    if not any(
        isinstance(handler, RotatingFileHandler)
        and Path(getattr(handler, "baseFilename", "")) == path
        for handler in logger.handlers
    ):
        handler = RotatingFileHandler(
            path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return path


def _legacy_windows_data_root() -> Path | None:
    override = os.environ.get("LLM_LAB_LEGACY_DESKTOP_DATA_ROOT")
    if override:
        return Path(override).resolve()
    if sys.platform != "win32":
        return None
    base = os.environ.get("LOCALAPPDATA")
    return (Path(base).resolve() / "LLMInterviewLab") if base else None


def _profiles_have_data(root: Path) -> bool:
    profiles = root / "workspace" / "profiles"
    return profiles.is_dir() and any(
        child.name != ".gitkeep" for child in profiles.iterdir()
    )


def detect_legacy_desktop_data(destination: Path) -> Path | None:
    """Return the Alpha.1 Windows data root only when user data exists there."""

    if not is_packaged_desktop() and "LLM_LAB_LEGACY_DESKTOP_DATA_ROOT" not in os.environ:
        return None
    source = _legacy_windows_data_root()
    if source is None or source == destination.resolve() or not source.is_dir():
        return None
    if not (source / STANDALONE_MARKER).is_file() or not _profiles_have_data(source):
        return None
    if _profiles_have_data(destination):
        return None
    return source


def _assert_plain_tree(root: Path) -> None:
    for path in root.rglob("*"):
        if path.is_symlink():
            raise WorkspaceError("旧版数据包含符号链接，已停止自动迁移")


def _tree_sha256(root: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def migrate_legacy_desktop_data(source: Path, destination: Path) -> Path:
    """Copy Alpha.1 Profiles after consent, keep a verified backup, never delete source."""

    source = source.resolve()
    destination = destination.resolve()
    expected = detect_legacy_desktop_data(destination)
    if expected is None or expected != source:
        raise WorkspaceError("没有可安全迁移的旧版桌面数据，或新目录已经包含学习档案")
    source_profiles = source / "workspace" / "profiles"
    destination_profiles = destination / "workspace" / "profiles"
    _assert_plain_tree(source_profiles)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    staging = destination / f".migration-{uuid4().hex}"
    backup = destination / "migration-backups" / f"alpha1-{timestamp}"
    try:
        staged_profiles = staging / "profiles"
        shutil.copytree(source_profiles, staged_profiles)
        source_digest = _tree_sha256(source_profiles)
        if _tree_sha256(staged_profiles) != source_digest:
            raise WorkspaceError("旧版数据复制校验失败，源数据保持不变")
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(staged_profiles, backup / "profiles")
        if _tree_sha256(backup / "profiles") != source_digest:
            raise WorkspaceError("迁移备份校验失败，源数据保持不变")
        if destination_profiles.exists():
            if any(destination_profiles.iterdir()):
                raise WorkspaceError("新数据目录已经包含学习档案，未执行迁移")
            destination_profiles.rmdir()
        os.replace(staged_profiles, destination_profiles)
        (destination / MIGRATION_MARKER).write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "from_version": "0.4.0-alpha.1",
                    "profile_tree_sha256": source_digest,
                    "backup_relpath": backup.relative_to(destination).as_posix(),
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return backup
    finally:
        shutil.rmtree(staging, ignore_errors=True)


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
    """Use a checkout in source mode, otherwise seed platform app data safely.

    Updates replace only bundled public assets.  ``workspace/profiles`` is
    never copied, removed, enumerated, or migrated by this function.
    """

    # An explicit desktop data root is authoritative. This keeps tests,
    # portable launches, and advanced deployments deterministic even when the
    # process happens to start below a source checkout.
    if (
        "LLM_LAB_DESKTOP_DATA_ROOT" not in os.environ
        and not is_packaged_desktop()
    ):
        try:
            return find_repository_root()
        except WorkspaceError:
            pass
    bundle = _bundle_root()
    destination = desktop_data_root()
    marker = destination / STANDALONE_MARKER
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
    # Only a genuinely frozen executable understands the private worker
    # protocol used by the packaged grader.  Tests and source launches may
    # set ``LLM_LAB_PACKAGED`` to exercise the platform data path, but their
    # ``sys.executable`` is the ordinary Python interpreter; pointing the
    # grader at it would make Python interpret ``--grader-worker`` as an
    # unknown option and contaminate subsequent in-process tests.
    if getattr(sys, "frozen", False) or "__compiled__" in globals():
        os.environ["LLM_LAB_GRADER_EXECUTABLE"] = str(Path(sys.executable).resolve())
    return find_repository_root(destination)
