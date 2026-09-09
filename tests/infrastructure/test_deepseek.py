"""Vendor wire contracts; no network and no real Keyring in unit tests."""
import asyncio
import json
from pathlib import Path

import httpx
import pytest

from llm_interview_lab.ai.providers import OpenAICompatibleChatProvider, ProviderConfig, ProviderError, create_chat_provider
from llm_interview_lab.desktop.coding_statements_zh import CONTRACTS, chinese_statement

pytestmark = pytest.mark.infrastructure


@pytest.mark.parametrize("effort", [None, "none", "low", "high", "max"])
def test_deepseek_wire_and_reasoning_content_is_not_an_answer(effort):
    requests, clients = [], []
    def handle(request):
        payload = json.loads(request.content)
        requests.append(payload)
        assert str(request.url) == "https://api.deepseek.com/chat/completions"
        if not payload.get("stream"):
            return httpx.Response(200, json={"choices": [{"message": {"content": "OK"}}]})
        chunks = [{"choices": [{"delta": {"reasoning_content": "not an answer"}}]},
                  {"choices": [{"delta": {"content": '{"follow_up":"请说明你的贡献。"}'}}]},
                  {"choices": [{"delta": {}, "finish_reason": "stop"}]}]
        body = "\n\n".join("data: " + json.dumps(chunk) for chunk in chunks) + "\n\ndata: [DONE]\n\n"
        return httpx.Response(200, text=body)
    def client(**kwargs):
        value = httpx.AsyncClient(transport=httpx.MockTransport(handle), **kwargs)
        clients.append(value)
        return value
    config = ProviderConfig("test", "deepseek", "deepseek-v4-flash", "DeepSeek", reasoning_effort=effort)
    assert isinstance(create_chat_provider(config, api_key="fake-key"), OpenAICompatibleChatProvider)
    provider = OpenAICompatibleChatProvider(config, api_key="fake-key", client_factory=client)
    async def run():
        assert (await provider.test_connection()).ok
        events = [event async for event in provider.stream_chat([{"role": "user", "content": "合成测试"}], json_mode=True)]
        assert "".join(e.text for e in events) == '{"follow_up":"请说明你的贡献。"}'
    asyncio.run(run())
    assert all(c.is_closed for c in clients)
    assert requests[0]["thinking"] == {"type": "disabled"}
    assert requests[1]["response_format"] == {"type": "json_object"}
    assert requests[1]["thinking"]["type"] == ("disabled" if effort == "none" else "enabled")
    assert requests[1].get("reasoning_effort") == (effort if effort not in {None, "none"} else None)


@pytest.mark.parametrize("finish", ["length", "content_filter", "insufficient_system_resource", "stop"])
def test_deepseek_incomplete_or_reasoning_only_is_not_success(finish):
    def handle(request):
        return httpx.Response(200, text='data: ' + json.dumps({"choices": [{"delta": {"reasoning_content": "internal"}, "finish_reason": finish}]}) + '\n\n')
    provider = OpenAICompatibleChatProvider(
        ProviderConfig("test", "deepseek", "deepseek-v4-flash", "DeepSeek"), api_key="fake-key",
        client_factory=lambda **kwargs: httpx.AsyncClient(transport=httpx.MockTransport(handle), **kwargs))
    async def run():
        with pytest.raises(ProviderError, match="未完整|未返回回答正文"):
            _ = [event async for event in provider.stream_chat([{"role": "user", "content": "test"}])]
    asyncio.run(run())


