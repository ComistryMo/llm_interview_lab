from __future__ import annotations

import asyncio
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from llm_interview_lab.ai.codex_backend import CodexAppServerBackend, CodexBackendError
from llm_interview_lab.ai.connections import (
    delete_connection,
    list_connections,
    save_connection,
)
from llm_interview_lab.ai.credentials import KeyringCredentialStore, SERVICE_NAME
from llm_interview_lab.ai.providers import (
    AnyLLMChatProvider,
    OpenAICompatibleChatProvider,
    ProviderConfig,
    ProviderError,
    create_chat_provider,
)
from llm_interview_lab.desktop.i18n import friendly_error
from llm_interview_lab.workspace import init_profile


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='ai-fixture'\nversion='0'\n", encoding="utf-8")
    (root / ".gitignore").write_text(
        "/workspace/profiles/*\n!/workspace/profiles/.gitkeep\n", encoding="utf-8"
    )
    (root / "curriculum").mkdir()
    shutil.copytree(REPO_ROOT / "workspace/schema", root / "workspace/schema")
    shutil.copytree(REPO_ROOT / "workspace/templates", root / "workspace/templates")
    (root / "workspace/profiles").mkdir(parents=True)
    (root / "workspace/profiles/.gitkeep").write_text("", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    init_profile(root, "learner-one")
    return root


class MemoryKeyring:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def set_password(self, service: str, username: str, password: str) -> None:
        self.values[(service, username)] = password

    def get_password(self, service: str, username: str) -> str | None:
        return self.values.get((service, username))

    def delete_password(self, service: str, username: str) -> None:
        self.values.pop((service, username), None)


def test_connection_metadata_never_contains_api_key(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    backend = MemoryKeyring()
    store = KeyringCredentialStore(backend)
    config = save_connection(
        root,
        "learner-one",
        connection_id="openai-main",
        provider_id="openai",
        model="gpt-test",
        display_name="OpenAI",
        api_key="super-secret",
        credential_store=store,
    )
    raw = (root / "workspace/profiles/learner-one/connections.json").read_text(encoding="utf-8")
    assert "super-secret" not in raw
    assert config.key_reference == "profile:learner-one:connection:openai-main"
    assert backend.values[(SERVICE_NAME, config.key_reference)] == "super-secret"
    assert list_connections(root, "learner-one") == (config,)
    assert delete_connection(
        root, "learner-one", "openai-main", credential_store=store
    )
    assert not backend.values


class FakeDelta:
    def __init__(self, text: str) -> None:
        self.choices = [type("Choice", (), {"delta": type("Delta", (), {"content": text})()})()]


class FakeStream:
    def __init__(self, values: list[str]) -> None:
        self.values = values

    def __aiter__(self):
        self.iterator = iter(self.values)
        return self

    async def __anext__(self):
        try:
            return FakeDelta(next(self.iterator))
        except StopIteration:
            raise StopAsyncIteration


def test_unified_provider_streams_and_sanitizes_failures() -> None:
    calls: list[dict] = []

    async def completion(**kwargs):
        calls.append(kwargs)
        if kwargs["stream"]:
            return FakeStream(["hello", " world"])
        return object()

    async def scenario() -> None:
        provider = AnyLLMChatProvider(
            ProviderConfig("local", "ollama", "model", "Local", "http://127.0.0.1:11434", None),
            api_key=None,
            completion=completion,
        )
        assert (await provider.test_connection()).ok
        events = [event async for event in provider.stream_chat([{"role": "user", "content": "hi"}])]
        assert "".join(event.text for event in events) == "hello world"
        assert events[-1].kind == "completed"
        assert all("api_key" not in call for call in calls)

    asyncio.run(scenario())


def test_openai_compatible_uses_openai_adapter_with_custom_endpoint() -> None:
    calls: list[dict] = []

    async def completion(**kwargs):
        calls.append(kwargs)
        return object()

    provider = AnyLLMChatProvider(
        ProviderConfig(
            "compatible",
            "openai-compatible",
            "private-model",
            "Compatible endpoint",
            "https://models.example.test/v1",
            "ref",
        ),
        api_key="not-logged",
        completion=completion,
    )
    assert asyncio.run(provider.test_connection()).ok
    assert calls[0]["provider"] == "openai"
    assert calls[0]["api_base"] == "https://models.example.test/v1"
    assert calls[0]["api_key"] == "not-logged"


class FakeHTTPResponse:
    def __init__(self, *, lines: list[str] | None = None, value: dict | None = None) -> None:
        self.lines = lines or []
        self.value = value or {}

    def raise_for_status(self) -> None:
        return None

    async def aiter_lines(self):
        for line in self.lines:
            yield line

    def json(self) -> dict:
        return self.value


class FakeHTTPStream:
    def __init__(self, response: FakeHTTPResponse) -> None:
        self.response = response

    async def __aenter__(self) -> FakeHTTPResponse:
        return self.response

    async def __aexit__(self, *args) -> None:
        del args


class FakeHTTPClient:
    def __init__(self, calls: list[dict], close_calls: list[bool]) -> None:
        self.calls = calls
        self.close_calls = close_calls

    async def post(self, path: str, **kwargs):
        self.calls.append({"method": "POST", "path": path, **kwargs})
        return FakeHTTPResponse()

    def stream(self, method: str, path: str, **kwargs) -> FakeHTTPStream:
        self.calls.append({"method": method, "path": path, **kwargs})
        return FakeHTTPStream(
            FakeHTTPResponse(
                lines=[
                    'data: {"choices":[{"delta":{"content":"one"}}]}',
                    'data: {"choices":[{"delta":{"content":" two"}}]}',
                    "data: [DONE]",
                ]
            )
        )

    async def get(self, path: str) -> FakeHTTPResponse:
        self.calls.append({"method": "GET", "path": path})
        return FakeHTTPResponse(value={"data": [{"id": "m-1"}]})

    async def close(self) -> None:
        self.close_calls.append(True)


def test_compact_openai_compatible_adapter_supports_ollama_and_streaming() -> None:
    constructor_calls: list[dict] = []
    completion_calls: list[dict] = []
    close_calls: list[bool] = []

    def factory(**kwargs):
        constructor_calls.append(kwargs)
        return FakeHTTPClient(completion_calls, close_calls)

    provider = OpenAICompatibleChatProvider(
        ProviderConfig("local", "ollama", "qwen", "Local Ollama"),
        api_key=None,
        client_factory=factory,
    )

    async def scenario() -> None:
        assert (await provider.test_connection()).ok
        events = [event async for event in provider.stream_chat([{"role": "user", "content": "hi"}])]
        assert "".join(event.text for event in events) == "one two"
        assert [item.id for item in await provider.list_models()] == ["m-1"]

    asyncio.run(scenario())
    assert all(call["base_url"] == "http://127.0.0.1:11434/v1/" for call in constructor_calls)
    assert all("Authorization" not in call["headers"] for call in constructor_calls)
    assert len(close_calls) == 3
    assert completion_calls[1]["json"]["stream"] is True


def test_provider_factory_uses_native_adapter_only_for_native_protocols() -> None:
    compatible = create_chat_provider(
        ProviderConfig("openai", "openai", "model", "OpenAI"), api_key="key"
    )
    native = create_chat_provider(
        ProviderConfig("anthropic", "anthropic", "model", "Anthropic"), api_key="key"
    )
    assert isinstance(compatible, OpenAICompatibleChatProvider)
    assert isinstance(native, AnyLLMChatProvider)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("401 unauthorized secret-value", "authentication failed"),
        ("429 rate limit secret-value", "rate limit"),
        ("500 upstream secret-value", "temporary server error"),
        ("invalid model secret-value", "provider request failed"),
    ],
)
def test_provider_failures_are_bounded_and_do_not_echo_secrets(
    message: str, expected: str
) -> None:
    async def completion(**kwargs):
        del kwargs
        raise RuntimeError(message)

    provider = AnyLLMChatProvider(
        ProviderConfig("remote", "openai", "model", "Remote"),
        api_key="secret-value",
        completion=completion,
    )
    result = asyncio.run(provider.test_connection())
    assert not result.ok
    assert expected in result.message
    assert "secret-value" not in result.message


