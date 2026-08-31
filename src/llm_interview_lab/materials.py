"""Private, profile-scoped career materials with explicit AI access consent."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any, Iterable, Mapping
from uuid import uuid4
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from jsonschema import Draft202012Validator

from .workspace import (
    WorkspaceError,
    ensure_profile_path_is_safe,
    ensure_profile_is_ignored,
    load_profile,
    profile_paths,
)


MAX_MATERIAL_BYTES = 20 * 1024 * 1024
MAX_TEXT_SNAPSHOT_CHARS = 200_000
MATERIAL_KINDS = frozenset(
    {
        "resume",
        "career_intent",
        "internship",
        "project",
        "paper",
        "competition",
        "interview_question",
        "experience",
        "research",
        "job_description",
        "portfolio",
        "other",
    }
)
TEXT_SUFFIXES = frozenset({".md", ".txt", ".json", ".yaml", ".yml"})
OPAQUE_SUFFIXES = frozenset({".pdf", ".docx"})
ALLOWED_SUFFIXES = TEXT_SUFFIXES | OPAQUE_SUFFIXES
MATERIAL_ID_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")


class MaterialError(RuntimeError):
    """Raised when a private material operation would violate its contract."""


@dataclass(frozen=True)
class MaterialRecord:
    id: str
    kind: str
    relative_path: str
    sha256: str
    size_bytes: int
    title: str
    tags: tuple[str, ...]
    ai_access: bool
    text_snapshot_relative_path: str | None = None
    text_snapshot_sha256: str | None = None
    text_snapshot_source_sha256: str | None = None
    text_snapshot_format: str | None = None

    @property
    def opaque(self) -> bool:
        """Whether the stored format is intentionally not parsed by the project."""

        return PurePosixPath(self.relative_path).suffix in OPAQUE_SUFFIXES

    def as_dict(self) -> dict[str, Any]:
        value = {
            "id": self.id,
            "kind": self.kind,
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "title": self.title,
            "tags": list(self.tags),
            "ai_access": self.ai_access,
        }
        if self.text_snapshot_relative_path is not None:
            value["text_snapshot"] = {
                "relative_path": self.text_snapshot_relative_path,
                "sha256": self.text_snapshot_sha256,
                "source_sha256": self.text_snapshot_source_sha256,
                "format": self.text_snapshot_format,
            }
        return value


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise MaterialError(f"material manifest contains duplicate JSON key: {key}")
        value[key] = item
    return value


def _is_obvious_link(path: Path) -> bool:
    try:
        file_stat = os.lstat(path)
    except OSError:
        return False
    attributes = getattr(file_stat, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(file_stat.st_mode) or bool(attributes & reparse_flag)


def _reject_linked_components(path: Path) -> None:
    current = path.absolute()
    while True:
        if _is_obvious_link(current):
            raise MaterialError("material path must not use a symlink or reparse point")
        if current.parent == current:
            return
        current = current.parent


def _schema_path(repo_root: Path) -> Path:
    return repo_root / "workspace/schema/material.schema.json"


def _manifest_path(repo_root: Path, profile_id: str) -> Path:
    return profile_paths(repo_root, profile_id).materials_root / "manifest.json"


def _safe_profile_path(
    repo_root: Path,
    profile_id: str,
    candidate: Path,
    *,
    must_exist: bool = False,
) -> Path:
    try:
        return ensure_profile_path_is_safe(
            repo_root, profile_id, candidate, must_exist=must_exist
        )
    except WorkspaceError as error:
        raise MaterialError(str(error)) from error


def _load_schema(repo_root: Path) -> dict[str, Any]:
    try:
        schema = json.loads(_schema_path(repo_root).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise MaterialError("material schema cannot be read") from error
    if not isinstance(schema, dict):
        raise MaterialError("material schema must be a JSON object")
    return schema


def _validate_manifest(repo_root: Path, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MaterialError("material manifest must be a JSON object")
    errors = sorted(
        Draft202012Validator(_load_schema(repo_root)).iter_errors(value),
        key=lambda item: list(item.path),
    )
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "<root>"
        raise MaterialError(f"invalid material manifest at {location}: {errors[0].message}")
    identifiers = [item["id"] for item in value["materials"]]
    relative_paths = [item["relative_path"] for item in value["materials"]]
    if len(identifiers) != len(set(identifiers)):
        raise MaterialError("material manifest contains duplicate material IDs")
    if len(relative_paths) != len(set(relative_paths)):
        raise MaterialError("material manifest contains duplicate storage paths")
    return value


def _load_manifest(repo_root: Path, profile_id: str) -> dict[str, Any]:
    paths = profile_paths(repo_root, profile_id)
    load_profile(paths, repo_root)
    manifest = _manifest_path(repo_root, profile_id)
    _safe_profile_path(repo_root, profile_id, paths.materials_root)
    if not paths.materials_root.exists():
        return {"schema_version": 1, "materials": []}
    if not paths.materials_root.is_dir():
        raise MaterialError("Profile materials path is invalid")
    _safe_profile_path(repo_root, profile_id, manifest)
    if _is_obvious_link(manifest):
        raise MaterialError("material manifest must be a regular, unlinked file")
    if not manifest.exists():
        return {"schema_version": 1, "materials": []}
    if not manifest.is_file():
        raise MaterialError("material manifest must be a regular, unlinked file")
    try:
        value = json.loads(
            manifest.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except MaterialError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise MaterialError("material manifest cannot be read") from error
    return _validate_manifest(repo_root, value)


def _record(value: Mapping[str, Any]) -> MaterialRecord:
    snapshot = value.get("text_snapshot")
    if not isinstance(snapshot, Mapping):
        snapshot = {}
    return MaterialRecord(
        id=str(value["id"]),
        kind=str(value["kind"]),
        relative_path=str(value["relative_path"]),
        sha256=str(value["sha256"]),
        size_bytes=int(value["size_bytes"]),
        title=str(value["title"]),
        tags=tuple(str(tag) for tag in value["tags"]),
        ai_access=bool(value["ai_access"]),
        text_snapshot_relative_path=(
            str(snapshot["relative_path"]) if snapshot.get("relative_path") else None
        ),
        text_snapshot_sha256=(
            str(snapshot["sha256"]) if snapshot.get("sha256") else None
        ),
        text_snapshot_source_sha256=(
            str(snapshot["source_sha256"]) if snapshot.get("source_sha256") else None
        ),
        text_snapshot_format=(
            str(snapshot["format"]) if snapshot.get("format") else None
        ),
    )


def _normalize_extracted_text(value: str) -> str:
    lines = [line.rstrip() for line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    normalized = "\n".join(lines).strip()
    if not normalized:
        raise MaterialError(
            "未提取到可读文本；如果这是扫描 PDF，请先在本机完成 OCR，或仅作为本地附件保存"
        )
    if len(normalized) > MAX_TEXT_SNAPSHOT_CHARS:
        raise MaterialError(
            f"提取文本超过 {MAX_TEXT_SNAPSHOT_CHARS} 个字符；请先在本机裁剪或脱敏后再导入"
        )
    return normalized + "\n"


def _extract_pdf_text(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise MaterialError(
            "PDF 文本提取组件不可用；请安装当前版本的完整桌面依赖，或先转为 UTF-8 文本"
        ) from error
    try:
        reader = PdfReader(BytesIO(content), strict=False)
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as error:
        raise MaterialError("PDF 无法读取；请确认文件未加密且内容完整") from error
    return _normalize_extracted_text("\n\n".join(pages))


def _extract_docx_text(content: bytes) -> str:
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

    def paragraph_text(element: ElementTree.Element) -> str:
        return "".join(
            node.text or "" for node in element.iter(f"{namespace}t")
        ).strip()

    try:
        with ZipFile(BytesIO(content)) as archive:
            document = archive.read("word/document.xml")
    except (BadZipFile, KeyError, OSError) as error:
        raise MaterialError("DOCX 无法读取；请确认文件不是损坏或加密的文档") from error
    try:
        root = ElementTree.fromstring(document)
    except ElementTree.ParseError as error:
        raise MaterialError("DOCX 正文结构无效") from error
    body = root.find(f"{namespace}body")
    if body is None:
        raise MaterialError("DOCX 不包含可读正文")
    blocks: list[str] = []
    for child in body:
        if child.tag == f"{namespace}p":
            text = paragraph_text(child)
            if text:
                blocks.append(text)
        elif child.tag == f"{namespace}tbl":
            rows: list[str] = []
            for row in child.findall(f"{namespace}tr"):
                cells = [
                    " ".join(
                        value
                        for value in (paragraph_text(item) for item in cell.findall(f"{namespace}p"))
                        if value
                    )
                    for cell in row.findall(f"{namespace}tc")
                ]
                if any(cells):
                    rows.append("\t".join(cells))
            if rows:
                blocks.append("\n".join(rows))
    return _normalize_extracted_text("\n\n".join(blocks))


def _extract_text_snapshot(content: bytes, suffix: str) -> tuple[str, str]:
    if suffix == ".pdf":
        return _extract_pdf_text(content), "pdf_text"
    if suffix == ".docx":
        return _extract_docx_text(content), "docx_text"
    raise MaterialError("this material format does not need a text snapshot")


def _resolve_stored_path(repo_root: Path, profile_id: str, record: MaterialRecord) -> Path:
    paths = profile_paths(repo_root, profile_id)
    pure = PurePosixPath(record.relative_path)
    if (
        pure.is_absolute()
        or not pure.parts
        or "\\" in record.relative_path
        or any(part in {"", ".", ".."} for part in pure.parts)
    ):
        raise MaterialError("material manifest contains an unsafe relative path")
    candidate = paths.root.joinpath(*pure.parts)
    _safe_profile_path(repo_root, profile_id, paths.materials_root, must_exist=True)
    _safe_profile_path(repo_root, profile_id, candidate, must_exist=True)
    _reject_linked_components(candidate)
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(paths.materials_root.resolve(strict=True))
    except (OSError, ValueError) as error:
        raise MaterialError("stored material is missing or outside the Profile materials directory") from error
    if not resolved.is_file():
        raise MaterialError("stored material must be a regular file")
    try:
        content = resolved.read_bytes()
    except OSError as error:
        raise MaterialError("stored material cannot be read") from error
    if len(content) != record.size_bytes or hashlib.sha256(content).hexdigest() != record.sha256:
        raise MaterialError(f"stored material content does not match manifest: {record.id}")
    if record.ai_access and not record.opaque:
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise MaterialError("AI-readable text materials must be UTF-8") from error
    if record.ai_access and record.opaque:
        _resolve_text_snapshot_path(repo_root, profile_id, record)
    return resolved


def _resolve_text_snapshot_path(
    repo_root: Path, profile_id: str, record: MaterialRecord
) -> Path:
    relative_path = record.text_snapshot_relative_path
    if (
        relative_path is None
        or record.text_snapshot_sha256 is None
        or record.text_snapshot_source_sha256 != record.sha256
    ):
        raise MaterialError(
            "PDF / DOCX 没有与当前原文件 SHA 绑定的文本快照，不能授权给 AI"
        )
    pure = PurePosixPath(relative_path)
    if (
        pure.is_absolute()
        or not pure.parts
        or "\\" in relative_path
        or any(part in {"", ".", ".."} for part in pure.parts)
    ):
        raise MaterialError("material text snapshot contains an unsafe relative path")
    paths = profile_paths(repo_root, profile_id)
    candidate = paths.root.joinpath(*pure.parts)
    _safe_profile_path(repo_root, profile_id, candidate, must_exist=True)
    _reject_linked_components(candidate)
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(paths.materials_root.resolve(strict=True))
        content = resolved.read_bytes()
    except (OSError, ValueError) as error:
        raise MaterialError("material text snapshot is missing or outside this Profile") from error
    if not resolved.is_file():
        raise MaterialError("material text snapshot must be a regular file")
    if hashlib.sha256(content).hexdigest() != record.text_snapshot_sha256:
        raise MaterialError("material text snapshot does not match its manifest")
    try:
        content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise MaterialError("material text snapshot must be UTF-8") from error
    return resolved


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _atomic_write_manifest(path: Path, value: Mapping[str, Any]) -> None:
    content = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    _atomic_write(path, content)


def _normalize_tags(tags: Iterable[str]) -> tuple[str, ...]:
    if isinstance(tags, (str, bytes)):
        raise MaterialError("material tags must be an iterable of strings")
    normalized: list[str] = []
    for tag in tags:
        if not isinstance(tag, str) or not tag.strip():
            raise MaterialError("material tags must be non-empty strings")
        value = tag.strip()
        if value in normalized:
            raise MaterialError("material tags must be unique")
        normalized.append(value)
    if len(normalized) > 20 or any(len(tag) > 64 for tag in normalized):
        raise MaterialError("material tags exceed the manifest limits")
    return tuple(normalized)


def _validate_material_id(material_id: str) -> str:
    if not isinstance(material_id, str) or MATERIAL_ID_RE.fullmatch(material_id) is None:
        raise MaterialError(
            "material ID must start with a lowercase letter and contain only lowercase letters, digits, or hyphens"
        )
    return material_id


def add_material(
    repo_root: Path,
    profile_id: str,
    source_path: str | Path,
    *,
    kind: str,
    title: str | None = None,
    tags: Iterable[str] = (),
    ai_access: bool = False,
    material_id: str | None = None,
) -> MaterialRecord:
    """Copy one user-selected file into one explicit ignored Profile."""

    paths = profile_paths(repo_root, profile_id)
    load_profile(paths, repo_root)
    ensure_profile_is_ignored(repo_root, profile_id)
    _safe_profile_path(repo_root, profile_id, paths.materials_root)
    if not paths.materials_root.exists():
        try:
            paths.materials_root.mkdir()
        except OSError as error:
            raise MaterialError("Profile materials path cannot be created") from error
    _safe_profile_path(
        repo_root, profile_id, paths.materials_root, must_exist=True
    )
    if kind not in MATERIAL_KINDS:
        raise MaterialError(f"unsupported material kind: {kind}")
    if type(ai_access) is not bool:
        raise MaterialError("ai_access must be a boolean")
    source = Path(source_path)
    _reject_linked_components(source)
    if not source.exists() or not source.is_file():
        raise MaterialError("material source must be a regular file")
    suffix = source.suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise MaterialError("material file type is not supported")
    try:
        stated_size = source.stat().st_size
    except OSError as error:
        raise MaterialError("material source cannot be inspected") from error
    if stated_size > MAX_MATERIAL_BYTES:
        raise MaterialError("material exceeds the 20 MiB size limit")
    try:
        content = source.read_bytes()
    except OSError as error:
        raise MaterialError("material source cannot be read") from error
    if len(content) > MAX_MATERIAL_BYTES:
        raise MaterialError("material exceeds the 20 MiB size limit")
    snapshot_text: str | None = None
    snapshot_format: str | None = None
    if suffix in TEXT_SUFFIXES:
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise MaterialError("AI-readable text materials must be UTF-8") from error
    elif ai_access:
        try:
            snapshot_text, snapshot_format = _extract_text_snapshot(content, suffix)
        except MaterialError:
            raise

    identifier = _validate_material_id(material_id or f"material-{uuid4().hex[:12]}")
    normalized_title = source.stem if title is None else title
    if not isinstance(normalized_title, str) or not normalized_title.strip():
        raise MaterialError("material title must be a non-empty string")
    normalized_title = normalized_title.strip()
    if len(normalized_title) > 200:
        raise MaterialError("material title exceeds 200 characters")
    normalized_tags = _normalize_tags(tags)

    manifest = _load_manifest(repo_root, profile_id)
    if any(item["id"] == identifier for item in manifest["materials"]):
        raise MaterialError(f"material ID already exists: {identifier}")
    files_root = paths.materials_root / "files"
    _safe_profile_path(repo_root, profile_id, files_root)
    if _is_obvious_link(paths.materials_root) or (
        paths.materials_root.exists() and not paths.materials_root.is_dir()
    ):
        raise MaterialError("Profile materials path is invalid")
    if _is_obvious_link(files_root) or (files_root.exists() and not files_root.is_dir()):
        raise MaterialError("Profile material files path must not be linked")
    try:
        files_root.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise MaterialError("Profile material files path cannot be created") from error
    _safe_profile_path(repo_root, profile_id, files_root, must_exist=True)
    relative_path = f"materials/files/{identifier}{suffix}"
    destination = paths.root.joinpath(*PurePosixPath(relative_path).parts)
    _safe_profile_path(repo_root, profile_id, destination)
    if destination.exists() or _is_obvious_link(destination):
        raise MaterialError("material destination already exists")

    source_sha256 = hashlib.sha256(content).hexdigest()
    snapshot_bytes = snapshot_text.encode("utf-8") if snapshot_text is not None else None
    snapshot_relative_path = (
        f"materials/text/{identifier}.txt" if snapshot_bytes is not None else None
    )
    record = MaterialRecord(
        id=identifier,
        kind=kind,
        relative_path=relative_path,
        sha256=source_sha256,
        size_bytes=len(content),
        title=normalized_title,
        tags=normalized_tags,
        ai_access=ai_access,
        text_snapshot_relative_path=snapshot_relative_path,
        text_snapshot_sha256=(
            hashlib.sha256(snapshot_bytes).hexdigest()
            if snapshot_bytes is not None
            else None
        ),
        text_snapshot_source_sha256=(
            source_sha256 if snapshot_bytes is not None else None
        ),
        text_snapshot_format=snapshot_format,
    )
    updated = {
        "schema_version": 1,
        "materials": sorted(
            [*manifest["materials"], record.as_dict()],
            key=lambda item: item["id"],
        ),
    }
    _validate_manifest(repo_root, updated)
    snapshot_destination = (
        paths.root.joinpath(*PurePosixPath(snapshot_relative_path).parts)
        if snapshot_relative_path is not None
        else None
    )
    if snapshot_destination is not None:
        _safe_profile_path(repo_root, profile_id, snapshot_destination)
        if snapshot_destination.exists() or _is_obvious_link(snapshot_destination):
            raise MaterialError("material text snapshot destination already exists")
    copied = False
    snapshot_copied = False
    try:
        _atomic_write(destination, content)
        copied = True
        if snapshot_destination is not None and snapshot_bytes is not None:
            _atomic_write(snapshot_destination, snapshot_bytes)
            snapshot_copied = True
        _atomic_write_manifest(_manifest_path(repo_root, profile_id), updated)
    except (OSError, MaterialError) as error:
        if copied:
            try:
                destination.unlink()
            except OSError:
                pass
        if snapshot_copied and snapshot_destination is not None:
            try:
                snapshot_destination.unlink()
            except OSError:
                pass
        if isinstance(error, MaterialError):
            raise
        raise MaterialError("material could not be stored atomically") from error
    return record


def list_materials(repo_root: Path, profile_id: str) -> tuple[MaterialRecord, ...]:
    """List only the explicitly named Profile's verified material records."""

    records = tuple(_record(item) for item in _load_manifest(repo_root, profile_id)["materials"])
    for record in records:
        _resolve_stored_path(repo_root, profile_id, record)
    return records


