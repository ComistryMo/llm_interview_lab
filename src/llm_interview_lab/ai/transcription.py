"""One explicit OpenAI-compatible speech-to-text path for interview audio."""

from __future__ import annotations

import asyncio
from importlib import import_module
from pathlib import Path
from typing import Any, Callable

from .providers import ProviderConfig, ProviderError


MAX_AUDIO_BYTES = 25 * 1024 * 1024


class TranscriptionError(RuntimeError):
    """A sanitized, actionable transcription failure."""


class OpenAICompatibleTranscriber:
    """Submit one local audio file only after the caller records consent."""

    def __init__(
        self,
        config: ProviderConfig,
        *,
        api_key: str | None,
        model: str = "whisper-1",
        client_factory: Callable[..., Any] | None = None,
    ) -> None:
        if config.provider_id not in {"openai", "openai-compatible"}:
            raise TranscriptionError(
                "语音转录当前仅支持 OpenAI 或兼容的 /audio/transcriptions 服务"
            )
        self.config = config
        self._api_key = api_key
        self.model = model
        self._client_factory = client_factory

    def _client(self) -> Any:
        factory = self._client_factory
        if factory is None:
            try:
                factory = import_module("httpx").AsyncClient
            except ImportError as error:
                raise TranscriptionError(
                    "语音转录组件未安装；你仍可直接编辑并提交文字回答"
                ) from error
        base_url = self.config.base_url
        if self.config.provider_id == "openai":
            base_url = base_url or "https://api.openai.com/v1"
        if not base_url:
            raise TranscriptionError("OpenAI-compatible 转录需要 API 地址")
        headers = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return factory(
            base_url=base_url.rstrip("/") + "/",
            headers=headers,
            timeout=60.0,
        )

    async def transcribe(
        self,
        audio_path: Path,
        *,
        consent_remote: bool,
        language: str = "zh",
    ) -> str:
        if not consent_remote:
            raise TranscriptionError("远程转录需要本次明确授权")
        if not audio_path.is_file():
            raise TranscriptionError("本地录音文件不存在，请重新录音")
        try:
            content = audio_path.read_bytes()
        except OSError as error:
            raise TranscriptionError("本地录音文件无法读取") from error
        if not content or len(content) > MAX_AUDIO_BYTES:
            raise TranscriptionError("录音必须包含内容且不超过 25 MiB")
        client = self._client()
        try:
            response = await asyncio.wait_for(
                client.post(
                    "audio/transcriptions",
                    data={"model": self.model, "language": language},
                    files={"file": (audio_path.name, content, "audio/wav")},
                ),
                timeout=65,
            )
            response.raise_for_status()
            value = response.json()
            text = value.get("text") if isinstance(value, dict) else None
            if not isinstance(text, str) or not text.strip():
                raise TranscriptionError("转录服务没有返回可编辑文本")
            return text.strip()
        except TranscriptionError:
            raise
        except asyncio.TimeoutError as error:
            raise TranscriptionError("语音转录超时；录音仍保存在本机，可改用文字回答") from error
        except Exception as error:
            safe_name = type(error).__name__
            if isinstance(error, ProviderError):
                safe_name = str(error)
            raise TranscriptionError(
                f"语音转录失败（{safe_name}）；录音仍保存在本机，可重试或改用文字回答"
            ) from error
        finally:
            close = getattr(client, "aclose", None) or getattr(client, "close", None)
            if close is not None:
                result = close()
                if hasattr(result, "__await__"):
                    await result
