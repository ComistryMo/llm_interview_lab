"""Production compiler and scripted transactions; semantic quality is UNRUN."""
import json
from copy import deepcopy
import pytest
from tests.infrastructure.test_interviewer_evidence import unified, public_repo, new_v3, context, packet, commit
from llm_interview_lab.ai.context_builder import build_role_interview_context_preview
from llm_interview_lab.desktop.controller import _dynamic_response_schema
from pathlib import Path

GRPO_ANSWERS = [
    ("充分", "我负责组内优势计算。采用总体标准差，[0,0,1,1]的优势为[-1,-1,1,1]；全相同奖励中心化为零，但KL项未必没有梯度。", "model_supported"),
    ("空泛", "我负责组内优势计算。GRPO、PPO、CoT、reward这些都用了，效果很好。", "partial"),
    ("错误", "我负责组内优势计算。奖励全相同时必须把优势设成正一，这样能保证训练更新正确。", "disputed"),
    ("未知", "我负责组内优势计算。但零方差怎样处理我不清楚，我没做过这部分。", "explicit_unknown"),
    ("矛盾", "我负责组内优势计算。我们每一步更新reference策略，之前也是如此。", "disputed"),
    ("回避", "我负责组内优势计算。先别讨论计算细节吧，我们团队最终交付得很漂亮。", "partial"),
]


@pytest.mark.parametrize("label,answer,status", GRPO_ANSWERS)
def test_grpo_compiled_expertise_and_scripted_transaction(unified, label, answer, status):
    service, profile = unified
    iid = new_v3(service, profile)
    opening = "我负责组内优势计算，使用GRPO；reference始终冻结。"
    service.answer_interview(profile, iid, "q-001", opening)
    c = context(service, profile, iid, opening)
    value = packet(c, criterion="advantage")
    value["state_update"]["claims"][0]["topic_id"] = "EGT-QB-028"
    value["probe"]["topic_id"] = "EGT-QB-028"
    value["follow_up"] = "你实现的GRPO如何计算组内优势？请用一个奖励组解释退化边界。"
    commit(service, profile, iid, c, value)
    service.answer_interview(profile, iid, "q-002", answer)
    preview = build_role_interview_context_preview(service.repo_root, profile, iid, candidate_answer=answer,
        include_materials=False, catalog=service.catalog, role_catalog=service.roles)
    c = json.loads(next(p.content for p in preview.parts if p.id == "interview_contract"))
    assert 1 <= len(c["methods"]) <= 2
    refs = c["expert_references"]
    assert refs[0]["topic_id"] == "EGT-QB-028" and refs[0]["criterion"] == "advantage"
    assert refs[0]["claim_ids"] == ["claim-0001"]
    assert "DeepSeekMath" in preview.selected_text and "source_pins" in preview.selected_text
    assert c["methods"][0]["sha256"] and all(m["path"].startswith("coach/skills/") for m in c["methods"])
    wire_schema = _dynamic_response_schema(preview, set(), set())
    assert wire_schema["properties"]["probe"] == c["response_schema"]["properties"]["probe"]
    value = packet(c, intro=False, criterion="advantage", status=status, claim_ref="claim-0001", experience_ref="exp-0001")
    value["state_update"]["claims"][0]["topic_id"] = "EGT-QB-028"
    value["probe"].update(topic_id="EGT-QB-028", method_id=c["methods"][0]["id"], knowledge_ids=["EGT-QB-028"])
    if status == "explicit_unknown":
        value["probe"]["action"] = "adjacent"
    if status == "model_supported":
        # Script explicitly accepts evidence; new criterion remains a separate gap.
        other = deepcopy(value["state_update"]["claims"][0])
        other.update(ref="new:ratio", criterion="ratio", status="unassessed", statement="更新路径尚待核实")
        value["state_update"]["claims"].append(other)
        value["probe"].update(claim_ref="new:ratio", criterion="ratio", action="change_angle")
    if label == "矛盾":
        value["state_update"]["contradictions"] = [{"claim_ref": "claim-0001",
            "first": {"question_id": "q-001", "quote": "reference始终冻结"},
            "second": {"question_id": "q-002", "quote": "每一步更新reference策略"},
            "ambiguity": "两个时机是否指同一策略仍需澄清", "resolved": False, "resolution": ""}]
    saved = commit(service, profile, iid, c, value)
    assert saved["interviewer_state"]["revision"] == 2
    assert saved["questions"][-1]["question_id"] == "q-003"
    assert saved["interviewer_state"]["claims"]["claim-0001"]["criterion_status"] == status
    print(json.dumps({"synthetic": True, "semantic_quality": "UNRUN", "methods": c["loaded_method_ids"],
        "references": [(r["topic_id"], r["criterion"], r["reason"]) for r in refs]}, ensure_ascii=False))


