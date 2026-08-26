"""Create and verify a restricted handoff archive.

The exporter is deliberately fail-closed:

* only exact paths in a JSON allowlist are considered;
* every exported path must be tracked by Git;
* only small, regular UTF-8 text files are accepted;
* links, Windows reparse points, suspicious filenames, and likely secrets fail;
* files are read into memory once, hashed, and written with ``writestr``;
* personal training records require an explicit review acknowledgement.

An allowlist and automated checks reduce risk, but they cannot prove that text
is safe to disclose. Review the dry-run output and the archive manually.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
from typing import Any, Iterable, Mapping, Sequence
import unicodedata
import zipfile


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ALLOWLIST = "config/export/handoff.json"
MANIFEST_NAME = "MANIFEST.json"
MANIFEST_SCHEMA_VERSION = 1

MAX_FILE_BYTES = 1 * 1024 * 1024
MAX_TOTAL_BYTES = 10 * 1024 * 1024
MAX_FILES = 200
MAX_ALLOWLIST_BYTES = 256 * 1024

REVIEW_REQUIRED_ROOTS = frozenset({"state", "reviews", "progress", "notes"})
TEXT_SUFFIXES = frozenset(
    {
        ".cfg",
        ".ini",
        ".json",
        ".jsonl",
        ".md",
        ".py",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
    }
)
TEXT_BASENAMES = frozenset(
    {
        ".editorconfig",
        ".gitattributes",
        ".gitignore",
        "CODE_OF_CONDUCT",
        "CONTRIBUTING",
        "LICENSE",
        "Makefile",
        "README",
        "SECURITY",
    }
)
DENIED_SUFFIXES = frozenset(
    {
        ".7z",
        ".bin",
        ".ckpt",
        ".crt",
        ".der",
        ".gguf",
        ".gz",
        ".ipynb",
        ".jks",
        ".key",
        ".onnx",
        ".p12",
        ".pem",
        ".pfx",
        ".pt",
        ".pth",
        ".safetensors",
        ".tar",
        ".zip",
    }
)
DENIED_BASENAMES = frozenset(
    {
        ".env",
        "credentials",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
        "id_rsa",
        "secrets",
    }
)
WINDOWS_FORBIDDEN_PATH_CHARS = frozenset('<>:"\\|?*')
WINDOWS_RESERVED_STEMS = frozenset(
    {
        "aux",
        "clock$",
        "con",
        "nul",
        "prn",
        *(f"com{number}" for number in range(1, 10)),
        *(f"lpt{number}" for number in range(1, 10)),
    }
)

SECRET_PATTERNS = (
    (
        "private-key header",
        re.compile(
            r"-----BEGIN (?:RSA |DSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"
        ),
    ),
    (
        "GitHub token",
        re.compile(
            r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"
        ),
    ),
    (
        "OpenAI-style token",
        re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    ),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")),
    (
        "credential-bearing URL",
        re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s/@:]+:[^\s/@]+@", re.IGNORECASE),
    ),
    (
        "credential assignment",
        re.compile(
            r"(?im)^\s*(?:api[_-]?key|access[_-]?token|password|passwd|secret)"
            r"\s*[:=]\s*['\"]?"
            r"(?!<|\$\{|your[_-]|example|dummy|fake|redacted|none|null|\*{3})"
            r"\S{8,}"
        ),
    ),
    (
        "Windows user-home path",
        re.compile(r"\b[A-Za-z]:\\Users\\[^\\\s]+\\", re.IGNORECASE),
    ),
    (
        "POSIX user-home path",
        re.compile(r"/(?:home|Users)/[^/\s]+/"),
    ),
)

_BIDI_CONTROL_PATTERN = re.compile(r"[\u202a-\u202e\u2066-\u2069]")
_GIT_SHA_PATTERN = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


class ExportError(RuntimeError):
    """Raised when a handoff cannot be exported safely."""


@dataclass(frozen=True)
class GitSnapshot:
    """The repository state recorded in an archive manifest."""

    sha: str
    dirty: bool
    tracked_files: frozenset[str]


@dataclass(frozen=True)
class PreparedFile:
    """Validated file bytes retained in memory until archive creation."""

    path: str
    data: bytes
    sha256: str

    @property
    def size(self) -> int:
        return len(self.data)


@dataclass(frozen=True)
class ExportPlan:
    """A complete immutable export plan."""

    files: tuple[PreparedFile, ...]
    git_sha: str
    dirty: bool
    requires_review_acknowledgement: bool

    def manifest(self) -> dict[str, Any]:
        return {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "git_sha": self.git_sha,
            "dirty": self.dirty,
            "files": [
                {
                    "path": file.path,
                    "size": file.size,
                    "sha256": file.sha256,
                }
                for file in self.files
            ],
        }


def _validate_git_sha(value: str) -> str:
    if not isinstance(value, str):
        raise ExportError("Git SHA must be a string")
    normalized = value.strip().lower()
    if _GIT_SHA_PATTERN.fullmatch(normalized) is None:
        raise ExportError("Git SHA must be a full 40- or 64-character hash")
    return normalized


def _validate_relative_path(value: str, *, reserved_manifest: bool = True) -> str:
    if not isinstance(value, str) or not value:
        raise ExportError("allowlist paths must be non-empty strings")
    if value != value.strip():
        raise ExportError("allowlist paths cannot have surrounding whitespace")
    if "\\" in value:
        raise ExportError("allowlist paths must use forward slashes")
    if unicodedata.normalize("NFC", value) != value:
        raise ExportError("allowlist paths must use NFC Unicode normalization")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ExportError("allowlist paths cannot contain control characters")

    path = PurePosixPath(value)
    if path.is_absolute() or value.startswith("/"):
        raise ExportError("absolute paths are not allowed")
    if value.endswith("/") or any(part in {"", ".", ".."} for part in path.parts):
        raise ExportError("paths must identify a file without '.' or '..' components")
    if not path.parts:
        raise ExportError("allowlist paths must identify a file")
    if path.as_posix() != value:
        raise ExportError("paths must already be in canonical relative form")

    for part in path.parts:
        if any(character in WINDOWS_FORBIDDEN_PATH_CHARS for character in part):
            raise ExportError("paths contain a character unsafe on Windows")
        if part.endswith((" ", ".")):
            raise ExportError("path components cannot end with a space or period")
        if part.split(".", 1)[0].casefold() in WINDOWS_RESERVED_STEMS:
            raise ExportError("paths cannot use reserved Windows device names")

    normalized = path.as_posix()
    if reserved_manifest and normalized.casefold() == MANIFEST_NAME.casefold():
        raise ExportError(f"{MANIFEST_NAME} is reserved for the generated manifest")
    return normalized


def _collision_key(path: str) -> str:
    return unicodedata.normalize("NFC", path).casefold()


def _validate_unique_paths(paths: Iterable[str]) -> tuple[str, ...]:
    normalized_paths: list[str] = []
    seen: dict[str, str] = {}
    for raw_path in paths:
        path = _validate_relative_path(raw_path)
        key = _collision_key(path)
        previous = seen.get(key)
        if previous is not None:
            raise ExportError("allowlist paths collide after case/Unicode normalization")
        seen[key] = path
        normalized_paths.append(path)
    if not normalized_paths:
        raise ExportError("allowlist must contain at least one file")
    if len(normalized_paths) > MAX_FILES:
        raise ExportError(f"allowlist exceeds the {MAX_FILES}-file limit")
    return tuple(sorted(normalized_paths))


def _json_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ExportError("JSON objects cannot contain duplicate keys")
        result[key] = value
    return result


def _decode_utf8_text(data: bytes, *, label: str) -> str:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ExportError(f"{label} is not valid UTF-8 text") from error
    if "\x00" in text:
        raise ExportError(f"{label} contains a NUL byte")
    if _BIDI_CONTROL_PATTERN.search(text):
        raise ExportError(f"{label} contains bidirectional control characters")
    for character in text:
        if ord(character) < 32 and character not in "\t\n\r":
            raise ExportError(f"{label} contains non-text control characters")
    return text


def _load_allowlist(repo_root: Path, allowlist_path: str) -> tuple[str, ...]:
    relative = _validate_relative_path(allowlist_path)
    candidate = _safe_regular_file(repo_root, relative)
    data = _read_regular_file_bounded(
        candidate,
        relative,
        limit=MAX_ALLOWLIST_BYTES,
    )
    text = _decode_utf8_text(data, label="allowlist")
    try:
        payload = json.loads(text, object_pairs_hook=_json_without_duplicate_keys)
    except (json.JSONDecodeError, TypeError) as error:
        raise ExportError("allowlist is not valid JSON") from error

    if not isinstance(payload, dict) or set(payload) != {"schema_version", "files"}:
        raise ExportError("allowlist must contain exactly schema_version and files")
    if (
        isinstance(payload["schema_version"], bool)
        or not isinstance(payload["schema_version"], int)
        or payload["schema_version"] != MANIFEST_SCHEMA_VERSION
    ):
        raise ExportError("unsupported allowlist schema_version")
    files = payload["files"]
    if not isinstance(files, list) or not all(isinstance(item, str) for item in files):
        raise ExportError("allowlist files must be a JSON array of strings")
    return _validate_unique_paths(files)


def _is_link_or_reparse(file_stat: os.stat_result | Any) -> bool:
    if stat.S_ISLNK(file_stat.st_mode):
        return True
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    attributes = getattr(file_stat, "st_file_attributes", 0)
    return bool(attributes & reparse_flag)


def _resolved_repo_root(repo_root: Path) -> Path:
    root = Path(repo_root)
    try:
        root_stat = os.lstat(root)
    except OSError as error:
        raise ExportError("repository root is not accessible") from error
    if _is_link_or_reparse(root_stat):
        raise ExportError("repository root cannot be a link or reparse point")
    if not stat.S_ISDIR(root_stat.st_mode):
        raise ExportError("repository root must be a directory")
    try:
        return root.resolve(strict=True)
    except OSError as error:
        raise ExportError("repository root cannot be resolved") from error


def _safe_regular_file(repo_root: Path, relative_path: str) -> Path:
    root = _resolved_repo_root(repo_root)
    normalized = _validate_relative_path(relative_path)
    current = root
    parts = PurePosixPath(normalized).parts
    for index, part in enumerate(parts):
        current = current / part
        try:
            file_stat = os.lstat(current)
        except OSError as error:
            raise ExportError(f"allowlisted file is missing: {normalized}") from error
        if _is_link_or_reparse(file_stat):
            raise ExportError(f"links and reparse points are forbidden: {normalized}")
        is_final = index == len(parts) - 1
        if not is_final and not stat.S_ISDIR(file_stat.st_mode):
            raise ExportError(f"allowlisted parent is not a directory: {normalized}")
        if is_final and not stat.S_ISREG(file_stat.st_mode):
            raise ExportError(f"allowlisted path is not a regular file: {normalized}")
    try:
        current.resolve(strict=True).relative_to(root)
    except (OSError, ValueError) as error:
        raise ExportError(f"allowlisted path escapes the repository: {normalized}") from error
    return current


def _read_regular_file_bounded(path: Path, label: str, *, limit: int) -> bytes:
    """Read one checked regular file without ever buffering more than limit+1."""

    try:
        before = os.lstat(path)
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ExportError(f"allowlisted file cannot be opened: {label}") from error
    try:
        opened = os.fstat(descriptor)
        if _is_link_or_reparse(before) or _is_link_or_reparse(opened):
            raise ExportError(f"links and reparse points are forbidden: {label}")
        if not stat.S_ISREG(opened.st_mode):
            raise ExportError(f"allowlisted path is not a regular file: {label}")
        before_identity = (before.st_dev, before.st_ino)
        opened_identity = (opened.st_dev, opened.st_ino)
        if before_identity != opened_identity:
            raise ExportError(f"allowlisted file changed while being opened: {label}")
        if opened.st_size > limit:
            raise ExportError(f"allowlisted file exceeds the size limit: {label}")

        chunks: list[bytes] = []
        remaining = limit + 1
        while remaining > 0:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > limit:
            raise ExportError(f"allowlisted file exceeds the size limit: {label}")
        after = os.fstat(descriptor)
        stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        if any(getattr(opened, field) != getattr(after, field) for field in stable_fields):
            raise ExportError(f"allowlisted file changed while being read: {label}")
        return data
    finally:
        os.close(descriptor)


def _validate_text_filename(path: str) -> None:
    pure_path = PurePosixPath(path)
    basename = pure_path.name
    casefolded_basename = basename.casefold()
    suffix = pure_path.suffix.casefold()

    if suffix in DENIED_SUFFIXES:
        raise ExportError(f"forbidden file type in allowlist: {path}")
    if casefolded_basename in DENIED_BASENAMES or casefolded_basename.startswith(
        (".env.", "credentials.", "secrets.")
    ):
        raise ExportError(f"sensitive filename is forbidden: {path}")
    if suffix not in TEXT_SUFFIXES and basename not in TEXT_BASENAMES:
        raise ExportError(f"file type is not on the UTF-8 text allowlist: {path}")


def _scan_for_secrets(path: str, text: str) -> None:
    for label, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            raise ExportError(f"possible {label} detected in {path}")


def _run_git(repo_root: Path, *arguments: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *arguments],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as error:
        raise ExportError("Git is required to create a handoff archive") from error
    if result.returncode != 0:
        command = " ".join(arguments[:2])
        raise ExportError(f"Git command failed: {command}")
    return result.stdout


def _git_snapshot(repo_root: Path) -> GitSnapshot:
    root = _resolved_repo_root(repo_root)
    tracked_raw = _run_git(root, "ls-files", "-z")
    try:
        tracked_text = tracked_raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ExportError("Git returned a non-UTF-8 tracked path") from error
    tracked = frozenset(path for path in tracked_text.split("\x00") if path)
    if not tracked:
        raise ExportError("repository has no tracked files; commit a reviewed baseline first")

    sha_raw = _run_git(root, "rev-parse", "--verify", "HEAD")
    try:
        sha = _validate_git_sha(sha_raw.decode("ascii"))
    except UnicodeDecodeError as error:
        raise ExportError("Git returned an invalid HEAD hash") from error
    dirty = bool(
        _run_git(root, "status", "--porcelain=v1", "-z", "--untracked-files=normal")
    )
    return GitSnapshot(sha=sha, dirty=dirty, tracked_files=tracked)


def _git_hash_bytes(repo_root: Path, path: str, data: bytes) -> str:
    """Hash bytes with Git's path-aware clean filters."""

    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "hash-object", f"--path={path}", "--stdin"],
            input=data,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as error:
        raise ExportError("Git is required to verify handoff contents") from error
    if result.returncode != 0:
        raise ExportError("Git could not hash an allowlisted file")
    try:
        return _validate_git_sha(result.stdout.decode("ascii"))
    except UnicodeDecodeError as error:
        raise ExportError("Git returned an invalid content hash") from error


