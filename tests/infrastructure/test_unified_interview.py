"""New role/difficulty interviews keep historical seniority out of decisions."""
import hashlib
import json
from uuid import uuid4

import pytest

from llm_interview_lab.application import ApplicationService
from llm_interview_lab.role_interviews import dynamic_coding_candidates
from llm_interview_lab.workspace import init_profile
from tests.infrastructure.test_dynamic_interview_flow import public_repo


@pytest.fixture
def unified(public_repo):
    service = ApplicationService(public_repo)
    profile = "unified-" + uuid4().hex[:8]
    init_profile(public_repo, profile)
    return service, profile


def create(service, profile, **overrides):
    settings = dict(role_id="post_training_engineer", difficulty="hard", duration_minutes=60)
    settings.update(overrides)
    preview = service.dynamic_interview_context(profile, **settings)
    return service.create_dynamic_interview(
        profile, **settings, ai_mode="provider",
        initial_question={"kind": "oral", "title": "自我介绍", "prompt": "请介绍你亲自完成的一段经历。", "source_kind": "process_opening"},
        context_sha256=hashlib.sha256(preview.selected_text.encode()).hexdigest(),
    )


def test_new_session_has_no_seniority_and_preserves_duration(unified):
    service, profile = unified
    session = create(service, profile, duration_minutes=45)
    assert "seniority" not in session
    assert session["interaction_version"] == 2
    assert session["duration_minutes"] == 45
    assert session["blueprint_id"].endswith(".dynamic")
    service.start_interview(profile, session["interview_id"])
    assert service.current_interview(profile, session["interview_id"])["question"]["question_id"] == "q-001"


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
def test_legacy_classification_cannot_filter_new_questions(unified, difficulty):
    service, profile = unified
    session = create(service, profile, difficulty=difficulty)
    def candidates(value):
        return [p.id for p, _ in dynamic_coding_candidates(service.catalog, service.roles, value)]
    expected = candidates(session)
    assert expected
    for legacy in ("intern", "new_grad", "mid"):
        assert candidates({**session, "seniority": legacy}) == expected
    levels = [p.raw["difficulty"]["coding"] for p, _ in dynamic_coding_candidates(service.catalog, service.roles, session)]
    assert set(levels) <= {"easy": {1, 2}, "medium": {2, 3, 4}, "hard": {3, 4, 5}}[difficulty]
    if difficulty == "hard":
        assert levels == sorted(levels, reverse=True)


def test_start_prompt_is_independent_of_legacy_argument(unified):
    service, profile = unified
    prompts = [service.dynamic_interview_context(profile, role_id="post_training_engineer", seniority=value,
               difficulty="hard").selected_text for value in (None, "intern", "new_grad", "mid")]
    assert len(set(prompts)) == 1
    assert '"seniority"' not in prompts[0]
    assert '"target_level"' not in prompts[0]


def test_local_script_accepts_input_and_does_not_claim_test_pass(tmp_path):
    from llm_interview_lab.script_runner import run_local_python
    script = tmp_path / "submission.py"
    script.write_text("values = list(map(int, input().split()))\nprint(sum(values))\n", encoding="utf-8")
    result = run_local_python(script, "1 2 3\n", repo_root=tmp_path)
    assert result["stdout"] == "6\n" and result["exit_code"] == 0
    assert result["status"] == "finished"
    assert "passed" not in result


def test_practice_save_failure_never_starts_script(unified, monkeypatch):
    service, profile = unified
    calls = []
    def reject(*args, **kwargs):
        raise OSError("synthetic disk failure")
    monkeypatch.setattr(service, "save_practice_submission", reject)
    monkeypatch.setattr("llm_interview_lab.script_runner.run_local_python", lambda *a, **kw: calls.append(kw))
    with pytest.raises(OSError):
        service.run_practice_script(profile, "FND-001", "print('latest')")
    assert not calls
