"""Unified optional chat-provider adapter backed by Mozilla any-llm."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from importlib import import_module
import inspect
import json
import re
import time
from typing import Any, AsyncIterator, Awaitable, Callable, Sequence

from .base import ChatEvent, ConnectionResult, ModelInfo
from .connection_diagnostics import connection_diagnostic


class ProviderError(RuntimeError):
    """A sanitized provider error suitable for local UI display."""


@dataclass(frozen=True)
class ProviderConfig:
    connection_id: str
    provider_id: str
    model: str
    display_name: str
    base_url: str | None = None
    key_reference: str | None = None
    reasoning_effort: str | None = None


def _safe_error(error: Exception) -> ProviderError:
    if isinstance(error, ProviderError):
        return error
    name = type(error).__name__.lower()
    text = str(error).lower()
    if "auth" in name or "401" in text or "unauthorized" in text:
        return ProviderError("authentication failed; check the stored API key")
    if "402" in text:
        return ProviderError("服务账户余额不足（402）。请到服务控制台检查余额后重试；回答已保留。")
    if "400" in text or "422" in text:
        return ProviderError("模型或推理参数不被服务接受。请核对模型 ID 与该服务支持的推理选项。")
    if "rate" in name or "429" in text:
        return ProviderError("provider rate limit reached; retry later")
    if "timeout" in name or "timed out" in text:
        return ProviderError("provider request timed out")
    if any(code in text for code in ("500", "502", "503")):
        return ProviderError("provider service returned a temporary server error")
    return ProviderError(f"provider request failed ({type(error).__name__})")


def _delta_text(chunk: Any) -> str:
    try:
        value = chunk.choices[0].delta.content
    except (AttributeError, IndexError, TypeError):
        if isinstance(chunk, dict):
            try:
                value = chunk["choices"][0]["delta"].get("content", "")
            except (KeyError, IndexError, TypeError):
                value = ""
        else:
            value = ""
    return value or ""


def _response_id(value: Any) -> str | None:
    """Keep recognizable transport IDs, never arbitrary header/body strings."""
    if isinstance(value, str) and re.fullmatch(
        r"(?:[a-fA-F0-9]{16,64}|[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}"
        r"|(?:chatcmpl-|req_)[A-Za-z0-9_-]{8,96})", value,
    ) and "sk-" not in value.lower():
        return value
    return None


class AnyLLMChatProvider:
    """One adapter for OpenAI, Anthropic, Gemini, Ollama and compatible APIs."""

    def __init__(
        self,
        config: ProviderConfig,
        *,
        api_key: str | None,
        completion: Callable[..., Awaitable[Any]] | None = None,
    ) -> None:
        self.config = config
        self._api_key = api_key
        self._completion = completion

    def _call(self) -> Callable[..., Awaitable[Any]]:
        if self._completion is not None:
            return self._completion
        try:
            # Keep provider SDKs optional for the core CLI and the compact
            # Windows executable. Source installs with ``[ai]`` use any-llm
            # for native Anthropic and Gemini protocols.
            acompletion = import_module("any_llm").acompletion
        except ImportError as error:
            raise ProviderError(
                "AI provider support is not installed; install llm_interview_lab[ai]"
            ) from error
        return acompletion

    def _kwargs(self, *, stream: bool) -> dict[str, Any]:
        provider = (
            "openai"
            if self.config.provider_id == "openai-compatible"
            else self.config.provider_id
        )
        values: dict[str, Any] = {
            "provider": provider,
            "model": self.config.model,
            "stream": stream,
        }
        if self._api_key:
            values["api_key"] = self._api_key
        if self.config.base_url:
            values["api_base"] = self.config.base_url
        if self.config.reasoning_effort:
            values["reasoning_effort"] = self.config.reasoning_effort
        return values

    async def test_connection(self) -> ConnectionResult:
        started = time.perf_counter()
        try:
            await asyncio.wait_for(
                self._call()(
                    messages=[{"role": "user", "content": "Reply with OK."}],
                    max_tokens=2,
                    **self._kwargs(stream=False),
                ),
                timeout=20,
            )
        except Exception as error:
            safe = _safe_error(error)
            return ConnectionResult(False, str(safe), round((time.perf_counter() - started) * 1000), connection_diagnostic(error))
        return ConnectionResult(True, "Connection succeeded", round((time.perf_counter() - started) * 1000))

    async def stream_chat(
        self, messages: Sequence[dict[str, str]]
    ) -> AsyncIterator[ChatEvent]:
        try:
            stream = await self._call()(messages=list(messages), **self._kwargs(stream=True))
            async for chunk in stream:
                text = _delta_text(chunk)
                if text:
                    yield ChatEvent("text_delta", text)
            yield ChatEvent("completed")
        except asyncio.CancelledError:
            yield ChatEvent("cancelled")
            raise
        except Exception as error:
            raise _safe_error(error) from error

    async def list_models(self) -> list[ModelInfo]:
        # Model listing is not uniformly available across providers.  The
        # configured model remains usable and explicit instead of guessing.
        return [ModelInfo(self.config.model, self.config.model)]


class OpenAICompatibleChatProvider:
    """One HTTP/SSE adapter shared by OpenAI, compatible endpoints and Ollama.

    It delegates transport, cancellation and timeouts to httpx instead of
    maintaining vendor clients. Anthropic and Gemini continue to use
    :class:`AnyLLMChatProvider` in source installs.
    """

    def __init__(
        self,
        config: ProviderConfig,
        *,
        api_key: str | None,
        client_factory: Callable[..., Any] | None = None,
    ) -> None:
        if config.provider_id not in {"openai", "openai-compatible", "ollama", "deepseek"}:
            raise ProviderError("this adapter requires an OpenAI-compatible provider")
        self.config = config
        self._api_key = api_key
        self._client_factory = client_factory
        self.last_diagnostic: dict[str, Any] = {}

    def _client(self) -> Any:
        factory = self._client_factory
        if factory is None:
            try:
                factory = import_module("httpx").AsyncClient
            except ImportError as error:
                raise ProviderError(
                    "OpenAI-compatible support is not installed; install llm_interview_lab[ai]"
                ) from error
        base_url = self.config.base_url
        if self.config.provider_id == "ollama":
            base_url = base_url or "http://127.0.0.1:11434/v1"
        elif self.config.provider_id == "openai":
            base_url = base_url or "https://api.openai.com/v1"
        elif self.config.provider_id == "deepseek":
            base_url = "https://api.deepseek.com"
        if not base_url:
            raise ProviderError("an OpenAI-compatible endpoint is required")
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return factory(base_url=base_url.rstrip("/") + "/", headers=headers,
                       timeout=90.0 if self.config.provider_id == "deepseek" else 20.0)

    def _reasoning_options(self) -> dict[str, Any]:
        effort = self.config.reasoning_effort
        if self.config.provider_id == "deepseek":
            if effort == "none":
                return {"thinking": {"type": "disabled"}}
            return {"thinking": {"type": "enabled"},
                    **({"reasoning_effort": effort} if effort else {})}
        return {"reasoning_effort": effort} if effort else {}

    @staticmethod
    async def _close(client: Any) -> None:
        close = getattr(client, "aclose", None) or getattr(client, "close", None)
        if close is not None:
            result = close()
            if inspect.isawaitable(result):
                await result

    async def test_connection(self) -> ConnectionResult:
        started = time.perf_counter()
        client = None
        stage = "init_client"
        try:
            client = self._client()
            stage = "request"
            payload: dict[str, Any] = {
                "model": self.config.model,
                "messages": [{"role": "user", "content": "Reply with OK."}],
                "max_tokens": 256 if self.config.provider_id == "deepseek" else 2,
            }
            payload.update(self._reasoning_options())
            if self.config.provider_id == "deepseek":
                # A short model/key reachability check, not a reasoning task.
                payload["thinking"] = {"type": "disabled"}
                payload.pop("reasoning_effort", None)
            await asyncio.wait_for(
                self._post_checked(
                    client,
                    payload,
                ),
                timeout=20,
            )
        except Exception as error:
            safe = _safe_error(error)
            return ConnectionResult(
                False,
                str(safe),
                round((time.perf_counter() - started) * 1000),
                connection_diagnostic(error, stage),
            )
        finally:
            if client is not None:
                await self._close(client)
        return ConnectionResult(
            True,
            "Connection succeeded",
            round((time.perf_counter() - started) * 1000),
        )

    async def stream_chat(
        self, messages: Sequence[dict[str, str]], *, json_mode: bool = False
    ) -> AsyncIterator[ChatEvent]:
        started = time.perf_counter()
        client = None
        # Only counts, known enums and transport IDs leave this adapter. In
        # particular, do not attach messages, exception bodies or reasoning.
        diagnostic: dict[str, Any] = {
            "provider": self.config.provider_id,
            "model": self.config.model if self.config.provider_id == "deepseek"
            and self.config.model in {"deepseek-v4-flash", "deepseek-v4-pro", "deepseek-chat", "deepseek-reasoner"} else "custom",
            "reasoning_effort": self.config.reasoning_effort
            if self.config.reasoning_effort in {"none", "low", "medium", "high", "xhigh", "max"} else "default",
            "json_mode": json_mode, "max_tokens": "provider_default",
            "http_status": None, "request_id": None, "response_id": None,
            "finish_reason": None, "done_marker": False,
            "content_chars": 0, "reasoning_chars": 0,
            "first_content_ms": None, "usage": {}, "code": "AI_TRANSPORT_FAILED",
        }
        try:
            client = self._client()
            payload: dict[str, Any] = {
                "model": self.config.model,
                "messages": list(messages),
                "stream": True,
            }
            payload.update(self._reasoning_options())
            # Keep explicit output requirements even in thinking mode. V4
            # supports JSON Output; prose alone cannot drive a validated turn.
            # An empty/truncated service response still remains a retryable error.
            if json_mode:
                payload["response_format"] = {"type": "json_object"}
            received_text = False
            received_reasoning = False
            stream_finished = False
            async with client.stream(
                "POST",
                "chat/completions",
                json=payload,
            ) as response:
                diagnostic["http_status"] = response.status_code
                diagnostic["request_id"] = _response_id(response.headers.get("x-request-id"))
                if response.is_error:
                    diagnostic["code"] = "AI_HTTP_ERROR"
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        diagnostic["done_marker"] = True
                        stream_finished = True
                        break
                    if not data:
                        continue
                    try:
                        chunk = json.loads(data)
                    except (ValueError, TypeError) as error:
                        diagnostic["code"] = "AI_RESPONSE_FORMAT"
                        raise ProviderError("provider returned malformed streaming JSON") from error
                    if not isinstance(chunk, dict):
                        diagnostic["code"] = "AI_RESPONSE_FORMAT"
                        raise ProviderError("AI 返回的流格式不正确。请重试；回答已保留。")
                    if diagnostic["response_id"] is None:
                        diagnostic["response_id"] = _response_id(chunk.get("id"))
                    usage = chunk.get("usage")
                    if isinstance(usage, dict):
                        for key in ("prompt_tokens", "completion_tokens", "total_tokens",
                                    "prompt_cache_hit_tokens", "prompt_cache_miss_tokens"):
                            if type(usage.get(key)) is int and usage[key] >= 0:
                                diagnostic["usage"][key] = usage[key]
                        details = usage.get("completion_tokens_details")
                        if isinstance(details, dict) and type(details.get("reasoning_tokens")) is int and details["reasoning_tokens"] >= 0:
                            diagnostic["usage"]["reasoning_tokens"] = details["reasoning_tokens"]
                    if "error" in chunk:
                        # The raw service message may echo the request or Key.
                        # Surface only known codes, never its message/body.
                        failure = chunk["error"]
                        code = str(failure.get("code", "")) if isinstance(failure, dict) else ""
                        hints = {"400": "模型或推理参数不被接受", "401": "凭证无效，请更新 API Key",
                                 "402": "账户余额不足", "429": "请求限流，请稍后重试",
                                 "500": "服务暂时异常", "503": "服务繁忙，请稍后重试"}
                        detail = f"（{code}）：{hints[code]}" if code in hints else ""
                        diagnostic["code"] = "AI_PROVIDER_ERROR"
                        diagnostic["service_error_code"] = code if code in hints else "other"
                        raise ProviderError(f"AI 响应流返回服务端错误{detail}。请重试；回答已保留。")
                    text = _delta_text(chunk)
                    if not isinstance(text, str):
                        diagnostic["code"] = "AI_RESPONSE_FORMAT"
                        raise ProviderError("AI 正文不是文本格式。请重试；回答已保留。")
                    if text:
                        received_text = received_text or bool(text.strip())
                        diagnostic["content_chars"] += len(text)
                        if text.strip() and diagnostic["first_content_ms"] is None:
                            diagnostic["first_content_ms"] = round((time.perf_counter() - started) * 1000)
                        yield ChatEvent("text_delta", text)
                    # DeepSeek sends reasoning_content separately. Only final
                    # content is an answer; never parse its thinking as a score.
                    choices = chunk.get("choices", [])
                    finish = choices[0].get("finish_reason") if choices else None
                    reasoning = choices[0].get("delta", {}).get("reasoning_content") if choices else None
                    if isinstance(reasoning, str) and reasoning:
                        received_reasoning = True
                        diagnostic["reasoning_chars"] += len(reasoning)
                    if finish is not None:
                        diagnostic["finish_reason"] = finish if finish in {
                            "stop", "length", "content_filter", "insufficient_system_resource", "tool_calls",
                        } else "other"
                    if finish == "stop":
                        stream_finished = True
                    elif finish == "length":
                        diagnostic["code"] = "AI_RESPONSE_TRUNCATED"
                        raise ProviderError("AI 回复未完整生成：输出预算已用完（包含思考消耗）。回答已保留，请重试或复制脱敏诊断；原模型与推理强度未改变。")
                    elif finish in {"content_filter", "insufficient_system_resource"}:
                        diagnostic["code"] = "AI_RESPONSE_FILTERED" if finish == "content_filter" else "AI_RESPONSE_RESOURCE"
                        reason = "服务内容过滤" if finish == "content_filter" else "服务算力暂时不足"
                        raise ProviderError(f"AI 回复未完整生成（{reason}）。请重试；回答已保留。")
                    elif finish is not None:
                        diagnostic["code"] = "AI_RESPONSE_UNEXPECTED_FINISH"
                        raise ProviderError("AI 以非预期原因结束，未确认回答完整。请重试或复制脱敏诊断；回答已保留。")
            if self.config.provider_id == "deepseek" and not stream_finished:
                diagnostic["code"] = "AI_RESPONSE_INTERRUPTED"
                raise ProviderError("AI 响应流在完成前中断，未收到结束标记。请重试；不会保存半截题目或评分，回答已保留。")
            if not received_text:
                diagnostic["code"] = "AI_RESPONSE_REASONING_ONLY" if received_reasoning else "AI_RESPONSE_EMPTY"
                reason = "服务仅返回思考，未返回回答正文" if received_reasoning else "服务返回空白，未返回回答正文"
                raise ProviderError(f"{reason}。请重试；不会把思考内容当作题目，原模型与推理强度未改变。")
            diagnostic["code"] = ""
            yield ChatEvent("completed")
        except asyncio.CancelledError:
            diagnostic["code"] = "AI_REQUEST_CANCELLED"
            yield ChatEvent("cancelled")
            raise
        except Exception as error:
            if "timeout" in type(error).__name__.lower():
                diagnostic["code"] = "AI_REQUEST_TIMEOUT"
                diagnostic["timeout_kind"] = {
                    "ReadTimeout": "read", "ConnectTimeout": "connect",
                    "WriteTimeout": "write", "PoolTimeout": "pool",
                }.get(type(error).__name__, "transport")
            raise _safe_error(error) from error
        finally:
            diagnostic["elapsed_ms"] = round((time.perf_counter() - started) * 1000)
            self.last_diagnostic = diagnostic
            if client is not None:
                await self._close(client)

    async def list_models(self) -> list[ModelInfo]:
        client = self._client()
        try:
            response = await asyncio.wait_for(client.get("models"), timeout=20)
            response.raise_for_status()
            value = response.json()
            if not isinstance(value, dict) or not isinstance(value.get("data"), list):
                raise ProviderError("provider returned an invalid model list")
            ids = [item.get("id") for item in value["data"] if isinstance(item, dict)]
            return [ModelInfo(item, item) for item in ids if isinstance(item, str) and item]
        except Exception as error:
            if isinstance(error, ProviderError):
                raise
            raise _safe_error(error) from error
        finally:
            await self._close(client)

    @staticmethod
    async def _post_checked(client: Any, payload: dict[str, Any]) -> Any:
        response = await client.post("chat/completions", json=payload)
        response.raise_for_status()
        return response


def create_chat_provider(
    config: ProviderConfig, *, api_key: str | None
) -> AnyLLMChatProvider | OpenAICompatibleChatProvider:
    """Select the smallest protocol adapter that exactly fits a connection."""

    if config.provider_id in {"openai", "openai-compatible", "ollama", "deepseek"}:
        return OpenAICompatibleChatProvider(config, api_key=api_key)
    return AnyLLMChatProvider(config, api_key=api_key)
