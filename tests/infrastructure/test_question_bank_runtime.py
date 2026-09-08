"""Real knowledge practice and dynamic candidate delivery, with synthetic Profiles."""
from __future__ import annotations

import json
from uuid import uuid4

import pytest

from llm_interview_lab.application import ApplicationService
from llm_interview_lab.ai.context_builder import build_role_interview_context_preview
from llm_interview_lab.workspace import init_profile, profile_paths
from .test_interview_input_runtime import (
    QCoreApplication, QPointF, QTest, Qt, _capture, _click, _find, _visible_hints,
)
from .test_interview_input_runtime import public_repo as public_repo
from .test_interview_input_runtime import controller as controller
from .test_interview_input_runtime import qapp as qapp
from .test_interview_input_runtime import scene as scene
from .test_dynamic_interview_flow import interview as interview
from .test_dynamic_interview_flow import advance, lock, reply


pytestmark = pytest.mark.infrastructure


def test_local_knowledge_answer_survives_reload_without_events(public_repo):
    service = ApplicationService(public_repo)
    first, second = "oral-" + uuid4().hex[:8], "oral-" + uuid4().hex[:8]
    for profile in (first, second):
        init_profile(public_repo, profile)
    card = service.knowledge_cards(kind="eight_stock")[0]["id"]
    events = profile_paths(public_repo, first).events_file.read_bytes()
    assert service.knowledge_answer(first, card) == ""
    service.save_knowledge_answer(first, card, "我的独立回答：先解释机制，再给一个边界例子。")
    restored = ApplicationService(public_repo)
    assert "独立回答" in restored.knowledge_answer(first, card)
    assert restored.knowledge_answer(second, card) == ""
    assert profile_paths(public_repo, first).events_file.read_bytes() == events


def test_knowledge_picker_does_not_truncate_at_two_hundred(controller):
    assert controller.loadKnowledge()
    assert len(controller.knowledgeCards) == len(controller.service.knowledge.cards)
    card = controller.knowledgeCards[-1]["id"]
    assert controller.openKnowledgeCard(card)
    assert not controller.saveKnowledgeAnswer("a-different-profile", card, "串档文本")
    assert controller.knowledgeDetail["draft_answer"] == ""
    assert controller.saveKnowledgeAnswer(controller.profileId, card, "本档案回答")
    assert controller.searchKnowledge(card)
    assert any(c["id"] == card for c in controller.knowledgeCards)


def test_switch_profile_clears_private_knowledge_answer(scene):
    window, controller = scene
    controller.navigate("learn")
    _click(window, _find(window, "knowledgeBrowserButton"))
    card = next(c["id"] for c in controller.knowledgeCards if c["kind"] == "eight_stock")
    first = controller.profileId
    second = "oral-switch-" + uuid4().hex[:8]
    init_profile(controller.repo_root, second)
    marker = "SYNTHETIC FIRST PROFILE ANSWER"
    controller.service.save_knowledge_answer(first, card, marker)
    assert controller.openKnowledgeCard(card)
    QCoreApplication.processEvents()
    editor = _find(window, "knowledgePracticeAnswer")
    assert editor.property("text") == marker
    assert controller.switchProfile(second), controller.profileSwitchError
    QCoreApplication.processEvents()
    assert controller.knowledgeDetail == {}
    assert editor.property("text") == ""
    assert not controller.saveKnowledgeAnswer(first, card, marker)
    assert not controller.saveKnowledgeAnswer(second, card, marker)
    assert controller.openKnowledgeCard(card)
    QCoreApplication.processEvents()
    assert editor.property("text") == ""
    assert controller.knowledgeDetail["profile_id"] == second
    assert controller.service.knowledge_answer(second, card) == ""
    assert controller.switchProfile(first)
    assert controller.openKnowledgeCard(card)
    QCoreApplication.processEvents()
    assert editor.property("text") == marker