def get_material(repo_root: Path, profile_id: str, material_id: str) -> MaterialRecord:
    """Return one verified record without printing or returning its content."""

    identifier = _validate_material_id(material_id)
    records = (
        _record(item)
        for item in _load_manifest(repo_root, profile_id)["materials"]
    )
    for record in records:
        if record.id == identifier:
            _resolve_stored_path(repo_root, profile_id, record)
            return record
    raise MaterialError(f"unknown material ID in current Profile: {identifier}")


def resolve_material_path(
    repo_root: Path,
    profile_id: str,
    material: MaterialRecord | str,
) -> Path:
    """Resolve one canonical record inside the explicitly named Profile."""

    identifier = material.id if isinstance(material, MaterialRecord) else material
    canonical = get_material(repo_root, profile_id, identifier)
    if isinstance(material, MaterialRecord) and canonical != material:
        raise MaterialError("material record is not current for this Profile")
    return _resolve_stored_path(repo_root, profile_id, canonical)


def resolve_material_text_path(
    repo_root: Path,
    profile_id: str,
    material: MaterialRecord | str,
) -> Path:
    """Resolve the exact UTF-8 text authorized for one material.

    Text files are read directly. PDF/DOCX files use a read-only snapshot
    whose manifest entry is bound to the original file SHA-256.
    """

    identifier = material.id if isinstance(material, MaterialRecord) else material
    canonical = get_material(repo_root, profile_id, identifier)
    if isinstance(material, MaterialRecord) and canonical != material:
        raise MaterialError("material record is not current for this Profile")
    if not canonical.ai_access:
        raise MaterialError("material does not allow AI access")
    # Validate the original file first. A snapshot is useful only while the
    # source bytes still match the manifest SHA; otherwise an old extraction
    # could be sent after the user replaced the PDF/DOCX in place.
    stored = _resolve_stored_path(repo_root, profile_id, canonical)
    if canonical.opaque:
        return _resolve_text_snapshot_path(repo_root, profile_id, canonical)
    return stored
