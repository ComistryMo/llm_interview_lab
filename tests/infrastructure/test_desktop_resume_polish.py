"""Real desktop routes; isolated Profiles, fake network probes, no paid AI calls."""
import asyncio
import re
from pathlib import Path

import pytest
from tests.infrastructure.test_interview_input_runtime import (
    qapp, public_repo, controller, scene, _find, _click, _capture, _within_window,
    _wait_for_asr, _visible_hints,
)

from PySide6.QtCore import QObject, QPointF, QMetaObject, Qt
from PySide6.QtGui import QInputMethodEvent
from PySide6.QtTest import QTest

from llm_interview_lab.ai.base import ConnectionResult
from llm_interview_lab.desktop.controller import AppController
from llm_interview_lab.desktop.coding_statements_zh import CONTRACTS, chinese_statement


def test_sidebar_and_interview_use_desktop_space_without_losing_input(scene, qapp):
    window, controller = scene
    controller.navigate("interview")
    editor = _find(window, "interviewAnswerEditor")
    for width, height in ((900, 620), (1080, 680), (1280, 800), (1440, 900), (2560, 1411)):
        window.resize(width, height)
        for scale, theme in ((1.0, "dark"), (1.25, "light")):
            controller.setTheme(theme)
            window.setProperty("displayFontScaleOverride", scale)
            QTest.qWait(70)
            toggle = _find(window, "toggleSidebar")
            assert _within_window(window, toggle)
            for collapsed in (False, True):
                if bool(window.property("compactShell")) != collapsed:
                    _click(window, toggle)
                QTest.qWait(40)
                assert window.property("sidebarWidth") == (64 if collapsed else 220)
                assert not window.findChild(QObject, "sidebarProfileSwitcher")
                assert _find(window, "profileSwitcher")  # Still available in Settings.
                assert editor is _find(window, "interviewAnswerEditor")
                assert _within_window(window, editor)
                assert _within_window(window, _find(window, "lockInterviewAnswer"))
                if width == 2560:
                    assert 1100 < editor.width() < 1250
                    assert _find(window, "interviewConversation").height() < window.height() * .7
                _click(window, editor)
                qapp.sendEvent(window, QInputMethodEvent("中文组字", []))
                assert not _visible_hints(editor)
                commit = QInputMethodEvent()
                commit.setCommitString("中文回答。")
                qapp.sendEvent(window, commit)
                assert "中文回答。" in editor.property("text")
            if width == 2560:
                _capture(window, f"resume-polish-interview-wide-{theme}")
    controller.setSidebarCollapsed(True)
    reopened = AppController(controller.repo_root, profile_id=controller.profileId)
    assert reopened.sidebarMode == "collapsed"
    reopened.shutdown()


def test_practice_uses_complete_chinese_statement_and_keeps_source(scene):
    from llm_interview_lab.workspace import init_profile
    window, controller = scene
    # The fixture already has a different active Practice task. Use another
    # isolated Profile instead of bypassing its unfinished-task rule.
    init_profile(controller.repo_root, "statement-review")
    assert controller.switchProfile("statement-review")
    controller.setLanguage("zh-CN")
    assert controller.openProblem("FND-001"), controller.lastActionResult.get("technical_message")
    QTest.qWait(100)
    original = controller.currentTask["task"]
    for size in ((900, 620), (1440, 900)):
        window.resize(*size)
        QTest.qWait(50)
        # At a narrow width the actual statement is in the prompt drawer.
        prompts = [obj for obj in window.findChildren(QObject)
                   if obj.objectName() == "practiceQuestionPrompt"]
        assert prompts
        body = prompts[0].property("text")
        for required in ("count_wrong_predictions", "ValueError", "bool", "O(n)", "非空", "示例", "口述"):
            assert required in body
        assert "完整接口与边界契约仍以" not in body
        assert controller.currentTask["task"] == original
    _capture(window, "resume-polish-practice-chinese")
    controller.setLanguage("en")
    QTest.qWait(60)
    assert "Contract" in _find(window, "practiceQuestionPrompt").property("text")
    assert controller.currentTask["task"] == original


def test_all_current_coding_statements_keep_full_interfaces_and_chinese_requirements():
    root = Path(__file__).resolve().parents[2] / "curriculum/problems"
    reviewed = set()
    for path in root.glob("*/task.md"):
        source = path.read_text(encoding="utf-8")
        pid = re.match(r"# ([A-Z]+(?:-[A-Z]+)?-\d+)", source)[1]
        translated = chinese_statement(pid, source)
        assert len(re.findall(r"[\u4e00-\u9fff]", translated)) > 80, pid
        assert "尚未同步" not in translated, pid
        for block in re.findall(r"```[^\n]*\n.*?```", source, re.S):
            assert block in translated, pid
        if pid in CONTRACTS:
            reviewed.add(pid)
            if re.search(r"^## (?:目标|任务|题目要求)\s*$", source, re.M):
                assert re.sub(r"^# [^\n]+\n+", "", source) == translated
                continue
            for heading in ("## 接口", "## 题目要求", "## 验收", "## 口述与复盘"):
                assert heading in translated, pid
            assert CONTRACTS[pid].split("\n", 1)[1] in translated, pid
    assert reviewed == set(CONTRACTS)


