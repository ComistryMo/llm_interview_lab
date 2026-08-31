from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from llm_interview_lab.ai.providers import ProviderConfig
from llm_interview_lab.ai.transcription import (
    OpenAICompatibleTranscriber,
    TranscriptionError,
)


pytestmark = pytest.mark.infrastructure


class _Response:
    def __init__(self, payload: object, error: Exception | None = None) -> None:
        self.payload = payload
        self.error = error

    def raise_for_status(self) -> None:
        if self.error is not None:
            raise self.error

    def json(self) -> object:
        return self.payload


class _Client:
    def __init__(self, response: _Response | None = None, error: Exception | None = None, **kwargs):
        self.response = response
        self.error = error
        self.kwargs = kwargs
        self.calls: list[tuple[str, dict, dict]] = []
        self.closed = False

    async def post(self, endpoint: str, *, data: dict, files: dict) -> _Response:
        self.calls.append((endpoint, data, files))
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response

    async def aclose(self) -> None:
        self.closed = True


def _config(provider_id: str = "openai-compatible") -> ProviderConfig:
    return ProviderConfig(
        "transcription-test",
        provider_id,
        "gpt-test",
        "Test provider",
        "https://example.test/v1",
        None,
    )


def test_transcriber_sends_only_selected_wav_after_consent(tmp_path: Path) -> None:
    audio = tmp_path / "answer.wav"
    audio.write_bytes(b"RIFF synthetic wav")
    client = _Client(_Response({"text": "整理后的回答"}))

    result = asyncio.run(
        OpenAICompatibleTranscriber(
            _config(), api_key="secret-not-for-logs", client_factory=lambda **kw: client
        ).transcribe(audio, consent_remote=True)
    )

    assert result == "整理后的回答"
    assert client.calls[0][0] == "audio/transcriptions"
    assert client.calls[0][1] == {"model": "whisper-1", "language": "zh"}
    assert client.calls[0][2]["file"][0] == "answer.wav"
    assert client.closed

def test_transcriber_requires_explicit_consent_before_opening_transport(tmp_path: Path) -> None:
    audio = tmp_path / "answer.wav"
    audio.write_bytes(b"wav")
    called = False

    def factory(**_kwargs):
        nonlocal called
        called = True
        return _Client(_Response({"text": "should not happen"}))

    with pytest.raises(TranscriptionError, match="授权"):
        asyncio.run(
            OpenAICompatibleTranscriber(
                _config(), api_key=None, client_factory=factory
            ).transcribe(audio, consent_remote=False)
        )
    assert not called


def test_transcriber_rejects_unsupported_provider_and_missing_audio(tmp_path: Path) -> None:
    with pytest.raises(TranscriptionError, match="OpenAI"):
        OpenAICompatibleTranscriber(_config("anthropic"), api_key=None)

    with pytest.raises(TranscriptionError, match="不存在"):
        asyncio.run(
            OpenAICompatibleTranscriber(
                _config(), api_key=None, client_factory=lambda **_kw: _Client()
            ).transcribe(tmp_path / "missing.wav", consent_remote=True)
        )


def test_transcriber_sanitizes_transport_error_and_closes_client(tmp_path: Path) -> None:
    audio = tmp_path / "answer.wav"
    audio.write_bytes(b"wav")
    client = _Client(error=RuntimeError("Bearer secret-value should not escape"))

    with pytest.raises(TranscriptionError) as caught:
        asyncio.run(
            OpenAICompatibleTranscriber(
                _config(), api_key="secret-value", client_factory=lambda **_kw: client
            ).transcribe(audio, consent_remote=True)
        )

    assert "secret-value" not in str(caught.value)
    assert "RuntimeError" in str(caught.value)
    assert client.closed


def test_transcriber_timeout_is_actionable(tmp_path: Path) -> None:
    audio = tmp_path / "answer.wav"
    audio.write_bytes(b"wav")
    client = _Client(error=asyncio.TimeoutError())

    with pytest.raises(TranscriptionError, match="超时"):
        asyncio.run(
            OpenAICompatibleTranscriber(
                _config(), api_key=None, client_factory=lambda **_kw: client
            ).transcribe(audio, consent_remote=True)
        )
    assert client.closed