def test_deepseek_high_keeps_reasoning_and_requested_json_output():
    """Wire contract only: explicit JSON must not silently become free text."""
    requests = []

    def handle(request):
        payload = json.loads(request.content)
        requests.append(payload)
        assert payload["thinking"] == {"type": "enabled"}
        assert payload["reasoning_effort"] == "high"
        assert payload["response_format"] == {"type": "json_object"}
        final = '{"follow_up":"请说明如何验证收益？"}'
        chunks = [
            {"choices": [{"delta": {"reasoning_content": "private internal reasoning", "content": None}}]},
            {"choices": [{"delta": {"content": final}, "finish_reason": "stop"}]},
            {"choices": [], "usage": {"completion_tokens": 200}},
        ]
        return httpx.Response(200, text="\n\n".join("data: " + json.dumps(c) for c in chunks) + "\n\ndata: [DONE]\n\n")

    provider = OpenAICompatibleChatProvider(
        ProviderConfig("test", "deepseek", "deepseek-v4-flash", "DeepSeek", reasoning_effort="high"),
        api_key="fake-key", client_factory=lambda **kw: httpx.AsyncClient(transport=httpx.MockTransport(handle), **kw))

    async def run():
        events = [e async for e in provider.stream_chat([{"role": "user", "content": 'Return JSON: {"follow_up":"..."}'}], json_mode=True)]
        assert "".join(e.text for e in events) == '{"follow_up":"请说明如何验证收益？"}'
        assert events[-1].kind == "completed"

    asyncio.run(run())
    assert len(requests) == 1, "Never silently retry/disable thinking or spend another request"


@pytest.mark.parametrize(("chunks", "expected"), [
    ([{"choices": [{"delta": {"content": "  \n"}, "finish_reason": "stop"}]}], "空白"),
    ([{"choices": [{"delta": {"reasoning_content": "private"}, "finish_reason": "stop"}]}], "仅返回思考"),
    ([{"choices": [{"delta": {"content": '{"follow_up":"incomplete"}'}}]}], "中断"),
    ([{"error": {"code": 429, "message": "private-key-and-prompt"}}], "429"),
    ([{"error": {"code": "unknown", "message": "private-key-and-prompt"}}], "服务端错误"),
    ([{"choices": [{"delta": {"content": "partial"}, "finish_reason": "length"}]}], "输出预算"),
])
def test_stream_failure_is_actionable_and_cannot_become_completed(chunks, expected):
    clients = []

    def client(**kwargs):
        body = "\n\n".join("data: " + json.dumps(c) for c in chunks) + "\n\n"
        value = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, text=body)), **kwargs)
        clients.append(value)
        return value

    provider = OpenAICompatibleChatProvider(
        ProviderConfig("test", "deepseek", "deepseek-v4-flash", "DeepSeek", reasoning_effort="high"),
        api_key="fake-key", client_factory=client)
    events = []

    async def run():
        with pytest.raises(ProviderError, match=expected) as failure:
            async for event in provider.stream_chat([{"role": "user", "content": "synthetic"}], json_mode=True):
                events.append(event)
        assert "private" not in str(failure.value)

    asyncio.run(run())
    assert all(e.kind != "completed" for e in events)
    assert all(c.is_closed for c in clients)