def _validate_snapshot(snapshot: GitSnapshot) -> GitSnapshot:
    if not isinstance(snapshot.dirty, bool):
        raise ExportError("Git dirty state must be boolean")
    tracked = frozenset(snapshot.tracked_files)
    if not tracked or not all(isinstance(path, str) for path in tracked):
        raise ExportError("Git snapshot must contain tracked paths")
    return GitSnapshot(
        sha=_validate_git_sha(snapshot.sha),
        dirty=snapshot.dirty,
        tracked_files=tracked,
    )


def prepare_export(
    *,
    repo_root: Path = REPO_ROOT,
    allowlist_path: str = DEFAULT_ALLOWLIST,
    git_snapshot: GitSnapshot | None = None,
) -> ExportPlan:
    """Validate and read every allowlisted file into memory."""

    root = _resolved_repo_root(repo_root)
    allowlisted_paths = _load_allowlist(root, allowlist_path)
    snapshot = _validate_snapshot(git_snapshot or _git_snapshot(root))

    prepared: list[PreparedFile] = []
    total_bytes = 0
    requires_acknowledgement = False

    for path in allowlisted_paths:
        if path not in snapshot.tracked_files:
            raise ExportError(f"allowlisted file is not tracked by Git: {path}")
        _validate_text_filename(path)
        candidate = _safe_regular_file(root, path)
        data = _read_regular_file_bounded(candidate, path, limit=MAX_FILE_BYTES)
        _safe_regular_file(root, path)
        text = _decode_utf8_text(data, label=path)
        _scan_for_secrets(path, text)

        total_bytes += len(data)
        if total_bytes > MAX_TOTAL_BYTES:
            raise ExportError("allowlisted files exceed the total size limit")
        if PurePosixPath(path).parts[0].casefold() in REVIEW_REQUIRED_ROOTS:
            requires_acknowledgement = True
        prepared.append(
            PreparedFile(
                path=path,
                data=data,
                sha256=hashlib.sha256(data).hexdigest(),
            )
        )

    if git_snapshot is None:
        final_snapshot = _git_snapshot(root)
        if final_snapshot != snapshot:
            raise ExportError("repository state changed while preparing the handoff")
        if not snapshot.dirty:
            for file in prepared:
                head_hash = _run_git(root, "rev-parse", f"HEAD:{file.path}")
                try:
                    expected = _validate_git_sha(head_hash.decode("ascii"))
                except UnicodeDecodeError as error:
                    raise ExportError("Git returned an invalid HEAD content hash") from error
                if _git_hash_bytes(root, file.path, file.data) != expected:
                    raise ExportError(
                        "clean repository content disagrees with HEAD during export"
                    )

    return ExportPlan(
        files=tuple(prepared),
        git_sha=snapshot.sha,
        dirty=snapshot.dirty,
        requires_review_acknowledgement=requires_acknowledgement,
    )


