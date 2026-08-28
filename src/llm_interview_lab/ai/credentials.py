"""System-keyring secret storage; plaintext Profile files store references only."""

from __future__ import annotations

from typing import Protocol


SERVICE_NAME = "llm_interview_lab"


class CredentialError(RuntimeError):
    """Raised when system credential storage is unavailable or incomplete."""


class CredentialBackend(Protocol):
    def set_password(self, service: str, username: str, password: str) -> None: ...
    def get_password(self, service: str, username: str) -> str | None: ...
    def delete_password(self, service: str, username: str) -> None: ...


class KeyringCredentialStore:
    def __init__(self, backend: CredentialBackend | None = None) -> None:
        if backend is None:
            try:
                import keyring
            except ImportError as error:
                raise CredentialError(
                    "system keyring support is not installed; install llm_interview_lab[ai]"
                ) from error
            backend = keyring
        self._backend = backend

    @staticmethod
    def reference(profile_id: str, connection_id: str) -> str:
        return f"profile:{profile_id}:connection:{connection_id}"

    def save(self, profile_id: str, connection_id: str, secret: str) -> str:
        if not isinstance(secret, str) or not secret.strip():
            raise CredentialError("API key cannot be empty")
        reference = self.reference(profile_id, connection_id)
        try:
            self._backend.set_password(SERVICE_NAME, reference, secret.strip())
        except Exception as error:
            raise CredentialError("system keyring rejected the API key") from error
        return reference

    def load(self, reference: str) -> str:
        try:
            value = self._backend.get_password(SERVICE_NAME, reference)
        except Exception as error:
            raise CredentialError("system keyring could not read the API key") from error
        if not value:
            raise CredentialError("API key is missing from the system keyring")
        return value

    def delete(self, reference: str) -> None:
        try:
            self._backend.delete_password(SERVICE_NAME, reference)
        except Exception as error:
            # Deleting an already-missing secret is idempotent for the workbench.
            if "not found" not in str(error).lower():
                raise CredentialError("system keyring could not delete the API key") from error