@pytest.mark.parametrize(("finish", "code"), [
    ("stop", "AI_RESPONSE_REASONING_ONLY"),
    ("length", "AI_RESPONSE_TRUNCATED"),
    ("content_filter", "AI_RESPONSE_FILTERED"),
    ("insufficient_system_resource", "AI_RESPONSE_RESOURCE"),
    ("tool_calls", "AI_RESPONSE_UNEXPECTED_FINISH"),
])
def test_stream_diagnostic_distinguishes_finish_and_keeps_only_metadata(finish, code):
    requests = []
    private = "synthetic-private-answer-and-reasoning"
    request_id = "12345678-1234-1234-1234-123456789abc"
    response_id = "chatcmpl-1234567890abcdef"

    def handle(request):
        requests.append(json.loads(request.content))
        chunk = {
            "id": response_id, "model": private, "unknown": private,
            "choices": [{"delta": {"reasoning_content": private}, "finish_reason": finish}],
            "usage": {"prompt_tokens": 40, "completion_tokens": 100, "total_tokens": 140,
                      "completion_tokens_details": {"reasoning_tokens": 100, "secret": private},
                      "secret": private},
        }
        return httpx.Response(200, headers={"x-request-id": request_id, "authorization": private},
                              text="data: " + json.dumps(chunk) + "\n\ndata: [DONE]\n\n")

    provider = OpenAICompatibleChatProvider(
        ProviderConfig("test", "deepseek", "deepseek-v4-flash", "DeepSeek", reasoning_effort="high"),
        api_key="sk-synthetic-secret", client_factory=lambda **kw: httpx.AsyncClient(transport=httpx.MockTransport(handle), **kw))

    async def run():
        with pytest.raises(ProviderError):
            _ = [e async for e in provider.stream_chat([{"role": "user", "content": private}], json_mode=True)]

    asyncio.run(run())
    diagnostic = provider.last_diagnostic
    assert diagnostic["code"] == code
    assert diagnostic["finish_reason"] == finish
    assert diagnostic["request_id"] == request_id and diagnostic["response_id"] == response_id
    assert diagnostic["http_status"] == 200
    assert diagnostic["usage"] == {"prompt_tokens": 40, "completion_tokens": 100, "total_tokens": 140, "reasoning_tokens": 100}
    assert diagnostic["content_chars"] == 0 and diagnostic["reasoning_chars"] == len(private)
    assert diagnostic["first_content_ms"] is None and diagnostic["elapsed_ms"] >= 0
    assert diagnostic["max_tokens"] == "provider_default"
    assert private not in json.dumps(diagnostic) and "sk-synthetic-secret" not in json.dumps(diagnostic)
    assert len(requests) == 1 and requests[0]["reasoning_effort"] == "high"
    assert requests[0]["response_format"] == {"type": "json_object"}


@pytest.mark.parametrize(("ending", "code", "finish"), [
    ("", "AI_RESPONSE_INTERRUPTED", None),
    ("data: [DONE]\n\n", "AI_RESPONSE_REASONING_ONLY", None),
    ('data: {"choices":[{"delta":{},"finish_reason":"untrusted-secret"}]}\n\n', "AI_RESPONSE_UNEXPECTED_FINISH", "other"),
])
def test_stream_diagnostic_does_not_invent_finish_or_token_usage(ending, code, finish):
    chunk = {"id": "sk-synthetic-secret", "choices": [{"delta": {"reasoning_content": "synthetic private reasoning"}}],
             "usage": {"completion_tokens": "synthetic secret", "total_tokens": True}}
    provider = OpenAICompatibleChatProvider(
        ProviderConfig("test", "deepseek", "deepseek-v4-flash", "DeepSeek"), api_key="fake",
        client_factory=lambda **kw: httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(
            200, headers={"x-request-id": "sk-synthetic-secret"}, text="data: " + json.dumps(chunk) + "\n\n" + ending)), **kw))

    async def run():
        with pytest.raises(ProviderError):
            _ = [e async for e in provider.stream_chat([{"role": "user", "content": "synthetic"}])]

    asyncio.run(run())
    diagnostic = provider.last_diagnostic
    assert diagnostic["code"] == code and diagnostic["finish_reason"] == finish
    assert diagnostic["done_marker"] is ("[DONE]" in ending)
    assert diagnostic["usage"] == {}  # Missing usage is unknown, not zero cost.
    assert diagnostic["request_id"] is None and diagnostic["response_id"] is None
    assert "secret" not in json.dumps(diagnostic) and "private" not in json.dumps(diagnostic)


def test_read_timeout_retains_partial_counts_not_private_text():
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'data: {"choices":[{"delta":{"reasoning_content":"private"}}]}\n\n'
            raise httpx.ReadTimeout("private request and key")

    provider = OpenAICompatibleChatProvider(
        ProviderConfig("test", "deepseek", "deepseek-v4-flash", "DeepSeek"), api_key="fake",
        client_factory=lambda **kw: httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=Stream())), **kw))

    async def run():
        with pytest.raises(ProviderError, match="timed out"):
            _ = [e async for e in provider.stream_chat([{"role": "user", "content": "synthetic"}])]

    asyncio.run(run())
    assert provider.last_diagnostic["code"] == "AI_REQUEST_TIMEOUT"
    assert provider.last_diagnostic["timeout_kind"] == "read"
    assert provider.last_diagnostic["reasoning_chars"] == 7
    assert provider.last_diagnostic["finish_reason"] is None
    assert "private" not in json.dumps(provider.last_diagnostic)


