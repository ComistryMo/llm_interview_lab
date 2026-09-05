"""One-question-at-a-time flow, authorized background and real local grading."""
import hashlib
import asyncio
import json
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

import pytest

from llm_interview_lab.application import ApplicationService
from llm_interview_lab.ai.context_builder import build_role_interview_context_preview, ContextBuilderError
from llm_interview_lab.interview_flow import next_stages, flow_coverage
from llm_interview_lab.materials import add_material, set_material_ai_access
from llm_interview_lab.role_interviews import dynamic_coding_candidates, RoleInterviewError
from llm_interview_lab.workspace import init_profile

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def public_repo(tmp_path_factory):
    root = tmp_path_factory.mktemp("dynamic-flow")
    for name in (".gitignore", "pyproject.toml"):
        shutil.copy2(REPO / name, root / name)
    for name in ("curriculum", "coach", "workspace/schema", "workspace/templates"):
        shutil.copytree(REPO / name, root / name)
    (root / "workspace/profiles").mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return root


@pytest.fixture
def interview(public_repo, tmp_path):
    service = ApplicationService(public_repo)
    profile = "flow-" + uuid4().hex[:8]
    init_profile(public_repo, profile)
    refs = []
    for kind, body in (("resume", "合成候选人林青。星舟竞赛负责 DPO 偏好对去重，按用户隔离训练和评测。没有论文。"),
                       ("job_description", "合成 JD：后训练实习，重点评估偏好数据、DPO reference/beta、评测泄漏和稳定损失。")):
        path = tmp_path / f"{kind}.txt"
        path.write_text(body, encoding="utf-8")
        refs.append(add_material(public_repo, profile, path, kind=kind, ai_access=True).id)
    preview = service.dynamic_interview_context(profile, role_id="post_training_engineer", seniority="intern", difficulty="hard", material_ids=refs, consent_materials=True)
    session = service.create_dynamic_interview(profile, role_id="post_training_engineer", seniority="intern", difficulty="hard", ai_mode="codex",
        initial_question={"kind": "oral", "title": "自我介绍", "prompt": "请先介绍你本人在后训练项目中完成的工作。", "source_kind": "process_opening"},
        context_sha256=hashlib.sha256(preview.selected_text.encode()).hexdigest(), material_ids=refs, consent_materials=True)
    service.start_interview(profile, session["interview_id"])
    return service, profile, session["interview_id"], refs


def context(service, profile, interview_id, include_materials=True):
    session = service.interview_session(profile, interview_id)
    q = session["questions"][-1]
    return build_role_interview_context_preview(service.repo_root, profile, interview_id,
        candidate_answer=service.interview_answer_text(profile, interview_id, q["question_id"]), include_materials=include_materials,
        catalog=service.catalog, role_catalog=service.roles)


def reply(service, profile, interview_id, stage, coding_id=""):
    q = service.current_interview(profile, interview_id)["question"]
    return {"scores": {d: 3 for d in q["rubric"]["dimensions"]},
            "evidence": "候选人说明了按用户隔离的评测方法，仍需核实去重和评测数据的具体边界。",
            "confidence": "medium", "fatal_issues": [], "next_stage": stage,
            "follow_up": "对于你提到的按用户隔离，如何排除跨集合的重复偏好对？" if stage not in {"coding", "finish"} else "",
            "coding_problem_id": coding_id,
            "next_skill_ids": [next(iter(service.roles.roles["post_training_engineer"].skill_weights))] if stage not in {"coding", "finish"} else []}


def lock(service, profile, interview_id, answer="我在星舟竞赛负责按用户隔离并对偏好对去重，没有参与论文。"):
    q = service.current_interview(profile, interview_id)["question"]
    service.answer_interview(profile, interview_id, q["question_id"], answer)
    return q["question_id"]


def advance(service, profile, interview_id, stage, coding_id=""):
    qid = lock(service, profile, interview_id)
    preview = context(service, profile, interview_id)
    return service.advance_dynamic_interview(profile, interview_id, qid, reply(service, profile, interview_id, stage, coding_id),
        context_sha256=hashlib.sha256(preview.selected_text.encode()).hexdigest())


def test_context_keeps_resume_jd_and_prior_answers_not_future_questions(interview):
    service, profile, iid, _ = interview
    assert len(service.interview_session(profile, iid)["questions"]) == 1
    advance(service, profile, iid, "experience")
    lock(service, profile, iid, "第二轮：我还按时间切分，独立留出用户评测。")
    preview = context(service, profile, iid)
    parts = {p.id: p.content for p in preview.parts}
    assert "星舟竞赛" in preview.selected_text and "合成 JD" in preview.selected_text
    assert "星舟竞赛" in parts["dialogue_history"] and "q-001" in parts["dialogue_history"]
    assert "第二轮" in parts["candidate_answer"]
    assert "q-003" not in preview.selected_text
    contract = json.loads(parts["interview_contract"])
    assert contract["role_skills"][0]["description"]
    assert contract["difficulty_directive"] and contract["seniority"] == "intern"
    assert contract["allowed_next_stages"] == ["experience"]
    assert contract["coding_candidates"]
    assert "合成 JD" not in context(service, profile, iid, False).selected_text