def test_long_actual_compilation_rejects_unsent_old_quotes_and_overflow(unified):
    from scripts.evaluate_interviewer_expertise import compile_input
    from llm_interview_lab.ai.context_builder import ContextBuilderError
    from llm_interview_lab.ai.interview_context_budget import measure
    from llm_interview_lab.role_interviews import RoleInterviewError
    service, profile = unified
    value = {"role_id": "post_training_engineer", "difficulty": "hard",
        "question": "请解释GRPO的组优势与退化组。", "answer": "我负责组内优势计算。GRPO采用组均值。",
        "history": [{"question": f"请解释合成实验第{i}步的实现与验证方式。",
                     "answer": "我负责这部分合成实验。" + "这是公开合成的长回答。" * 550 + f"未发送的尾部标记{i}。"} for i in range(8)]}
    iid, preview = compile_input(service, profile, value)
    contract = json.loads(next(p.content for p in preview.parts if p.id == "interview_contract"))
    assert contract["history_omitted_count"] >= 6
    assert "未发送的尾部标记0" not in preview.selected_text
    assert next(p.content for p in preview.parts if p.id == "candidate_answer") == value["answer"]
    assert service.interview_answer_text(profile, iid, "q-001").endswith("未发送的尾部标记0。")
    invalid = packet(contract, intro=False, criterion="contribution", claim_ref="claim-0001", experience_ref="")
    invalid["state_update"]["closures"] = [{"claim_ref": "claim-0001", "reason": "sufficient",
        "evidence": {"question_id": "q-001", "quote": "未发送的尾部标记0"}}]
    before = service.interview_session(profile, iid)
    with pytest.raises(RoleInterviewError, match="实际发送"):
        commit(service, profile, iid, contract, invalid)
    assert service.interview_session(profile, iid) == before
    with pytest.raises(ContextBuilderError, match="预算"):
        build_role_interview_context_preview(service.repo_root, profile, iid, candidate_answer="长" * 50000,
            include_materials=False, catalog=service.catalog, role_catalog=service.roles)
    print("long_compiled_request", json.dumps(measure(preview.selected_text)), "omitted", contract["history_omitted_count"])


def test_method_allowlist_and_latest_answer_change_route(unified):
    from llm_interview_lab.interview_expertise import route_methods, load_methods
    from llm_interview_lab.interviewer_state import empty_state
    service, profile = unified
    refs = [{"topic_id": "EGT-QB-028", "criterion": "advantage"}]
    unknown = route_methods("experience", empty_state(), "GRPO我不知道，记不清", "post_training_engineer", "hard", refs)
    failure = route_methods("experience", empty_state(), "GRPO这段代码反向传播出现NaN", "post_training_engineer", "hard", refs)
    assert unknown[0]["id"] == "counterexample-constraint-transfer"
    assert failure[0]["id"] == "code-defense-failure-analysis"
    iid = new_v3(service, profile)
    answer = "我负责GRPO实现，这段代码反向传播出现NaN。"
    service.answer_interview(profile, iid, "q-001", answer)
    compiled = context(service, profile, iid, answer)
    assert compiled["methods"][0]["id"] == "code-defense-failure-analysis"
    assert "不改 submission" in compiled["methods"][0]["content"]
    with pytest.raises(ValueError, match="白名单"):
        load_methods(service.repo_root, [{"id": "../../private"}])


def test_all_eight_expert_topics_match_state_criteria_and_sources(unified):
    from llm_interview_lab.knowledge import load_knowledge
    from llm_interview_lab.interview_expertise import TOPICS
    from llm_interview_lab.interviewer_state import CRITERIA
    service, _ = unified
    knowledge = load_knowledge(service.repo_root, curriculum=service.catalog)
    for topic in TOPICS:
        card = knowledge.cards[topic]
        reference = card.raw["expert_reference"]
        assert set(reference["criteria"]) <= set(CRITERIA)
        assert reference["source_pins"] and card.source_claims
        for criterion in reference["criteria"].values():
            assert all(criterion[k] for k in ("mechanism", "variants", "misconceptions", "discriminator", "adjacent", "stop"))


