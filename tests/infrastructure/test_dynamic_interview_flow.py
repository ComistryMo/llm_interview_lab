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
from llm_interview_lab.interview_flow import DIFFICULTY_DIRECTIVES, ROLE_PROBE_FOCUS, next_stages, flow_coverage
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


def test_conversation_strategy_and_selected_role_reach_each_turn(interview):
    service, profile, iid, _ = interview
    assert set(ROLE_PROBE_FOCUS) == set(service.roles.roles)
    for role_id in service.roles.roles:
        for difficulty in ("easy", "medium", "hard"):
            preview = service.dynamic_interview_context(profile, role_id=role_id, seniority="intern", difficulty=difficulty)
            contract = json.loads(next(p.content for p in preview.parts if p.id == "interview_contract"))
            assert contract["role_probe_focus"] == ROLE_PROBE_FOCUS[role_id]
            assert contract["difficulty_directive"] == DIFFICULTY_DIRECTIVES[difficulty]
            assert "从自我介绍进入经历" in contract["conversation_strategy"]
            assert "不是我负责" in contract["conversation_strategy"]
            assert "不要把答案塞进问题" in contract["conversation_strategy"]
            assert "级别决定责任范围" in contract["conversation_strategy"]
            assert "改变一个约束" in contract["conversation_strategy"]
            assert "温和指出两处实际表述" in contract["conversation_strategy"]
            assert "未来问题" not in contract
    advance(service, profile, iid, "experience")
    lock(service, profile, iid, "我记不清 beta，这不是我负责的部分。我只做过偏好数据去重。")
    followup = context(service, profile, iid)
    parts = {p.id: p.content for p in followup.parts}
    assert "只做过偏好数据去重" in parts["candidate_answer"]
    assert "答不上来与换角度" in parts["policy"]
    assert "不知道或非本人负责时换一个实际接触过的角度" in parts["interview_contract"]
    assert "chosen" not in parts["dialogue_history"]  # No invented candidate facts.


@pytest.mark.parametrize(("role_id", "expected"), [
    ("post_training_engineer", {"OPT-003", "LOSS-002", "PT-019"}),
    ("ai_algorithm_research_engineer", {"LOSS-002", "ATT-003"}),
])
def test_new_handwriting_is_reachable_as_real_interview_candidates(interview, role_id, expected):
    service, profile, iid, _ = interview
    session = service.interview_session(profile, iid)
    session = {**session, "role_id": role_id, "seniority": "mid"}
    candidates = {p.id for p, _ in dynamic_coding_candidates(service.catalog, service.roles, session)}
    assert expected.issubset(candidates)


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


@pytest.mark.parametrize("suggestion", ["NOT-A-LOCAL-PROBLEM", ""])
def test_unknown_coding_suggestion_enters_real_local_task(interview, suggestion):
    service, profile, iid, _ = interview
    for stage in (["experience"] * 8 + ["theory"] * 4):
        advance(service, profile, iid, stage)
    candidates = dynamic_coding_candidates(service.catalog, service.roles, service.interview_session(profile, iid))
    after = advance(service, profile, iid, "coding", suggestion)
    question = after["questions"][-1]
    assert question["source"]["id"] in {p.id for p, _ in candidates}
    problem = service.catalog.problems[question["source"]["id"]]
    assert question["prompt"] == (problem.problem_dir / "task.md").read_text(encoding="utf-8")
    assert service.current_interview_coding_submission(profile, iid)["text"] == (problem.problem_dir / "starter.py").read_text(encoding="utf-8")
    assert after["timeline"][-1]["coding_selection_corrected"] is True
    assert service.interview_state(profile, iid)["coding_selection_corrected"] is True
    assert len(after["assessments"]) == 13


def test_valid_coding_suggestion_is_preserved(interview):
    service, profile, iid, _ = interview
    for stage in (["experience"] * 8 + ["theory"] * 4):
        advance(service, profile, iid, stage)
    candidates = dynamic_coding_candidates(service.catalog, service.roles, service.interview_session(profile, iid))
    chosen = candidates[-1][0].id
    after = advance(service, profile, iid, "coding", chosen)
    assert after["questions"][-1]["source"]["id"] == chosen
    assert not after["timeline"][-1].get("coding_selection_corrected")