def test_provider_timeout_and_stream_cancellation_are_explicit() -> None:
    async def timeout_completion(**kwargs):
        del kwargs
        raise asyncio.TimeoutError

    timeout_provider = AnyLLMChatProvider(
        ProviderConfig("remote", "openai", "model", "Remote"),
        api_key="secret",
        completion=timeout_completion,
    )
    assert "timed out" in asyncio.run(timeout_provider.test_connection()).message

    started = asyncio.Event()

    class SlowStream:
        def __aiter__(self):
            return self

        async def __anext__(self):
            started.set()
            await asyncio.sleep(60)
            raise StopAsyncIteration

    async def stream_completion(**kwargs):
        del kwargs
        return SlowStream()

    async def scenario() -> None:
        provider = AnyLLMChatProvider(
            ProviderConfig("local", "ollama", "model", "Local"),
            api_key=None,
            completion=stream_completion,
        )

        async def consume() -> None:
            async for _ in provider.stream_chat([{"role": "user", "content": "hi"}]):
                pass

        task = asyncio.create_task(consume())
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())


class FakeWriter:
    def __init__(self, reader: asyncio.StreamReader) -> None:
        self.reader = reader
        self.messages: list[dict] = []

    def write(self, value: bytes) -> None:
        message = json.loads(value.decode("utf-8"))
        self.messages.append(message)
        if message.get("method") == "initialize":
            self.reader.feed_data(b'{"id":1,"result":{"platformOs":"windows"}}\n')
        elif message.get("method") == "account/read":
            self.reader.feed_data(
                (json.dumps({"id": message["id"], "result": {"account": {"type": "chatgpt"}}}) + "\n").encode()
            )
        elif message.get("method") == "thread/start":
            self.reader.feed_data(
                (json.dumps({"id": message["id"], "result": {"thread": {"id": "thr-1"}}}) + "\n").encode()
            )
        elif message.get("method") == "turn/start":
            self.reader.feed_data(
                (json.dumps({"id": message["id"], "result": {"turn": {"id": "turn-1"}}}) + "\n").encode()
            )
            self.reader.feed_data(
                b'{"method":"item/agentMessage/delta","params":{"delta":"hello"}}\n'
            )
            self.reader.feed_data(
                b'{"method":"item/fileChange/delta","params":{"delta":"--- a/file.py\\n+++ b/file.py\\n"}}\n'
            )
            self.reader.feed_data(
                b'{"id":77,"method":"item/fileChange/requestApproval","params":{"threadId":"thr-1","turnId":"turn-1","reason":"edit"}}\n'
            )

    async def drain(self) -> None:
        return None

    def close(self) -> None:
        return None


