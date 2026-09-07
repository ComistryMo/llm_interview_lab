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