def test_dynamic_candidates_require_actual_runtime_assets(interview, tmp_path, monkeypatch):
    from dataclasses import replace

    service, profile, iid, _ = interview
    session = service.interview_session(profile, iid)
    before = dynamic_coding_candidates(service.catalog, service.roles, session)
    missing = before[0][0]
    monkeypatch.setitem(service.catalog.problems, missing.id, replace(missing, problem_dir=tmp_path / "missing-assets"))
    after = dynamic_coding_candidates(service.catalog, service.roles, session)
    assert missing.id not in {p.id for p, _ in after}
    assert {p.id for p, _ in after} == {p.id for p, _ in before[1:]}


def test_no_local_coding_assets_finishes_with_explicit_gap(interview, monkeypatch):
    service, profile, iid, _ = interview
    for stage in (["experience"] * 8 + ["theory"] * 4):
        advance(service, profile, iid, stage)
    monkeypatch.setattr("llm_interview_lab.role_interviews.dynamic_coding_candidates", lambda *args: ())
    session = advance(service, profile, iid, "coding", "AI-INVENTED-404")
    assert len(session["questions"]) == 13
    assert service.current_interview(profile, iid)["question"] is None
    assert "coding" in flow_coverage(session)["missing_stages"]
    final = service.finish_interview(profile, iid, confirm_incomplete=True)
    assert final["status"] == "incomplete"
    assert not final["coding_evidence"]


def test_full_flow_reaches_real_coding_and_evidence_report(interview):
    service, profile, iid, _ = interview
    for stage in (["experience"] * 8 + ["theory"] * 4):
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
    service.score_interview(profile, iid, question["question_id"], {name: 1 for name in question["rubric"]["dimensions"]}, evidence="Local Grader", source="grader", confidence="high")
    after = service.interview_session(profile, iid)
    assert flow_coverage(after)["complete"]
    # New service instance proves progression isn't held only in Controller.
    service = ApplicationService(service.repo_root)
    final = service.finish_interview(profile, iid)
    assert final["status"] == "completed"
    assert 0 <= final["result"]["overall_score"] <= 100
    assert final["assessments"][question["question_id"]]["source"] == "grader"
    assert all(a["answer_sha256"] for key, a in final["assessments"].items() if key != question["question_id"])


def test_stage_minimums_prevent_skipping_theory_without_capping_deep_followups():
    session = {"difficulty": "hard", "questions": [{"question_id": "q-001", "kind": "oral", "stage": "introduction"}]}
    assert next_stages(session, coding_available=True) == ["experience"]
    for index in range(8):
        session["questions"].append({"question_id": f"q-{index+2:03d}", "kind": "oral", "stage": "experience"})
    assert next_stages(session, coding_available=True) == ["experience", "theory"]
    session["questions"].extend([dict(session["questions"][-1]) for _ in range(20)])
    assert next_stages(session, coding_available=True) == ["experience", "theory"]
    for index in range(3):
        session["questions"].append({"question_id": f"q-{index+6:03d}", "kind": "oral", "stage": "theory"})
    assert next_stages(session, coding_available=True) == ["theory"]
    session["questions"].append({"question_id": "q-050", "kind": "oral", "stage": "theory"})
    assert next_stages(session, coding_available=False) == ["theory", "finish"]
    assert next_stages(session, coding_available=True) == ["theory", "coding"]


