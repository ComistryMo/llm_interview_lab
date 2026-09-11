"""Two bounded regressions: compiled resource grants and exact sent quotes."""
from copy import deepcopy
import hashlib
import json

import pytest

from tests.infrastructure.test_interviewer_evidence import unified, public_repo, new_v3, context, packet, commit
from llm_interview_lab.ai.context_builder import build_role_interview_context_preview
from llm_interview_lab.role_interviews import RoleInterviewError


def contract(preview):
    return json.loads(next(p.content for p in preview.parts if p.id == "interview_contract"))


def test_ordinary_cards_coexist_with_fallback_experts(unified, monkeypatch):
    from llm_interview_lab.knowledge import KnowledgeCatalog
    service, profile = unified
    knowledge = service.knowledge_catalog()
    card = knowledge.cards["EGT-QB-002"]
    role = service.roles.resolve_role("post_training_engineer")
    assert set(card.skills) & set(role.skill_weights) and not card.raw.get("expert_reference")
    iid = new_v3(service, profile)
    answer = "我负责组内优势计算。"
    service.answer_interview(profile, iid, "q-001", answer)
    c = context(service, profile, iid, answer)
    value = packet(c)
    value["follow_up"] = "请介绍混合精度中的算子dtype与主权重。"
    commit(service, profile, iid, c, value)
    answer = "混合精度需要区分主权重与算子dtype。"
    service.answer_interview(profile, iid, "q-002", answer)
    # Only the retrieval boundary is controlled; compiler/budget/transaction are real.
    monkeypatch.setattr(KnowledgeCatalog, "interview_candidates", lambda *a, **kw: (card, card))
    preview = build_role_interview_context_preview(service.repo_root, profile, iid, candidate_answer=answer,
        include_materials=False, catalog=service.catalog, role_catalog=service.roles, knowledge=knowledge)
    c = contract(preview)
    assert c["expert_references"] and all(r["priority"] == 3 for r in c["expert_references"])
    ordinary = json.loads(next(p.content for p in preview.parts if p.id == "knowledge_candidates"))
    assert [x["id"] for x in ordinary["cards"]] == [card.id]
    assert card.prompt in ordinary["cards"][0]["prompt"]
    assert c["loaded_knowledge_ids"] == list(dict.fromkeys([card.id] + [r["topic_id"] for r in c["expert_references"]]))
    from llm_interview_lab.ai.interview_context_budget import bounded_parts, part, enforce_wire_budget
    from llm_interview_lab.ai.base import ContextPreview
    from llm_interview_lab.desktop.controller import _dynamic_response_schema
    from llm_interview_lab.interview_flow import next_question_instruction
    before = service.interview_session(profile, iid)
    expert_id = c["expert_references"][0]["topic_id"]
    # A same-topic ordinary card must survive beside a single expert criterion.
    same_topic = knowledge.cards[expert_id]
    for overflow in (False, True):
        optional = deepcopy(ordinary)
        optional["cards"].append({"id": same_topic.id, "prompt": same_topic.prompt})
        if overflow:
            optional["cards"][0]["prompt"] = "隔离公开候选的预算压力文本。" * 6000
        parts = [p for p in preview.parts if p.id != "knowledge_candidates"] + [part("knowledge_candidates", "候选", optional)]
        compiled = ContextPreview("interviewer", profile, tuple(bounded_parts(parts, deepcopy(c), before)))
        final = contract(compiled)
        expected = list(dict.fromkeys(([card.id, expert_id] if not overflow else []) + [r["topic_id"] for r in final["expert_references"]]))
        assert final["loaded_knowledge_ids"] == expected
        assert any(p.id == "knowledge_candidates" for p in compiled.parts) == (not overflow)
        for resource in compiled.parts:
            assert resource.sha256 == hashlib.sha256(resource.content.encode()).hexdigest()
        instruction = next_question_instruction(3)
        provider = [{"role": "system", "content": compiled.selected_text}, {"role": "user", "content": instruction}]
        codex = {"prompt": compiled.selected_text + "\n\n## Frozen scorecard contract\n" + instruction,
            "output_schema": _dynamic_response_schema(compiled, set(), set())}
        for wire in (provider, codex):
            enforce_wire_budget(json.dumps(wire, ensure_ascii=False))
        # Both transports contain this exact compiled contract, not a stale dictionary.
        contract_text = next(p.content for p in compiled.parts if p.id == "interview_contract")
        assert contract_text in provider[0]["content"] and contract_text in codex["prompt"]
        if overflow:
            invalid = packet(final, intro=False, claim_ref="claim-0001", experience_ref="exp-0001")
            invalid["state_update"]["claims"][0]["evidence"]["quote"] = answer
            invalid["probe"]["knowledge_ids"] = [card.id]
            with pytest.raises(RoleInterviewError, match="未加载"):
                commit(service, profile, iid, final, invalid)
            assert service.interview_session(profile, iid) == before
    mandatory = [p for p in preview.parts if p.id != "candidate_answer"] + [part("candidate_answer", "当前回答", "长" * 49000, True)]
    with pytest.raises(ValueError, match="预算"):
        bounded_parts(mandatory, deepcopy(c), before)
    value = packet(c, intro=False, claim_ref="claim-0001", experience_ref="exp-0001")
    value["state_update"]["claims"][0]["evidence"]["quote"] = answer
    value["probe"]["knowledge_ids"] = [card.id]
    assert commit(service, profile, iid, c, value)["interviewer_state"]["revision"] == 2