@pytest.mark.parametrize("size,theme,scale", [
    ((900, 620), "dark", 1.25), ((1080, 680), "light", 1.0),
    ((1280, 800), "dark", 1.0), ((1440, 900), "light", 1.0),
])
def test_knowledge_real_typing_reveal_scroll_and_saved_answer(scene, size, theme, scale):
    window, controller = scene
    controller.setTheme(theme)
    window.resize(*size)
    window.setProperty("displayFontScaleOverride", scale)
    controller.navigate("learn")
    QTest.qWait(80)
    _click(window, _find(window, "knowledgeBrowserButton"))
    assert controller.knowledgeLoaded
    card = next(c for c in controller.knowledgeCards if c["kind"] == "eight_stock")
    assert controller.openKnowledgeCard(card["id"])
    page = _find(window, "learnPage")
    page.setProperty("compactKnowledgeDetail", True)
    QTest.qWait(60)
    editor = _find(window, "knowledgePracticeAnswer")
    core = _find(window, "knowledgeCoreAnswer")
    assert editor.isVisible() and not core.isVisible()
    editor.forceActiveFocus()
    for character in "gradient = prediction - target":
        QTest.keyClick(window, Qt.Key(ord(character.upper())))
    assert editor.property("text") == "gradient = prediction - target"
    assert not _visible_hints(editor)
    viewport = _find(window, "knowledgeDetailScroll").property("contentItem")
    reveal = _find(window, "knowledgeRevealAnswer")
    y = reveal.mapToItem(viewport, QPointF()).y()
    viewport.setProperty("contentY", max(0, viewport.property("contentY") + y - viewport.height() + reveal.height() + 24))
    QTest.qWait(60)
    _click(window, reveal)
    assert core.isVisible()
    assert controller.service.knowledge_answer(controller.profileId, card["id"]) == editor.property("text")
    assert _find(window, "knowledgeDetailContent").height() > viewport.height()
    content = _find(window, "knowledgeDetailContent")
    visible_children = sorted((c for c in content.childItems() if c.isVisible() and c.height() > 0), key=lambda c: c.y())
    for before, after in zip(visible_children, visible_children[1:]):
        assert before.y() + before.height() <= after.y() + 1
    for item in visible_children:
        assert item.x() >= -1 and item.x() + item.width() <= content.width() + 1
    viewport.setProperty("contentY", 0)
    _capture(window, f"question-bank-{size[0]}-{theme}")
    other = next(c for c in controller.knowledgeCards if c["id"] != card["id"])
    assert controller.openKnowledgeCard(other["id"])
    QCoreApplication.processEvents()
    assert editor.property("text") == "" and not core.isVisible()
    assert controller.openKnowledgeCard(card["id"])
    QCoreApplication.processEvents()
    assert editor.property("text") == "gradient = prediction - target"


def test_actual_dynamic_context_selects_then_materializes_one_bank_question(interview):
    service, profile, iid, _ = interview
    for _ in range(8):
        advance(service, profile, iid, "experience")
    advance(service, profile, iid, "theory")
    lock(service, profile, iid, "我实际做了 GRPO，组内 reward 全相同时归一化优势为零。")
    before = service.interview_session(profile, iid)
    preview = build_role_interview_context_preview(
        service.repo_root, profile, iid, candidate_answer=service.interview_answer_text(profile, iid, before["questions"][-1]["question_id"]),
        include_materials=True, catalog=service.catalog, role_catalog=service.roles,
        knowledge=service.knowledge_catalog(),
    )
    pool = json.loads(next(p.content for p in preview.parts if p.id == "knowledge_candidates"))
    assert 0 < len(pool["cards"]) <= 8
    assert any("GRPO" in c["title"].upper() + c["prompt"].upper() for c in pool["cards"])
    assert all("core_answer" not in c and "acceptance" not in c for c in pool["cards"])
    assert "knowledge_candidates" not in before  # A candidate pool is not a session plan.
    chosen = pool["cards"][0]
    response = reply(service, profile, iid, "theory")
    response["follow_up"] = chosen["prompt"]
    response["next_skill_ids"] = chosen["skills"][:3]
    after = service.advance_dynamic_interview(profile, iid, before["questions"][-1]["question_id"], response, context_sha256="a" * 64)
    assert len(after["questions"]) == len(before["questions"]) + 1
    assert after["questions"][-1]["prompt"] == chosen["prompt"]
    assert after["questions"][-1]["skills"] == chosen["skills"][:3]