def _manifest_bytes(plan: ExportPlan) -> bytes:
    return (
        json.dumps(
            plan.manifest(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _zip_info(path: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    return info


def _validate_output_path(repo_root: Path, relative_path: str) -> Path:
    root = _resolved_repo_root(repo_root)
    normalized = _validate_relative_path(relative_path, reserved_manifest=False)
    pure_path = PurePosixPath(normalized)
    if not pure_path.parts or pure_path.parts[0] != "dist" or pure_path.suffix != ".zip":
        raise ExportError("archive output must be a .zip file under dist/")

    parent = root
    for part in pure_path.parts[:-1]:
        parent = parent / part
        if parent.exists():
            parent_stat = os.lstat(parent)
            if _is_link_or_reparse(parent_stat):
                raise ExportError("archive output directory cannot be a link or reparse point")
            if not stat.S_ISDIR(parent_stat.st_mode):
                raise ExportError("archive output parent must be a directory")
        else:
            try:
                parent.mkdir()
            except OSError as error:
                raise ExportError("archive output directory cannot be created") from error
            parent_stat = os.lstat(parent)
            if _is_link_or_reparse(parent_stat):
                raise ExportError("archive output directory cannot be a link or reparse point")

    output = root.joinpath(*pure_path.parts)
    try:
        output.parent.resolve(strict=True).relative_to(root)
    except (OSError, ValueError) as error:
        raise ExportError("archive output escapes the repository") from error
    return output


def create_archive(
    plan: ExportPlan,
    *,
    repo_root: Path = REPO_ROOT,
    output_path: str,
    acknowledge_review: bool = False,
) -> Path:
    """Write an already prepared plan atomically and verify it before return."""

    if plan.requires_review_acknowledgement and not acknowledge_review:
        raise ExportError(
            "state/reviews/progress/notes require --acknowledge-review before writing"
        )

    output = _validate_output_path(repo_root, output_path)
    try:
        reservation = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise ExportError("archive output already exists; refusing to overwrite it") from error
    except OSError as error:
        raise ExportError("archive output cannot be created") from error
    else:
        os.close(reservation)

    temp_name: str | None = None
    completed = False
    try:
        descriptor, temp_name = tempfile.mkstemp(
            prefix=".handoff-",
            suffix=".tmp",
            dir=output.parent,
        )
        os.close(descriptor)
        temp_path = Path(temp_name)
        with zipfile.ZipFile(
            temp_path,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for file in plan.files:
                archive.writestr(_zip_info(file.path), file.data)
            archive.writestr(_zip_info(MANIFEST_NAME), _manifest_bytes(plan))
        verify_archive(temp_path)
        if _validate_output_path(repo_root, output_path) != output:
            raise ExportError("archive output path changed during creation")
        os.replace(temp_path, output)
        temp_name = None
        verify_archive(output)
        completed = True
        return output
    except (OSError, zipfile.BadZipFile) as error:
        raise ExportError("archive creation or verification failed") from error
    finally:
        if temp_name is not None:
            Path(temp_name).unlink(missing_ok=True)
        if not completed:
            output.unlink(missing_ok=True)


def _validate_manifest(payload: Any) -> tuple[dict[str, Any], tuple[Mapping[str, Any], ...]]:
    expected_keys = {"schema_version", "git_sha", "dirty", "files"}
    if not isinstance(payload, dict) or set(payload) != expected_keys:
        raise ExportError("archive manifest has unexpected fields")
    if (
        isinstance(payload["schema_version"], bool)
        or not isinstance(payload["schema_version"], int)
        or payload["schema_version"] != MANIFEST_SCHEMA_VERSION
    ):
        raise ExportError("archive manifest schema_version is unsupported")
    payload["git_sha"] = _validate_git_sha(payload["git_sha"])
    if not isinstance(payload["dirty"], bool):
        raise ExportError("archive manifest dirty field must be boolean")
    files = payload["files"]
    if not isinstance(files, list) or not files or len(files) > MAX_FILES:
        raise ExportError("archive manifest files must be a non-empty bounded list")

    paths: list[str] = []
    validated_entries: list[Mapping[str, Any]] = []
    total_size = 0
    for entry in files:
        if not isinstance(entry, dict) or set(entry) != {"path", "size", "sha256"}:
            raise ExportError("archive manifest file entry has unexpected fields")
        path = _validate_relative_path(entry["path"])
        _validate_text_filename(path)
        size = entry["size"]
        sha256 = entry["sha256"]
        if isinstance(size, bool) or not isinstance(size, int) or not 0 <= size <= MAX_FILE_BYTES:
            raise ExportError("archive manifest contains an invalid file size")
        if not isinstance(sha256, str) or _SHA256_PATTERN.fullmatch(sha256) is None:
            raise ExportError("archive manifest contains an invalid SHA-256")
        total_size += size
        if total_size > MAX_TOTAL_BYTES:
            raise ExportError("archive manifest exceeds the total size limit")
        paths.append(path)
        validated_entries.append(entry)

    normalized_paths = _validate_unique_paths(paths)
    if tuple(paths) != normalized_paths:
        raise ExportError("archive manifest file entries must be sorted")
    return payload, tuple(validated_entries)


def verify_archive(archive_path: Path) -> dict[str, Any]:
    """Verify an archive without extracting it and return its manifest."""

    try:
        archive_stat = os.lstat(archive_path)
    except OSError as error:
        raise ExportError("archive does not exist") from error
    if _is_link_or_reparse(archive_stat) or not stat.S_ISREG(archive_stat.st_mode):
        raise ExportError("archive must be a regular file, not a link or reparse point")

    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            if archive.comment:
                raise ExportError("archive comments are not allowed")
            members = archive.infolist()
            names = [member.filename for member in members]
            if len(names) != len(set(names)):
                raise ExportError("archive contains duplicate member names")
            if MANIFEST_NAME not in names:
                raise ExportError(f"archive is missing {MANIFEST_NAME}")
            if len(members) > MAX_FILES + 1:
                raise ExportError("archive contains too many members")

            collision_keys: set[str] = set()
            payload_size = 0
            for member in members:
                name = _validate_relative_path(
                    member.filename,
                    reserved_manifest=member.filename != MANIFEST_NAME,
                )
                key = _collision_key(name)
                if key in collision_keys:
                    raise ExportError("archive member names collide after normalization")
                collision_keys.add(key)
                unix_mode = (member.external_attr >> 16) & 0xFFFF
                if unix_mode and not stat.S_ISREG(unix_mode):
                    raise ExportError("archive contains a non-regular member")
                if member.is_dir() or member.flag_bits & 0x1:
                    raise ExportError("archive directories and encrypted members are forbidden")
                if member.comment or member.extra:
                    raise ExportError("archive members cannot contain hidden metadata")
                if member.compress_type != zipfile.ZIP_DEFLATED:
                    raise ExportError("archive members must use DEFLATE compression")
                limit = MAX_ALLOWLIST_BYTES if name == MANIFEST_NAME else MAX_FILE_BYTES
                if member.file_size > limit:
                    raise ExportError("archive member exceeds its size limit")
                if name != MANIFEST_NAME:
                    payload_size += member.file_size
                    if payload_size > MAX_TOTAL_BYTES:
                        raise ExportError("archive payload exceeds the total size limit")

            manifest_data = archive.read(MANIFEST_NAME)
            manifest_text = _decode_utf8_text(manifest_data, label="archive manifest")
            try:
                manifest_payload = json.loads(
                    manifest_text,
                    object_pairs_hook=_json_without_duplicate_keys,
                )
            except (json.JSONDecodeError, TypeError) as error:
                raise ExportError("archive manifest is not valid JSON") from error
            manifest, entries = _validate_manifest(manifest_payload)

            expected_names = {MANIFEST_NAME, *(entry["path"] for entry in entries)}
            if set(names) != expected_names:
                raise ExportError("archive members do not exactly match the manifest")
            for entry in entries:
                data = archive.read(entry["path"])
                if len(data) != entry["size"]:
                    raise ExportError("archive member size does not match the manifest")
                if hashlib.sha256(data).hexdigest() != entry["sha256"]:
                    raise ExportError("archive member hash does not match the manifest")
                text = _decode_utf8_text(data, label=entry["path"])
                _scan_for_secrets(entry["path"], text)
            return manifest
    except zipfile.BadZipFile as error:
        raise ExportError("archive is not a valid ZIP file") from error


def _default_output_path(plan: ExportPlan) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dirty_suffix = "-dirty" if plan.dirty else ""
    return f"dist/handoff-{timestamp}-{plan.git_sha[:12]}{dirty_suffix}.zip"


def _print_dry_run(plan: ExportPlan) -> None:
    print("Dry run: no archive was created.")
    print(f"Git SHA: {plan.git_sha}")
    print(f"Dirty: {str(plan.dirty).lower()}")
    print(
        "Review acknowledgement required to write: "
        f"{str(plan.requires_review_acknowledgement).lower()}"
    )
    print("Files:")
    for file in plan.files:
        print(f"- {file.path} ({file.size} bytes, sha256={file.sha256})")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and list files without creating dist/ or an archive",
    )
    action.add_argument(
        "--verify",
        metavar="ARCHIVE",
        help="verify a repository-relative archive without extracting it",
    )
    parser.add_argument(
        "--allowlist",
        default=DEFAULT_ALLOWLIST,
        help=f"repository-relative exact allowlist (default: {DEFAULT_ALLOWLIST})",
    )
    parser.add_argument(
        "--output",
        help="repository-relative output under dist/; refuses overwrite",
    )
    parser.add_argument(
        "--acknowledge-review",
        action="store_true",
        help="confirm manual review of state/reviews/progress/notes before writing",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    repo_root: Path = REPO_ROOT,
    git_snapshot: GitSnapshot | None = None,
) -> int:
    """CLI entry point; injectable arguments keep pre-commit tests deterministic."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        root = _resolved_repo_root(repo_root)
        if args.verify:
            if args.output:
                raise ExportError("--output cannot be used with --verify")
            relative_archive = _validate_relative_path(
                args.verify,
                reserved_manifest=False,
            )
            archive = _safe_regular_file(root, relative_archive)
            manifest = verify_archive(archive)
            print(f"Verified: {relative_archive}")
            print(f"Files: {len(manifest['files'])}")
            print(f"Git SHA: {manifest['git_sha']}")
            print(f"Dirty: {str(manifest['dirty']).lower()}")
            return 0

        plan = prepare_export(
            repo_root=root,
            allowlist_path=args.allowlist,
            git_snapshot=git_snapshot,
        )
        if args.dry_run:
            _print_dry_run(plan)
            return 0

        output_path = args.output or _default_output_path(plan)
        output = create_archive(
            plan,
            repo_root=root,
            output_path=output_path,
            acknowledge_review=args.acknowledge_review,
        )
        relative_output = output.relative_to(root).as_posix()
        print(f"Created: {relative_output}")
        print(f"Included files: {len(plan.files)}")
        print("Inspect the manifest and archive manually before sharing.")
        return 0
    except (ExportError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
