"""Small provider-neutral values used by desktop controllers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator, Protocol, Sequence


@dataclass(frozen=True)
class ConnectionResult:
    ok: bool
    message: str
    latency_ms: int | None = None


@dataclass(frozen=True)
class ModelInfo:
    id: str
    display_name: str


@dataclass(frozen=True)
class ChatEvent:
    kind: str
    text: str = ""
    data: dict | None = None


@dataclass(frozen=True)
class ContextPart:
    id: str
    label: str
    content: str
    sha256: str
    selected: bool = True
    sensitive: bool = False


@dataclass(frozen=True)
class ContextPreview:
    mode: str
    profile_id: str
    parts: tuple[ContextPart, ...]

    @property
    def selected_text(self) -> str:
        return "\n\n".join(
            f"## {part.label}\n{part.content}" for part in self.parts if part.selected
        )

    @property
    def estimated_tokens(self) -> int:
        # A display hint only; providers remain authoritative for billing usage.
        return max(1, len(self.selected_text) // 4)


class ChatProvider(Protocol):
    async def test_connection(self) -> ConnectionResult: ...

    async def stream_chat(
        self, messages: Sequence[dict[str, str]]
    ) -> AsyncIterator[ChatEvent]: ...

    async def list_models(self) -> list[ModelInfo]: ...