def test_knowledge_related_mla_button_opens_real_coding_workspace(scene):
    window, controller = scene
    controller.navigate("learn")
    _click(window, _find(window, "knowledgeBrowserButton"))
    assert controller.openKnowledgeCard("EGT-QB-059")
    _find(window, "learnPage").setProperty("compactKnowledgeDetail", True)
    QTest.qWait(60)
    # Onboarding already started another real task: explain the single-active-
    # practice rule instead of presenting a button that will only fail.
    assert not _find(window, "knowledgeProblem-ATT-023").isEnabled()
    card = next(p for p in controller.problems if p["problem_id"] == "ATT-023")
    assert "完成当前练习" in card["start_blocked_reason"]
    fresh = "oral-coding-" + uuid4().hex[:8]
    init_profile(controller.repo_root, fresh, track_ids=("llm_algorithm",))
    assert controller.switchProfile(fresh)
    controller.navigate("learn")
    assert controller.openKnowledgeCard("EGT-QB-059")
    _find(window, "learnPage").setProperty("compactKnowledgeDetail", True)
    QTest.qWait(60)
    editor = _find(window, "knowledgePracticeAnswer")
    editor.setProperty("text", "先解释压缩缓存与解耦位置分量，再实现代码。")
    viewport = _find(window, "knowledgeDetailScroll").property("contentItem")
    button = _find(window, "knowledgeProblem-ATT-023")
    if not controller.service._problem_environment_available(controller.service.catalog.get("ATT-023")):
        assert not button.isEnabled()
        problem = next(p for p in controller.problems if p["problem_id"] == "ATT-023")
        assert "PyTorch" in problem["environment"]
        assert not controller.openProblem("ATT-023")
        assert not controller.currentTask.get("problem_id")
        return
    assert button.isEnabled()
    y = button.mapToItem(viewport, QPointF()).y()
    viewport.setProperty("contentY", max(0, viewport.property("contentY") + y - viewport.height() + button.height() + 24))
    QTest.qWait(60)
    _capture(window, "knowledge-related-before")
    _click(window, button)
    assert controller.lastActionResult["success"], controller.lastActionResult.get("technical_message")
    assert controller.currentTask["problem_id"] == "ATT-023"
    assert _find(window, "practiceOutputHeading").property("text") == "执行输出"
    assert "def mla_attention" in controller.submissionText
    assert "NotImplementedError" in controller.submissionText
    assert controller.service.knowledge_answer(controller.profileId, "EGT-QB-059").startswith("先解释")


def test_missing_practice_dependency_blocks_new_task_but_preserves_existing(controller, monkeypatch):
    current = controller.service.current_submission(controller.profileId)
    assert current
    events = profile_paths(controller.repo_root, controller.profileId).events_file
    before = events.read_bytes()
    available = controller.service._problem_environment_available
    monkeypatch.setattr(controller.service, "_problem_environment_available",
                        lambda problem: False if problem.raw.get("interface", {}).get("framework") == "pytorch"
                        else available(problem))
    # Restoring saved work remains possible after an environment change.
    assert controller.openProblem(current["problem_id"]), controller.lastActionResult
    assert controller.submissionText == current["text"]
    assert events.read_bytes() == before

    fresh = "missing-dependency-" + uuid4().hex[:8]
    init_profile(controller.repo_root, fresh, track_ids=("llm_algorithm",))
    assert controller.switchProfile(fresh)
    events = profile_paths(controller.repo_root, fresh).events_file
    before = events.read_bytes()
    assert not controller.openProblem("ATT-023")
    assert controller.lastActionResult["error_code"] == "PRACTICE_DEPENDENCY_MISSING"
    assert "PyTorch" in controller.lastActionResult["user_message"]
    assert controller.lastActionResult["recommended_action"]
    assert controller.service.current_submission(fresh) is None
    assert events.read_bytes() == before