def test_gap_priority_keeps_current_criterion_despite_adjacent_topic(unified):
    from llm_interview_lab.knowledge import load_knowledge
    from llm_interview_lab.interview_expertise import retrieve
    from llm_interview_lab.interviewer_state import empty_state
    service, _ = unified
    knowledge = load_knowledge(service.repo_root, curriculum=service.catalog)
    role = service.roles.resolve_role("post_training_engineer")
    state = empty_state()
    answer = "总体标准差下组内优势约为负一和正一，全相同奖励优势零但KL梯度未必为零。"
    refs = retrieve(knowledge, role, state, answer, "GRPO组内优势怎样计算？")
    assert (refs[0]["topic_id"], refs[0]["criterion"]) == ("EGT-QB-028", "advantage")
    state["claims"]["claim-0001"] = {"topic_id": "EGT-QB-028", "criterion": "advantage"}
    state["gaps"]["claim-0001"] = {"status": "open"}
    assert retrieve(knowledge, role, state, answer, "GRPO组内优势怎样计算？")[0]["reason"] == "relevant_open_gap"
    state["gaps"]["claim-0001"]["status"] = "closed"
    refs = retrieve(knowledge, role, state, "GRPO更新的概率比是什么？", "GRPO组内优势怎样计算？")
    assert refs[0]["criterion"] == "ratio"
    assert not any(r["topic_id"] == "EGT-QB-028" and r["criterion"] == "advantage" for r in refs)
    refs = retrieve(knowledge, service.roles.resolve_role("ai_algorithm_research_engineer"), empty_state(),
        "GQA四个Query共享KV，所以它们的attention权重和输出必然完全相同。",
        "GQA里Hq=8、Hkv=2时如何共享？哪些成本改变？")
    assert any(r["topic_id"] == "EGT-QB-058" for r in refs)


def test_scene_sidecars_never_enter_compiler(unified):
    from scripts.evaluate_interviewer_expertise import compile_input
    data = json.loads((Path(__file__).parents[1] / "fixtures/interviewer-expertise-scenarios.json").read_text(encoding="utf-8"))
    assert len(data["cases"]) == 48
    assert len({(x["evaluation"]["topic_id"], x["evaluation"]["answer_type"]) for x in data["cases"]}) == 48
    service, profile = unified
    case = data["cases"][0]
    case["evaluation"]["accept_direction"] = "EVALUATOR_ONLY_SENTINEL"
    _, preview = compile_input(service, profile, case["input"])
    assert "EVALUATOR_ONLY_SENTINEL" not in preview.selected_text


def test_offline_response_artifact_replay_uses_production_transaction(unified, tmp_path):
    from scripts.evaluate_interviewer_expertise import compile_input, evaluate
    service, profile = unified
    case = json.loads((Path(__file__).parents[1] / "fixtures/interviewer-expertise-scenarios.json").read_text(encoding="utf-8"))["cases"][0]
    _, preview = compile_input(service, profile, case["input"])
    c = json.loads(next(p.content for p in preview.parts if p.id == "interview_contract"))
    scripted = packet(c, intro=False, criterion="contribution", claim_ref="claim-0001", experience_ref="")
    scripted["state_update"]["claims"][0]["evidence"]["quote"] = case["input"]["answer"][:100]
    responses = tmp_path / "scripted-responses"
    responses.mkdir()
    raw = json.dumps(scripted, ensure_ascii=False)
    (responses / "s001.txt").write_text(raw, encoding="utf-8")
    output = tmp_path / "evaluation"
    output.mkdir()
    # Runner reads only the requested synthetic response file. No inference.
    summary = evaluate(Path(__file__).parents[2], output, [case], responses=responses)
    assert summary["cases"][0]["replay_validation"] == "passed"
    assert summary["semantic_quality"] == "UNRUN" and summary["network_calls"] == 0
    assert (output / "s001.response.txt").read_text(encoding="utf-8") == raw
