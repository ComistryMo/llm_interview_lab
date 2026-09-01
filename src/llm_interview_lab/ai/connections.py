"""Ignored Profile connection metadata with secrets referenced from system keyring."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from .credentials import KeyringCredentialStore
from .providers import ProviderConfig
from ..workspace import (
    ensure_profile_is_ignored,
    ensure_profile_path_is_safe,
    load_profile,
    profile_paths,
)


CONNECTION_ID_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
SUPPORTED_PROVIDERS = frozenset(
    {"openai", "openai-compatible", "anthropic", "gemini", "ollama"}
)
SUPPORTED_REASONING_EFFORTS = frozenset({"low", "medium", "high", "xhigh"})


class ConnectionConfigError(RuntimeError):
    """Raised when local connection metadata is invalid."""


def _path(repo_root: Path, profile_id: str) -> Path:
    return ensure_profile_path_is_safe(
        repo_root,
        profile_id,
        profile_paths(repo_root, profile_id).root / "connections.json",
    )


def _read(repo_root: Path, profile_id: str) -> dict[str, Any]:
    paths = profile_paths(repo_root, profile_id)
    load_profile(paths, repo_root)
    path = _path(repo_root, profile_id)
    if not path.exists():
        return {"schema_version": 2, "connections": []}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ConnectionConfigError("connection metadata cannot be read") from error
    if (
        not isinstance(value, dict)
        or value.get("schema_version") not in {1, 2}
        or not isinstance(value.get("connections"), list)
    ):
        raise ConnectionConfigError("connection metadata has an unsupported format")
    ids: set[str] = set()
    for item in value["connections"]:
        required = {
            "connection_id", "provider_id", "model", "display_name", "base_url", "key_reference"
        }
        if (
            not isinstance(item, dict)
            or not required.issubset(item)
            or not set(item).issubset(required | {"reasoning_effort"})
        ):
            raise ConnectionConfigError("connection metadata contains an invalid record")
        effort = item.get("reasoning_effort")
        if effort is not None and effort not in SUPPORTED_REASONING_EFFORTS:
            raise ConnectionConfigError("connection metadata contains an invalid reasoning effort")
        if item["connection_id"] in ids:
            raise ConnectionConfigError("connection IDs must be unique")
        ids.add(item["connection_id"])
        item.setdefault("reasoning_effort", None)
    value["schema_version"] = 2
    return value


def _write(repo_root: Path, profile_id: str, value: dict[str, Any]) -> None:
    ensure_profile_is_ignored(repo_root, profile_id)
    path = _path(repo_root, profile_id)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    encoded = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    try:
        with temporary.open("xb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError as error:
        temporary.unlink(missing_ok=True)
        raise ConnectionConfigError("connection metadata could not be written") from error


def _validate_url(provider_id: str, value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        raise ConnectionConfigError("endpoint must be an HTTP(S) URL without embedded credentials")
    if provider_id not in {"openai-compatible", "ollama"}:
        raise ConnectionConfigError("custom endpoints are available only for compatible or Ollama providers")
    return value.strip().rstrip("/")


def list_connections(repo_root: Path, profile_id: str) -> tuple[ProviderConfig, ...]:
    value = _read(repo_root, profile_id)
    return tuple(
        ProviderConfig(
            item["connection_id"],
            item["provider_id"],
            item["model"],
            item["display_name"],
            item["base_url"],
            item["key_reference"],
            item.get("reasoning_effort"),
        )
        for item in value["connections"]
    )


def save_connection(
    repo_root: Path,
    profile_id: str,
    *,
    connection_id: str,
    provider_id: str,
    model: str,
    display_name: str,
    base_url: str | None = None,
    api_key: str | None = None,
    reasoning_effort: str | None = None,
    credential_store: KeyringCredentialStore | None = None,
) -> ProviderConfig:
    if CONNECTION_ID_RE.fullmatch(connection_id) is None:
        raise ConnectionConfigError("connection ID must be lowercase letters, digits, or hyphens")
    if provider_id not in SUPPORTED_PROVIDERS:
        raise ConnectionConfigError("provider is not supported by the desktop alpha")
    if not model.strip() or len(model) > 200 or not display_name.strip() or len(display_name) > 100:
        raise ConnectionConfigError("model and display name must be non-empty and bounded")
    endpoint = _validate_url(provider_id, base_url)
    effort = reasoning_effort.strip().lower() if reasoning_effort else None
    if effort not in SUPPORTED_REASONING_EFFORTS | {None}:
        raise ConnectionConfigError(
            "reasoning effort must be low, medium, high, xhigh, or empty"
        )
    value = _read(repo_root, profile_id)
    existing = next(
        (item for item in value["connections"] if item["connection_id"] == connection_id),
        None,
    )
    reference = existing["key_reference"] if existing else None
    if api_key is not None:
        store = credential_store or KeyringCredentialStore()
        reference = store.save(profile_id, connection_id, api_key)
    if provider_id != "ollama" and reference is None:
        raise ConnectionConfigError("remote providers require an API key in the system keyring")
    record = {
        "connection_id": connection_id,
        "provider_id": provider_id,
        "model": model.strip(),
        "display_name": display_name.strip(),
        "base_url": endpoint,
        "key_reference": reference,
        "reasoning_effort": effort,
    }
    value["connections"] = [
        item for item in value["connections"] if item["connection_id"] != connection_id
    ] + [record]
    _write(repo_root, profile_id, value)
    return ProviderConfig(
        connection_id,
        provider_id,
        record["model"],
        record["display_name"],
        endpoint,
        reference,
        effort,
    )


def delete_connection(
    repo_root: Path,
    profile_id: str,
    connection_id: str,
    *,
    credential_store: KeyringCredentialStore | None = None,
) -> bool:
    value = _read(repo_root, profile_id)
    existing = next(
        (item for item in value["connections"] if item["connection_id"] == connection_id),
        None,
    )
    if existing is None:
        return False
    value["connections"] = [
        item for item in value["connections"] if item["connection_id"] != connection_id
    ]
    _write(repo_root, profile_id, value)
    if existing["key_reference"]:
        (credential_store or KeyringCredentialStore()).delete(existing["key_reference"])
    return True