class FakeProcess:
    def __init__(self) -> None:
        self.stdout = asyncio.StreamReader()
        self.stdin = FakeWriter(self.stdout)
        self.stderr = asyncio.StreamReader()
        self.returncode = None

    def terminate(self) -> None:
        self.returncode = 0

    def kill(self) -> None:
        self.returncode = 0

    async def wait(self) -> int:
        return self.returncode or 0


def test_codex_app_server_protocol_stream_and_explicit_approval(tmp_path: Path) -> None:
    async def scenario() -> None:
        process = FakeProcess()
        process_kwargs: dict = {}

        async def factory(*args, **kwargs):
            del args
            process_kwargs.update(kwargs)
            return process

        backend = CodexAppServerBackend(tmp_path, process_factory=factory)
        metadata = await backend.connect()
        assert metadata["platformOs"] == "windows"
        assert (await backend.account())["account"]["type"] == "chatgpt"
        thread = await backend.start_thread(mode="repository_agent")
        assert thread["thread"]["id"] == "thr-1"
        await backend.start_turn("thr-1", "Review this repository")
        first = await anext(backend.events())
        second = await anext(backend.events())
        third = await anext(backend.events())
        assert first.method == "item/agentMessage/delta"
        assert second.method == "item/fileChange/delta"
        assert third.requires_approval
        await backend.resolve_approval(third.request_id, "decline")
        assert process.stdin.messages[-1] == {"id": 77, "result": {"decision": "decline"}}
        thread_start = next(message for message in process.stdin.messages if message.get("method") == "thread/start")
        assert thread_start["params"]["approvalPolicy"] == "untrusted"
        assert thread_start["params"]["sandbox"] == "workspace-write"
        assert process_kwargs["stderr"] is asyncio.subprocess.DEVNULL
        await backend.close()

    asyncio.run(scenario())


def test_codex_read_only_workflows_use_protocol_sandbox_name(tmp_path: Path) -> None:
    async def scenario() -> None:
        process = FakeProcess()

        async def factory(*args, **kwargs):
            del args, kwargs
            return process

        backend = CodexAppServerBackend(tmp_path, process_factory=factory)
        await backend.connect()
        await backend.start_thread(mode="coach")
        thread_start = next(
            message
            for message in process.stdin.messages
            if message.get("method") == "thread/start"
        )
        assert thread_start["params"]["sandbox"] == "read-only"
        await backend.close()

    asyncio.run(scenario())


def test_codex_protocol_error_has_actionable_message() -> None:
    message = friendly_error(
        "Invalid request: unknown variant `readOnly`, expected one of "
        "`read-only`, `workspace-write`, `danger-full-access`"
    )
    assert "协议不兼容" in message
    assert "更新 Codex CLI" in message


def test_codex_request_send_failure_does_not_leave_pending_future(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        backend = CodexAppServerBackend(tmp_path)
        with pytest.raises(CodexBackendError, match="not connected"):
            await backend.request("thread/start")
        assert backend._pending == {}

    asyncio.run(scenario())


def test_codex_cancel_retry_and_invalid_approval_fail_closed(tmp_path: Path) -> None:
    async def scenario() -> None:
        process = FakeProcess()

        async def factory(*args, **kwargs):
            del args, kwargs
            return process

        backend = CodexAppServerBackend(tmp_path, process_factory=factory)
        await backend.connect()
        thread = await backend.start_thread(mode="coach")
        await backend.start_turn(thread["thread"]["id"], "first")
        await backend.start_turn(thread["thread"]["id"], "retry")
        with pytest.raises(CodexBackendError, match="unsupported approval"):
            await backend.resolve_approval(1, "approve_everything")
        # The fake server does not implement interrupt; verify the exact request shape
        # without waiting for its response.
        request_task = asyncio.create_task(backend.interrupt("thr-1", "turn-1"))
        await asyncio.sleep(0)
        interrupt = process.stdin.messages[-1]
        assert interrupt["method"] == "turn/interrupt"
        assert interrupt["params"] == {"threadId": "thr-1", "turnId": "turn-1"}
        request_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await request_task
        await backend.close()

    asyncio.run(scenario())