def test_material_choices_and_hash_consent_restore_and_can_be_revoked(controller, tmp_path):
    from llm_interview_lab.workspace import init_profile
    for name, kind in (("resume", "resume"), ("jd", "job_description")):
        source = tmp_path / f"{name}.txt"
        source.write_text(f"仅用于测试的合成 {name}：公开算法实现与独立评测。", encoding="utf-8")
        assert controller.addMaterial(str(source), kind, name, True)
    ids = [row["id"] for row in controller.materials]
    controller.saveInterviewPreferences({"material_id": ids[0], "additional_material_id": ids[1],
                                         "use_materials": True, "use_additional_material": True,
                                         "material_consent": True, "difficulty": "medium"})
    expected = controller.interviewPreferences()
    assert expected["material_consent"]
    restored = AppController(controller.repo_root, profile_id=controller.profileId)
    assert restored.interviewPreferences() == expected
    restored.shutdown()
    original_profile = controller.profileId
    init_profile(controller.repo_root, "isolated-other")
    assert controller.switchProfile("isolated-other")
    assert not controller.interviewPreferences()["material_consent"]
    assert controller.interviewPreferences()["material_id"] == ""
    assert controller.switchProfile(original_profile)
    assert controller.interviewPreferences() == expected
    # A new text extraction version is not the previously authorized content.
    record = controller._materials[0]
    old_snapshot = record.get("text_snapshot")
    record["text_snapshot"] = {"sha256": "new-extraction-version"}
    assert not controller.interviewPreferences()["material_consent"]
    record["text_snapshot"] = old_snapshot
    assert controller.setMaterialAiAccess(ids[0], False)
    assert not controller.interviewPreferences()["material_consent"]
    assert controller.setMaterialAiAccess(ids[0], True)
    assert not controller.interviewPreferences()["material_consent"], "Revoking permission must remove remembered grants"
    controller.saveInterviewPreferences({"material_consent": True})
    assert controller.interviewPreferences()["material_consent"]
    # The real start path still verifies bytes, not merely the cached manifest.
    source_path = controller.repo_root / "workspace/profiles" / controller.profileId / controller.materials[0]["relative_path"]
    source_path.write_text("Changed since authorization", encoding="utf-8")
    result = controller.previewInterviewSettings("post_training_engineer", "medium", f'["{ids[0]}"]', True)
    assert not result.get("parts")


def test_qml_restores_material_use_after_navigation_and_restarting_preparation(scene, tmp_path):
    window, controller = scene
    source = tmp_path / "resume.txt"
    source.write_text("合成简历：使用公开数据实现 DPO。", encoding="utf-8")
    assert controller.addMaterial(str(source), "resume", "合成简历", True)
    mid = controller.materials[0]["id"]
    controller.saveInterviewPreferences({"material_id": mid, "use_materials": True, "material_consent": True})
    controller.finishInterview()
    controller.prepareInterview()
    window.resize(1280, 800)
    QTest.qWait(80)
    for page in ("home", "interview", "settings", "interview"):
        controller.navigate(page)
        QTest.qWait(50)
    assert _find(window, "interviewUseMaterials").property("checked")
    assert _find(window, "interviewMaterialConsent").property("checked")
    assert _find(window, "interviewPrimaryMaterial").property("currentValue") == mid
    _click(window, _find(window, "interviewEditSettings"))
    QTest.qWait(40)
    consent = _find(window, "interviewMaterialConsent")
    scroll = _find(window, "interviewSetupScroll")
    content = scroll.property("contentItem")
    content.setProperty("contentY", max(0, consent.mapToItem(content, QPointF()).y() - 60))
    QTest.qWait(40)
    _click(window, consent)
    assert not controller.interviewPreferences()["material_consent"]
    _click(window, consent)
    assert controller.interviewPreferences()["material_consent"]
    _capture(window, "resume-polish-material-preferences")


@pytest.mark.parametrize("success", [True, False])
def test_startup_connects_last_api_once_without_blocking_ui(controller, monkeypatch, success):
    calls = []
    class Provider:
        async def test_connection(self):
            calls.append("probe")
            await asyncio.sleep(.1)
            return ConnectionResult(success, "可操作的合成连接结果", 100)
    monkeypatch.setattr("llm_interview_lab.desktop.controller.create_chat_provider", lambda *a, **k: Provider())
    assert controller.saveConnection("last-api", "ollama", "synthetic-model", "合成连接", "http://localhost:11434", "", "")
    controller.saveInterviewPreferences({"ai_mode": "provider", "connection_id": "last-api"})
    restarted = AppController(controller.repo_root, profile_id=controller.profileId)
    try:
        _wait_for_asr(lambda: bool(calls), 4000)
        assert not restarted.busy
        _wait_for_asr(lambda: restarted.connections[0]["status"] != "测试中", 4000)
        assert restarted.connections[0]["ready"] == success
        assert bool(restarted.connectionError) == (not success)
        restarted._restore_ai_connection()
        assert calls == ["probe"]
    finally:
        restarted.shutdown()


def test_startup_codex_waits_for_discovery_and_no_ai_never_connects(controller, monkeypatch):
    calls = []
    monkeypatch.setattr(controller, "connectCodex", calls.append)
    controller.saveInterviewPreferences({"ai_mode": "codex"})
    controller._ai_restore_profile = ""
    controller._codex_available = False
    controller._restore_ai_connection()
    assert not calls
    controller._codex_available = True
    controller._restore_ai_connection()
    controller._restore_ai_connection()
    assert calls == ["interviewer"]
    controller._ai_restore_profile = ""
    controller.saveInterviewPreferences({"ai_mode": "disabled"})
    controller._restore_ai_connection()
    assert calls == ["interviewer"]