@pytest.mark.parametrize("status", [401, 429, 503])
def test_http_failure_diagnostic_discards_service_body(status):
    private = "sk-synthetic-private-key-and-request"
    provider = OpenAICompatibleChatProvider(
        ProviderConfig("test", "deepseek", "deepseek-private-model", "DeepSeek"), api_key=private,
        client_factory=lambda **kw: httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(
            status, json={"error": {"message": private}}, headers={"x-request-id": private})), **kw))

    async def run():
        with pytest.raises(ProviderError) as failure:
            _ = [e async for e in provider.stream_chat([{"role": "user", "content": private}])]
        assert private not in str(failure.value)

    asyncio.run(run())
    assert provider.last_diagnostic["code"] == "AI_HTTP_ERROR"
    assert provider.last_diagnostic["http_status"] == status
    assert provider.last_diagnostic["request_id"] is None
    assert provider.last_diagnostic["usage"] == {}
    assert provider.last_diagnostic["model"] == "custom"
    assert "deepseek-private-model" not in json.dumps(provider.last_diagnostic)
    assert private not in json.dumps(provider.last_diagnostic)


def test_stream_diagnostic_resets_between_requests_without_reconnecting():
    calls = []

    def handle(request):
        calls.append(request)
        text = " \n" if len(calls) == 1 else '{"follow_up":"合成追问"}'
        chunk = {"choices": [{"delta": {"content": text}, "finish_reason": "stop"}]}
        return httpx.Response(200, text="data: " + json.dumps(chunk) + "\n\ndata: [DONE]\n\n")

    provider = OpenAICompatibleChatProvider(
        ProviderConfig("test", "deepseek", "deepseek-v4-flash", "DeepSeek", reasoning_effort="high"), api_key="fake",
        client_factory=lambda **kw: httpx.AsyncClient(transport=httpx.MockTransport(handle), **kw))

    async def run():
        with pytest.raises(ProviderError, match="空白"):
            _ = [e async for e in provider.stream_chat([{"role": "user", "content": "synthetic"}], json_mode=True)]
        assert provider.last_diagnostic["code"] == "AI_RESPONSE_EMPTY"
        assert provider.last_diagnostic["first_content_ms"] is None
        events = [e async for e in provider.stream_chat([{"role": "user", "content": "synthetic"}], json_mode=True)]
        assert events[-1].kind == "completed"

    asyncio.run(run())
    assert provider.last_diagnostic["code"] == ""
    assert provider.last_diagnostic["first_content_ms"] is not None
    assert provider.last_diagnostic["done_marker"] and provider.last_diagnostic["finish_reason"] == "stop"
    assert provider.last_diagnostic["reasoning_chars"] == 0
    assert len(calls) == 2 and all(json.loads(r.content)["stream"] for r in calls)


def test_current_chinese_statements_match_frozen_sources_and_keep_interfaces():
    import re
    root = Path(__file__).resolve().parents[2] / "curriculum/problems"
    seen = set()
    for path in root.glob("*/task.md"):
        original = path.read_text(encoding="utf-8")
        problem_id = re.match(r"# ([A-Z]+(?:-[A-Z]+)?-\d+)", original)[1]
        translated = chinese_statement(problem_id, original)
        assert "尚未同步" not in translated, problem_id
        assert re.search("[\u4e00-\u9fff]", translated), problem_id
        for code in re.findall(r"```python\n.*?```", original, re.DOTALL):
            assert code in translated, problem_id
        if problem_id in CONTRACTS:
            seen.add(problem_id)
            assert "## 题目要求" in translated
    assert seen == set(CONTRACTS)
    assert "尚未同步" in chinese_statement("FND-002", "changed historical statement")
    assert "尚未同步" in chinese_statement("PT-005", "changed historical Chinese statement")