def test_self_written_scripts_stdin_errors_timeout_and_revision_bound_review(interview):
    from llm_interview_lab.role_interviews import run_role_coding_script
    from llm_interview_lab.application import ApplicationError

    service, profile, iid, _ = interview
    for stage in ["experience"] * 8 + ["theory"] * 4 + ["coding"]:
        advance(service, profile, iid, stage)
    code = "def total(xs):\n    return sum(xs)\nprint('结果', total([1, 2, 3]))\nprint(input().upper())\n"
    saved = service.save_interview_coding_submission(profile, iid, code)
    run = service.run_interview_code(profile, iid, "hello\n")
    assert run["exit_code"] == 0 and run["stdout"] == "结果 6\nHELLO\n"
    assert run["submission_sha256"] == saved["sha256"]
    assert not service.interview_session(profile, iid)["coding_evidence"]
    assert not service.interview_session(profile, iid)["assessments"].get(saved["question_id"])

    service.save_interview_coding_submission(profile, iid, "def unfinished(:\n")
    failed = service.run_interview_code(profile, iid)
    assert failed["exit_code"] != 0 and "SyntaxError" in failed["stderr"]
    service.save_interview_coding_submission(profile, iid, "import time\nprint('before timeout', flush=True)\ntime.sleep(60)\n")
    timed = run_role_coding_script(service.repo_root, profile, iid, timeout=0.4)
    assert timed["status"] == "timed_out" and timed["exit_code"] is None and "before timeout" in timed["stdout"]
    service.save_interview_coding_submission(profile, iid, "while True:\n    print('x' * 4096)\n")
    limited = service.run_interview_code(profile, iid)
    assert limited["status"] == "output_limited" and limited["exit_code"] is None
    assert len(limited["stdout"]) < 8100 and "64 KB" in limited["stderr"]

    # A new revision must not inherit a successful or failed run from old code.
    saved = service.save_interview_coding_submission(profile, iid, "def total(xs):\n    # 核心是逐个累加，尚未补空列表处理\n    return sum(xs)\n")
    service.lock_interview_code(profile, iid)
    snapshot = json.loads(service.interview_answer_text(profile, iid, saved["question_id"]))
    assert snapshot["self_run"] == {"status": "not_run"}
    assert snapshot["public_tests"] == {"status": "not_run"}
    assert snapshot["submission_sha256"] == saved["sha256"]
    for action in (lambda: service.save_interview_coding_submission(profile, iid, "changed"),
                   lambda: service.run_interview_code(profile, iid),
                   lambda: service.test_interview_coding(profile, iid)):
        with pytest.raises((ApplicationError, RoleInterviewError), match="锁定"):
            action()

    preview = context(service, profile, iid)
    assert "不等于核心逻辑全错" in preview.selected_text
    assert "remaining_seconds_at_turn_start" in preview.selected_text
    rating = reply(service, profile, iid, "finish")
    rating["scores"] = {"core_logic": 4, "reasoning": 3, "validation": 1}
    rating["evidence"] = "候选人的 return sum(xs) 已体现逐项求和核心关系；注释承认边界说明未补。本版本没有执行证据，不推断测试通过。"
    service.advance_dynamic_interview(profile, iid, saved["question_id"], rating, context_sha256="f" * 64)
    final = service.finish_interview(profile, iid)
    assert final["status"] == "completed"
    assert final["assessments"][saved["question_id"]]["source"] == "ai"
    assert not final["coding_evidence"]
    view = service.interview_result_view(profile, iid)
    assert "本地执行：未运行" in view["assessment_evidence"][-1]["coding_execution_summary"]
    assert view["assessment_evidence"][-1]["score"] > 40


def test_failed_script_can_receive_partial_logic_credit_without_fabricating_pass(interview):
    service, profile, iid, _ = interview
    for stage in ["experience"] * 8 + ["theory"] * 4 + ["coding"]:
        advance(service, profile, iid, stage)
    code = "def f(xs):\n    return sum(xs)\n# 示例调用参数遗漏，核心求和关系已写出\nprint(f())\n"
    service.save_interview_coding_submission(profile, iid, code)
    run = service.run_interview_code(profile, iid)
    assert run["exit_code"] != 0
    locked = service.lock_interview_code(profile, iid)
    qid = locked["questions"][-1]["question_id"]
    snapshot = json.loads(service.interview_answer_text(profile, iid, qid))
    assert snapshot["self_run"]["exit_code"] == run["exit_code"]
    rating = reply(service, profile, iid, "finish")
    rating["scores"] = {"core_logic": 3, "reasoning": 2, "validation": 1}
    rating["evidence"] = "sum(xs) 核心累加关系合理，但 f() 调用缺少参数且本地 TypeError；未实现题面全部要求，不推断正确性或测试通过。"
    service.advance_dynamic_interview(profile, iid, qid, rating, context_sha256="e" * 64)
    final = service.finish_interview(profile, iid)
    assert final["assessments"][qid]["scores"]["core_logic"] == 3
    assert final["coding_evidence"] == {}
    assert "退出码 1" in service.interview_result_view(profile, iid)["assessment_evidence"][-1]["coding_execution_summary"]


@pytest.mark.parametrize("difficulty,experience,theory", [("easy", 4, 3), ("medium", 6, 3), ("hard", 8, 4)])
def test_difficulty_changes_coverage_not_score_leniency(difficulty, experience, theory):
    from llm_interview_lab.interview_flow import stage_minimums
    assert stage_minimums({"difficulty": difficulty}) == {"introduction": 1, "experience": experience, "theory": theory, "coding": 1}
    text = (REPO / "coach/prompts/dynamic-interviewer.md").read_text(encoding="utf-8")
    assert "三至四个不同" in text or "3–4" in text or "3–4" in DIFFICULTY_DIRECTIVES[difficulty] or "四个不同" in text
    assert "横向换重点" in text and "CoT" in text and "GRPO" in text


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
