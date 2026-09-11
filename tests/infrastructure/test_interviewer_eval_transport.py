"""Explicit existing-adapter entry. All transports below are synthetic."""
import asyncio
from types import SimpleNamespace
import pytest
from scripts.evaluate_interviewer_expertise import transmit_authorized_case
from llm_interview_lab.ai.base import ChatEvent, ContextPreview, ContextPart
from llm_interview_lab.ai.codex_backend import CodexEvent


@pytest.mark.parametrize("kind", ["provider", "codex"])
def test_explicit_eval_uses_frozen_parameters_and_default_no_network(kind):
    calls = []
    descriptor = {"provider_id":"synthetic", "model":"unchanged-model", "reasoning_effort":"high", "base_url":"http://synthetic.invalid"}
    preview = ContextPreview("interviewer", "synthetic", (ContextPart("input", "合成输入", "独立合成代码与回答", "a"*64),))
    class Provider:
        config = SimpleNamespace(**descriptor)
        async def stream_chat(self, messages):
            calls.append(messages)
            yield ChatEvent("delta", text="脚本响应")
    class Codex:
        async def start_turn(self, thread, prompt, **kw):
            calls.append((thread,prompt,kw))
            return {"turn":{"id":"t1"}}
        async def events(self):
            yield CodexEvent("item/agentMessage/delta", {"turnId":"t1","delta":"脚本响应"})
            yield CodexEvent("turn/completed", {"turn":{"id":"t1","status":"completed"}})
    args = {"provider":Provider()} if kind=="provider" else {"codex_backend":Codex(),"thread_id":"explicit-eval-thread","output_schema":{"type":"object"}}
    def call(**kw): return asyncio.run(transmit_authorized_case(preview,"协议",descriptor=descriptor,**args,**kw))
    prepared=call()
    assert prepared["network_calls"]==0 and calls==[]
    with pytest.raises(ValueError): call(execute=True)
    with pytest.raises(ValueError): call(execute=True,consent_sha256="bad")
    assert calls==[]
    sent=call(execute=True,consent_sha256=prepared["consent_sha256"])
    assert sent["network_calls"]==1 and len(calls)==1
    assert sent["raw_response"]=="脚本响应" and sent["semantic_quality"]=="UNRUN"
    if kind=="codex":
        assert calls[0][2]["model"]==descriptor["model"] and calls[0][2]["effort"]=="high"
    descriptor["reasoning_effort"]="low"
    with pytest.raises(ValueError): call(execute=True,consent_sha256=prepared["consent_sha256"])
    assert len(calls)==1
