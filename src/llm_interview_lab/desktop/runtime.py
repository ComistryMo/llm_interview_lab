"""Locate or provision writable, platform-native desktop application data."""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
import platform
from uuid import uuid4

from llm_interview_lab import __version__
from llm_interview_lab.workspace import WorkspaceError, find_repository_root


PUBLIC_DIRECTORIES = ("curriculum", "coach")
WORKSPACE_PUBLIC_DIRECTORIES = ("schema", "templates")
PUBLIC_FILES = ("AGENTS.md", ".gitignore")
STANDALONE_MARKER = ".llm-lab-standalone.json"
MIGRATION_MARKER = ".llm-lab-desktop-migration.json"
# Public assets can change between two builds that carry the same alpha
# version (for example, when a session schema learns a new provenance kind).
# Keep a small explicit revision in the standalone marker so an existing app
# data directory receives that public-asset update without ever touching the
# private ``workspace/profiles`` tree.
PUBLIC_ASSET_REVISION = "role-interview-dynamic-stages-v3"

# Error messages can contain paths that are not one of the well-known roots
# (for example a pytest temporary directory).  Keep bootstrap diagnostics
# useful while replacing those paths before they reach a local log that a user
# may attach to an issue.  The span intentionally accepts spaces (valid in
# both Windows and POSIX filenames) and stops at common sentence delimiters.
_ABSOLUTE_PATH_RE = re.compile(
    r"(?<![\w])(?:[A-Za-z]:[\\/]|\\\\)[^<>\"'()\[\]{},;!?\r\n]+"
    r"|(?<![:\w/])/(?:[^<>\"'()\[\]{},;!?\r\n]+)",
)
_PATH_TRAILING_PUNCTUATION = ".,;:!?)]}"


def bootstrap_log_path() -> Path:
    """Return a log path that is available before Qt or the repository starts."""

    override = os.environ.get("LLM_LAB_BOOTSTRAP_LOG")
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        root = Path(base).expanduser() if base else Path.home() / "AppData" / "Local"
    else:
        root = Path(tempfile.gettempdir())
    return (root / "LLMInterviewLab" / "logs" / "bootstrap.log").resolve()


def _sanitized_bootstrap_message(error: BaseException) -> str:
    message = " ".join(str(error).split())
    private_roots = {
        str(Path.home()),
        str(Path.cwd()),
        os.environ.get("LLM_LAB_DESKTOP_DATA_ROOT", ""),
        os.environ.get("LLM_LAB_BUNDLE_ROOT", ""),
    }
    for value in sorted((item for item in private_roots if item), key=len, reverse=True):
        message = message.replace(value, "<local-path>")

    def replace_path(match: re.Match[str]) -> str:
        value = match.group(0)
        trailing = value[len(value.rstrip()) :]
        value = value.rstrip()
        while value and value[-1] in _PATH_TRAILING_PUNCTUATION:
            trailing = value[-1] + trailing
            value = value[:-1]
        return "<local-path>" + trailing

    message = _ABSOLUTE_PATH_RE.sub(replace_path, message)
    return message[:400]


def record_bootstrap_event(
    startup_stage: str,
    *,
    error: BaseException | None = None,
    runtime_assets_found: bool | None = None,
    first_window_ms: int | None = None,
) -> Path:
    """Append a privacy-minimized startup event; logging failure never hides the UI."""

    path = bootstrap_log_path()
    build_commit = (
        os.environ.get("LLM_LAB_BUILD_COMMIT")
        or os.environ.get("GITHUB_SHA")
        or "unknown"
    )
    # Keep diagnostics useful without putting a user's checkout or AppData
    # path in a log that they may attach to an issue.
    payload: dict[str, object] = {
        "version": __version__,
        "app_version": __version__,
        "build_commit": build_commit[:40],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "startup_stage": startup_stage,
        "executable_path": Path(sys.executable).name,
        "app_data_path": "<app-data>",
        "platform": sys.platform,
        "python_runtime": platform.python_version(),
        "exception_type": None,
        "sanitized_exception": "",
    }
    if error is not None:
        payload["exception_type"] = type(error).__name__
        sanitized = _sanitized_bootstrap_message(error)
        payload["message"] = sanitized
        payload["sanitized_exception"] = sanitized
    if runtime_assets_found is not None:
        payload["runtime_assets_found"] = runtime_assets_found
    if first_window_ms is not None:
        payload["first_window_ms"] = first_window_ms
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError:
        pass
    return path


def runtime_assets_available() -> bool:
    root = _bundle_root()
    return all(
        path.exists()
        for path in (
            root / "curriculum",
            root / "coach",
            root / "workspace" / "schema",
            root / "workspace" / "templates",
        )
    )


def show_startup_error(code: str, reason: str, log_path: Path) -> None:
    """Show a native Windows error before Qt is available, with a CI-safe fallback."""

    message = f"{reason}\n\n错误编号：{code}\n日志位置：{log_path}"
    platform_name = os.environ.get("QT_QPA_PLATFORM", "").lower()
    suppressed = os.environ.get("LLM_LAB_SUPPRESS_STARTUP_DIALOG") == "1"
    if sys.platform == "win32" and platform_name not in {"offscreen", "minimal"} and not suppressed:
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(
                None,
                message,
                "LLM Interview Lab 启动失败",
                0x00000010,
            )
            return
        except (AttributeError, OSError):
            pass
    print(f"错误：{message}", file=sys.stderr)


def _bundle_root() -> Path:
    override = os.environ.get("LLM_LAB_BUNDLE_ROOT")
    if override:
        return Path(override).resolve()
    if not is_packaged_desktop():
        try:
            return find_repository_root(Path(__file__))
        except WorkspaceError:
            pass  # An installed wheel can still carry runtime_assets below.
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
    installed_asset_revision = None
    if marker.is_file():
        try:
            marker_value = json.loads(marker.read_text(encoding="utf-8"))
            if isinstance(marker_value, dict):
                installed_version = marker_value.get("version")
                installed_asset_revision = marker_value.get("public_asset_revision")
        except (OSError, UnicodeError, json.JSONDecodeError):
            installed_version = None
            installed_asset_revision = None
    if (
        installed_version != __version__
        or installed_asset_revision != PUBLIC_ASSET_REVISION
    ):
        destination.mkdir(parents=True, exist_ok=True)
        _copy_public_assets(bundle, destination)
        marker.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "version": __version__,
                    "public_asset_revision": PUBLIC_ASSET_REVISION,
                    "synthetic": True,
                },
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