def test_revoked_material_blocks_send_not_answer_recovery(interview):
    service, profile, iid, refs = interview
    lock(service, profile, iid)
    set_material_ai_access(service.repo_root, profile, refs[0], False)
    with pytest.raises(ContextBuilderError, match="stale|revoked"):
        context(service, profile, iid)
    assert service.interview_answer_text(profile, iid, "q-001")


def test_invalid_ai_stage_does_not_commit_score_or_extra_question(interview):
    service, profile, iid, _ = interview
    qid = lock(service, profile, iid)
    with pytest.raises(RoleInterviewError, match="阶段"):
        service.advance_dynamic_interview(profile, iid, qid, reply(service, profile, iid, "coding"), context_sha256="a" * 64)
    session = service.interview_session(profile, iid)
    assert session["answers"] and not session["assessments"] and len(session["questions"]) == 1


def test_full_flow_reaches_real_coding_and_evidence_report(interview):
    service, profile, iid, _ = interview
    for stage in ("experience", "experience", "theory", "theory"):
        before = service.interview_session(profile, iid)
        after = advance(service, profile, iid, stage)
        assert len(after["questions"]) == len(before["questions"]) + 1
    candidates = dynamic_coding_candidates(service.catalog, service.roles, after)
    assert candidates
    after = advance(service, profile, iid, "coding", candidates[0][0].id)
    assert after["questions"][-1]["source"]["kind"] == "catalog_problem"
    submission = service.current_interview_coding_submission(profile, iid)
    assert submission["text"]
    # Intentionally unimplemented starter: real failure evidence, not fake PASS.
    result = service.test_interview_coding(profile, iid)
    assert result.submission_sha256 == submission["sha256"]
    assert result.status == "failed"
    question = after["questions"][-1]
    service.score_interview(profile, iid, question["question_id"], {name: 1 for name in question["rubric"]["dimensions"]}, evidence="Local Grader", source="grader", confidence="high", fatal_issues=("does_not_run",))
    after = service.interview_session(profile, iid)
    assert flow_coverage(after)["complete"]
    # New service instance proves progression isn't held only in Controller.
    service = ApplicationService(service.repo_root)
    final = service.finish_interview(profile, iid)
    assert final["status"] == "completed"
    assert 0 <= final["result"]["overall_score"] <= 100
    assert final["assessments"][question["question_id"]]["source"] == "grader"
    assert all(a["answer_sha256"] for key, a in final["assessments"].items() if key != question["question_id"])


def test_stage_bounds_prevent_endless_project_questions_and_early_coding():
    session = {"questions": [{"question_id": "q-001", "kind": "oral", "stage": "introduction"}]}
    assert next_stages(session, coding_available=True) == ["experience"]
    for index in range(4):
        session["questions"].append({"question_id": f"q-{index+2:03d}", "kind": "oral", "stage": "experience"})
    assert next_stages(session, coding_available=True) == ["theory"]
    for index in range(2):
        session["questions"].append({"question_id": f"q-{index+6:03d}", "kind": "oral", "stage": "theory"})
    assert next_stages(session, coding_available=False) == ["theory", "finish"]


@pytest.mark.parametrize("provider_id", ["openai", "openai-compatible", "ollama"])
def test_api_wire_sends_selected_model_effort_and_complete_context(interview, provider_id):
    import httpx
    from llm_interview_lab.ai.providers import ProviderConfig, OpenAICompatibleChatProvider
    service, profile, iid, _ = interview
    advance(service, profile, iid, "experience")
    lock(service, profile, iid)
    preview = context(service, profile, iid)
    payloads = []

    def respond(request):
        payloads.append(json.loads(request.content))
        answer = json.dumps(reply(service, profile, iid, "experience"), ensure_ascii=False)
        event = {"choices": [{"delta": {"content": answer}}]}
        return httpx.Response(200, text="data: " + json.dumps(event) + "\n\ndata: [DONE]\n\n", headers={"content-type": "text/event-stream"})

    config = ProviderConfig("test", provider_id, "selected-model", "Synthetic API", base_url="https://model.invalid/v1", reasoning_effort="low")
    provider = OpenAICompatibleChatProvider(config, api_key=None, client_factory=lambda **kw: httpx.AsyncClient(**kw, transport=httpx.MockTransport(respond)))

    async def run():
        return [event async for event in provider.stream_chat([{"role": "system", "content": preview.selected_text}])]

    events = asyncio.run(run())
    assert any(event.text for event in events)
    assert payloads[0]["model"] == "selected-model" and payloads[0]["reasoning_effort"] == "low"
    sent = payloads[0]["messages"][0]["content"]
    assert "星舟竞赛" in sent and "合成 JD" in sent and "q-001" in sent
