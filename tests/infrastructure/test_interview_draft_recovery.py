"""Persisted oral drafts are private editing state, never interview evidence."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from PySide6.QtCore import QCoreApplication, QMetaObject, Qt
from PySide6.QtGui import QInputMethodEvent
from PySide6.QtTest import QTest

from llm_interview_lab.application import ApplicationError
from llm_interview_lab.desktop.controller import AppController
from tests.infrastructure.test_interview_input_runtime import (
    qapp, public_repo, controller, scene, _find, _click, _wait_for_asr, REPO,
)


def identity(controller):
    return (controller.profileId, controller.interview["interview_id"], controller.interview["question"]["question_id"])


def test_oral_draft_is_atomic_isolated_and_not_answer_evidence(controller):
    service = controller.service
    ids = identity(controller)
    original = service.interview_session(*ids[:2])
    answer = "合成草稿：我会用独立对照解释 KL，而不是只背结论。\n尚未提交。"
    assert service.interview_draft(*ids) == ""
    service.save_interview_draft(*ids, answer)
    assert service.interview_draft(*ids) == answer
    assert service.interview_session(*ids[:2]) == original
    assert not controller.queueInterviewDraft("another-synthetic-profile", *ids[1:], "不能串档")
    assert not controller.queueInterviewDraft(*ids[:2], "q-999", "不能串题")
    path = service._interview_draft_context(*ids)[1]
    assert list(path.parent.glob(".*.tmp")) == []
    value = json.loads(path.read_text(encoding="utf-8"))
    value["text"] = "意外修改的 synthetic 文本"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ApplicationError, match="草稿文件损坏"):
        service.interview_draft(*ids)
    assert service.interview_session(*ids[:2]) == original


def test_ime_debounce_focus_reload_and_real_process_restart(scene, qapp):
    window, controller = scene
    controller.navigate("interview")
    editor = _find(window, "interviewAnswerEditor")
    ids = identity(controller)
    _click(window, editor)
    qapp.sendEvent(window, QInputMethodEvent("停句校准", []))
    QTest.qWait(700)
    assert controller.service.interview_draft(*ids) == ""
    commit = QInputMethodEvent()
    commit.setCommitString("停句校准后的中文回答。")
    qapp.sendEvent(window, commit)
    assert _wait_for_asr(lambda: controller.interview.get("draft_status") == "saved")
    assert controller.service.interview_draft(*ids) == "停句校准后的中文回答。"
    cursor = editor.property("cursorPosition")
    controller.refreshInterviewClock()
    controller._load_interview(ids[1])
    QTest.qWait(50)
    assert editor.property("text") == "停句校准后的中文回答。"
    assert editor.property("cursorPosition") == cursor
    editor.setProperty("text", "切页前的新草稿；不提交。")
    controller.navigate("home")
    QTest.qWait(50)
    assert controller.service.interview_draft(*ids) == "切页前的新草稿；不提交。"
    controller.navigate("interview")
    QTest.qWait(50)
    editor.setProperty("text", "退出前最后一段中文。")
    window.close()  # Real QML close path commits IME and flushes the debounce.
    assert controller._shutdown_done
    code = """
import json, sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings
import llm_interview_lab.desktop.controller as module
app = QApplication(['synthetic-draft-restart'])
module.QSettings = lambda *args: QSettings(sys.argv[2], QSettings.IniFormat)
module.AppController.refreshCodexAvailability = lambda self: None
module.AppController._restore_ai_connection = lambda self: None
controller = module.AppController(Path(sys.argv[1]), profile_id=sys.argv[3])
controller._load_interview(sys.argv[4])
print(json.dumps({'draft': controller.interview.get('draft_text'), 'locked': controller.interview['answer_locked'],
                  'question': controller.interview['question']['question_id']}, ensure_ascii=False))
controller.shutdown()
"""
    result = subprocess.run([sys.executable, "-c", code, str(controller.repo_root), controller._settings.fileName(), *ids[:2]],
        env={**os.environ, "PYTHONPATH": str(REPO / "src"), "PYTHONIOENCODING": "utf-8", "QT_QPA_PLATFORM": "offscreen"},
        text=True, encoding="utf-8", capture_output=True, timeout=40)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout.strip().splitlines()[-1]) == {"draft": "退出前最后一段中文。", "locked": False, "question": ids[2]}
    session = controller.service.interview_session(*ids[:2])
    assert session["answers"] == {} and session["assessments"] == {}


def test_save_failure_keeps_window_text_and_allows_retry(scene, monkeypatch):
    window, controller = scene
    controller.navigate("interview")
    editor = _find(window, "interviewAnswerEditor")
    ids = identity(controller)
    controller.service.save_interview_draft(*ids, "上一版磁盘草稿")
    editor.setProperty("text", "不能丢失的本轮输入")
    with monkeypatch.context() as scoped:
        def disk_full(*args):
            raise OSError("No space left on device")
        scoped.setattr("llm_interview_lab.application.os.replace", disk_full)
        assert not controller.flushInterviewDraft()
        assert controller.interview["draft_status"] == "error"
        window.close()
        QTest.qWait(40)
        assert window.isVisible() and not controller._shutdown_done
        assert editor.property("text") == "不能丢失的本轮输入"
        assert controller.service.interview_draft(*ids) == "上一版磁盘草稿"
    _click(window, _find(window, "retryInterviewDraft"))
    assert controller.service.interview_draft(*ids) == "不能丢失的本轮输入"
    assert controller.interview["draft_status"] == "saved"


def test_locked_answer_wins_over_pending_and_stored_drafts(controller):
    ids = identity(controller)
    assert controller.queueInterviewDraft(*ids, "旧的未提交草稿")
    controller.service.answer_interview(*ids, "明确提交的新回答")
    controller._load_interview(ids[1])
    assert controller.interview["answer_locked"]
    assert controller.interview["answer_text"] == "明确提交的新回答"
    assert controller._pending_interview_draft is None
    assert not controller.queueInterviewDraft(*ids, "过期回调")
    assert controller.service.interview_draft(*ids) == ""
    with pytest.raises(ApplicationError, match="锁定"):
        controller.service.save_interview_draft(*ids, "不能覆盖")
    assert controller.service.interview_answer_text(*ids) == "明确提交的新回答"


def test_knowledge_draft_debounce_and_close_use_existing_save(scene):
    window, controller = scene
    controller.navigate("learn")
    _click(window, _find(window, "knowledgeBrowserButton"))
    assert controller.openKnowledgeCard("EGT-QB-028")
    QTest.qWait(40)
    editor = _find(window, "knowledgePracticeAnswer")
    editor.setProperty("text", "GRPO 合成口述草稿")
    assert _wait_for_asr(lambda: controller.service.knowledge_answer(controller.profileId, "EGT-QB-028") == "GRPO 合成口述草稿")
    editor.setProperty("text", "知识页退出前最后一段")
    window.close()
    assert controller.service.knowledge_answer(controller.profileId, "EGT-QB-028") == "知识页退出前最后一段"