def test_repeated_sent_quotes_persist_same_locations_in_all_updates(unified):
    service, profile = unified
    iid = new_v3(service, profile)
    quote = "我负责组内优势计算"
    old = quote + "。旧片段结束。" + quote + "。"
    service.answer_interview(profile, iid, "q-001", old)
    c = context(service, profile, iid, old)
    commit(service, profile, iid, c, packet(c))
    answer = quote + "。前段。" + quote + "，现在澄清具体实现。"
    service.answer_interview(profile, iid, "q-002", answer)
    c = context(service, profile, iid, answer)
    before = service.interview_session(profile, iid)
    c["sent_answer_sources"] = [{"question_id": qid, "answer_sha256": before["answers"][qid]["sha256"],
        "ranges": [{"start": text.rindex(quote), "end": len(text)}]} for qid, text in (("q-001", old), ("q-002", answer))]
    value = packet(c, intro=False, claim_ref="claim-0001", experience_ref="exp-0001", status="model_supported")
    update = value["state_update"]
    historical = {"question_id": "q-001", "quote": quote}
    current = {"question_id": "q-002", "quote": quote}
    update["experiences"] = [{"ref": "new:history", "label": "补充历史出处", "evidence": historical}]
    new_claim = deepcopy(update["claims"][0])
    new_claim.update(ref="new:boundary", criterion="boundary", status="partial")
    update["claims"].append(new_claim)
    update["contradictions"] = [{"claim_ref": "claim-0001", "first": historical, "second": current,
        "ambiguity": "前后实现说明需要澄清", "resolved": True, "resolution": "本轮澄清原话含义，仅为脚本状态验证。"}]
    update["closures"] = [{"claim_ref": "claim-0001", "reason": "sufficient", "evidence": historical}]
    value["probe"].update(claim_ref="new:boundary", criterion="boundary")
    untouched = deepcopy(value)
    for damage in ("empty", "none", "missing", "hash", "outside", "split"):
        invalid = deepcopy(c)
        if damage in ("empty", "none"):
            invalid["sent_answer_sources"] = [] if damage == "empty" else None
        elif damage == "missing":
            invalid.pop("sent_answer_sources")
        elif damage == "hash":
            invalid["sent_answer_sources"][0]["answer_sha256"] = "0" * 64
        elif damage == "outside":
            invalid["sent_answer_sources"][0]["ranges"] = [{"start": len(old)-1, "end": len(old)}]
        else:
            start = old.rindex(quote)
            invalid["sent_answer_sources"][0]["ranges"] = [{"start": start, "end": start+3}, {"start": start+3, "end": len(old)}]
        with pytest.raises(RoleInterviewError, match="实际发送"):
            commit(service, profile, iid, invalid, value)
        assert service.interview_session(profile, iid) == before
    invalid = deepcopy(value)
    invalid["state_update"]["claims"][0]["evidence"] = historical
    with pytest.raises(RoleInterviewError, match="当前已锁定"):
        commit(service, profile, iid, c, invalid)
    assert service.interview_session(profile, iid) == before
    saved = commit(service, profile, iid, c, value)
    state = saved["interviewer_state"]
    citations = [state["experiences"]["exp-0002"]["evidence"], state["claims"]["claim-0001"]["evidence"][-1],
        state["claims"]["claim-0002"]["evidence"][-1], state["contradictions"]["claim-0001"]["first"],
        state["contradictions"]["claim-0001"]["second"], *[x["evidence"] for x in state["closures"]]]
    for anchored in citations:
        text = old if anchored["question_id"] == "q-001" else answer
        assert anchored["start"] == text.rindex(quote)
        assert text[anchored["start"]:anchored["end"]] == anchored["quote"] == quote
        assert anchored["answer_sha256"] == before["answers"][anchored["question_id"]]["sha256"]
    assert value == untouched
    assert state["claims"]["claim-0001"]["evidence"][0]["start"] == 0  # Never relocate historical evidence.
    assert type(service)(service.repo_root).interview_session(profile, iid) == saved


@pytest.mark.parametrize("qid,text,quote,ranges,expected", [
    ("q-001", "ab--ab", "ab", [(4, 6)], (4, "ab")),
    ("q-001", "ab--ab", "ab", [(4, 6), (0, 2)], (0, "ab")),
    ("q-001", "ab--a`b", "ab", [(4, 7)], (4, "a`b")),
    ("q-001", "a`b--ab", "ab", [(0, 3), (5, 7)], (5, "ab")),
    ("q-001", "ab--ab", "ab", None, (0, "ab")),
    ("q-001", "ab", "ab", [], None),
    ("q-001", "ab", "ab", {}, None),
    ("q-001", "ab--cd", "abcd", [(0, 2), (4, 6)], None),
    ("q-001", "ab", "ab", [(-1, 2)], None),
    ("q-001", "ab", "ab", [(0, 3)], None),
    ("q-001", "ab", "ab", [(True, 2)], None),
    *[(prefix + "q-004", "a`b", "ab", [(0, 3)], None) for prefix in ("code:", "run:", "test:")],
    *[(prefix + "q-004", "a  b", "a b", [(0, 4)], None) for prefix in ("code:", "run:", "test:")],
])
def test_scoped_anchor_exact_priority_and_strict_sources(qid, text, quote, ranges, expected):
    from llm_interview_lab.interviewer_state import anchor
    digest = hashlib.sha256(text.encode()).hexdigest()
    scope = None if ranges is None else ([{"question_id": qid, "answer_sha256": digest,
        "ranges": [{"start": a, "end": b} for a, b in ranges]}] if ranges else ranges)
    if expected is None:
        with pytest.raises(ValueError):
            anchor({"question_id": qid, "quote": quote}, {qid: (text, digest)}, scope)
    else:
        result = anchor({"question_id": qid, "quote": quote}, {qid: (text, digest)}, scope)
        assert (result["start"], result["quote"]) == expected
        assert text[result["start"]:result["end"]] == result["quote"]
