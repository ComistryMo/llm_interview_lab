"""Exercise real Qt input/IME behavior and persisted dynamic interview turns."""

from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from uuid import uuid4

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Material")
pytest.importorskip("PySide6")

from PySide6.QtCore import QCoreApplication, QMetaObject, QObject, QPoint, QPointF, QSettings, Qt, QUrl
from PySide6.QtGui import QFont, QGuiApplication, QInputMethodEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest

from llm_interview_lab.desktop.controller import AppController
from llm_interview_lab.ai.codex_backend import CodexEvent

REPO = Path(__file__).resolve().parents[2]
QML = REPO / "src/llm_interview_lab/desktop/qml/Main.qml"


@pytest.fixture(scope="module")
def qapp():
    app = QGuiApplication.instance() or QApplication(["interview-input-tests"])
    if os.name == "nt":
        app.setFont(QFont("Microsoft YaHei UI", 10))
    return app


@pytest.fixture(scope="module")
def public_repo(tmp_path_factory):
    root = tmp_path_factory.mktemp("interview-input-public")
    for name in ("pyproject.toml", ".gitignore"):
        shutil.copy2(REPO / name, root / name)
    for name in ("curriculum", "coach", "workspace/schema", "workspace/templates"):
        shutil.copytree(REPO / name, root / name)
    (root / "workspace/profiles").mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return root


@pytest.fixture
def controller(qapp, public_repo, tmp_path, monkeypatch):
    # The explicit organization/application constructor uses NativeFormat on
    # Windows even after setDefaultFormat. Redirect that constructor as well.
    monkeypatch.setattr("llm_interview_lab.desktop.controller.QSettings", lambda *args: QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat))
    monkeypatch.setattr(AppController, "refreshCodexAvailability", lambda self: None)
    profile = "input-" + uuid4().hex[:10]
    controller = AppController(public_repo, profile_id=profile, log_root=tmp_path / "logs")
    assert controller.completeOnboarding(profile, "post_training_engineer", "intern", "codex", "{}")
    preview = controller.dynamicInterviewContextPreview("post_training_engineer", "intern", "hard", "", False)
    controller.startDynamicPersonalizedInterview(
        "post_training_engineer", "intern", "hard", "codex", "", False, preview["context_sha256"]
    )
    assert controller.interview["question"]["question_id"] == "q-001"
    yield controller
    controller.shutdown()
    QCoreApplication.processEvents()


@pytest.fixture
def scene(controller):
    engine = QQmlApplicationEngine()
    qml_errors = []
    engine.warnings.connect(lambda values: qml_errors.extend(value.toString() for value in values))
    engine.rootContext().setContextProperty("backend", controller)
    engine.load(QUrl.fromLocalFile(str(QML)))
    assert engine.rootObjects(), qml_errors
    window = engine.rootObjects()[0]
    assert isinstance(window, QQuickWindow)
    window.show()
    QTest.qWait(80)
    yield window, controller
    assert not qml_errors, "\n".join(qml_errors)
    window.close()
    engine.deleteLater()
    QCoreApplication.sendPostedEvents()
    QCoreApplication.processEvents()


def _items(item):
    for child in item.childItems():
        yield child
        yield from _items(child)


def _find(window, name):
    item = next((item for item in _items(window.contentItem()) if item.objectName() == name), None)
    if item is None:
        # Closed Popup content is owned by the QML object tree, not the scene.
        item = window.findChild(QObject, name)
    assert item is not None, name
    return item


def _click(window, item):
    point = item.mapToScene(QPointF(item.width() / 2, min(20, item.height() / 2)))
    QTest.mouseClick(window, Qt.LeftButton, pos=QPoint(round(point.x()), round(point.y())))
    QCoreApplication.processEvents()


def _visible_hints(editor):
    return [
        item for item in _items(editor)
        if "Placeholder" in item.metaObject().className()
        and item.property("visible") and item.property("opacity") > 0
        and item.property("text") and item.property("color").alpha() > 0
    ]


def _capture(window, name):
    directory = os.environ.get("LLM_LAB_UI_EVIDENCE_DIR")
    if directory:
        QTest.qWait(150)  # Let the production hover/theme transition settle.
        destination = Path(directory)
        destination.mkdir(parents=True, exist_ok=True)
        assert window.grabWindow().save(str(destination / f"{name}.png"))


def _enter_coding_round(controller, coding_id="FND-002"):
    """Prepare a real persisted session; replies here are fixture data, not AI evidence."""
    for stage in (["experience"] * 8 + ["theory"] * 4 + ["coding"]):
        question = controller.interview["question"]
        controller.lockInterviewAnswer("合成验收回答：我负责偏好数据去重，用独立留出集验证。")
        preview = controller.interviewContextPreview(controller.interview["answer_text"], False)
        assert preview["parts"]
        controller.service.advance_dynamic_interview(
            controller.profileId, controller.interview["interview_id"], question["question_id"],
            {"scores": {name: 3 for name in question["rubric"]["dimensions"]},
             "evidence": "合成验收数据，仅用于界面测试。", "confidence": "medium", "fatal_issues": [],
             "next_stage": stage, "follow_up": "如何验证你提到的数据去重？" if stage != "coding" else "",
             "coding_problem_id": coding_id if stage == "coding" else "",
             "next_skill_ids": [next(iter(controller.service.roles.roles["post_training_engineer"].skill_weights))]
                               if stage != "coding" else []},
            context_sha256=controller._interview_context_confirmation[-1],
        )
        controller._load_interview(controller.interview["interview_id"])
    assert controller.interview["question"]["kind"] == "coding"
    QTest.qWait(100)


def _within_window(window, item):
    start = item.mapToScene(QPointF())
    return (start.x() >= 0 and start.y() >= 0
            and start.x() + item.width() <= window.width() + 1
            and start.y() + item.height() <= window.height() + 1)


def _scroll_to_voice_control(window, item):
    settings = _find(window, "interviewVoiceSettingsScroll")
    if not settings.isVisible():
        assert _within_window(window, item)
        return
    viewport = settings.property("contentItem")
    y = item.mapToItem(viewport, QPointF()).y()
    if y + item.height() > viewport.height():
        viewport.setProperty("contentY", viewport.property("contentY") + y + item.height() - viewport.height() + 16)
    QTest.qWait(100)
    assert _within_window(window, item)


def _stub_dictation_capture(controller, monkeypatch, source=None):
    """Inject only the microphone, never a demo controller or transcript UI."""
    recorder = controller._voice_recorder

    def start(path):
        path.parent.mkdir(parents=True, exist_ok=True)
        if source:
            shutil.copy2(source, path)
        else:
            path.write_bytes(b"synthetic audio for stub decoder")
        recorder.path = path
        recorder.state = "recording"
        recorder.error_message = ""
        recorder.duration_ms = 0
        recorder.changed.emit()

    def stop():
        recorder.state = "recorded"
        recorder.changed.emit()
        recorder.ready.emit(str(recorder.path))

    monkeypatch.setattr(recorder, "start", start)
    monkeypatch.setattr(recorder, "stop", stop)


def _dictation_model_ready(controller, monkeypatch):
    monkeypatch.setattr(controller._local_stt, "ready", lambda: True)
    monkeypatch.setattr(controller._local_stt, "runtime_available", lambda: True)
    controller._refresh_local_stt_status()
    controller.stateChanged.emit()


@pytest.mark.parametrize("size,theme,scale", [
    ((900, 620), "dark", 1.25), ((1080, 680), "light", 1.0),
    ((1280, 800), "dark", 1.0), ((1440, 900), "light", 1.0),
])
def test_dictation_click_records_and_stop_automatically_appends(scene, monkeypatch, size, theme, scale):
    window, controller = scene
    _dictation_model_ready(controller, monkeypatch)
    _stub_dictation_capture(controller, monkeypatch)
    calls = []

    def transcribe(path):
        calls.append(path)
        return "合成转录：我负责数据清洗和离线评估。"

    monkeypatch.setattr(controller._local_stt, "transcribe", transcribe)
    controller.setTheme(theme)
    window.resize(*size)
    window.setProperty("displayFontScaleOverride", scale)
    QTest.qWait(120)
    answer = _find(window, "interviewAnswerEditor")
    answer.setProperty("text", "保留原有回答。")
    button = _find(window, "toggleInterviewVoice")
    _click(window, button)
    QTest.qWait(80)
    assert controller.interviewVoice["state"] == "recording"
    stop = _find(window, "finishInterviewDictation")
    assert stop.isVisible() and stop.property("text") == "完成录音"
    assert not button.isVisible(), "Only one recording action should be visible"
    assert not _find(window, "lockInterviewAnswer").isEnabled()
    assert not _find(window, "interviewVoiceConnection").isVisible()
    assert not _find(window, "downloadLocalSttModel").isVisible()
    assert not _find(window, "transcribeInterviewRecording").isVisible()
    card = _find(window, "interviewVoiceCard")
    assert card.height() < 150, "Ordinary dictation must not expand the entire settings form"
    assert _within_window(window, card) and _within_window(window, stop)
    for item in _items(card):
        if item.isVisible() and item.property("text"):
            assert item.mapToItem(card, QPointF()).x() >= 0
            assert item.mapToItem(card, QPointF(item.width(), item.height())).x() <= card.width() + 1
    _capture(window, f"dictation-recording-{size[0]}-{theme}")
    _click(window, stop)
    for _ in range(100):
        QTest.qWait(20)
        time.sleep(.005)
        if controller.interviewVoice["transcription_state"] == "transcribed":
            break
    assert len(calls) == 1
    assert controller.interviewVoice["transcription_state"] == "transcribed"
    assert answer.property("text") == "保留原有回答。\n合成转录：我负责数据清洗和离线评估。"
    assert not controller.interview["answer_locked"] and not controller.busy
    assert button.property("text") == "语音输入"
    assert not _find(window, "transcribeInterviewRecording").isVisible()
    _capture(window, f"dictation-text-{size[0]}-{theme}")


@pytest.mark.parametrize("changed", ["profile", "question", "finished"])
def test_dictation_stop_cannot_start_inference_in_changed_context(controller, monkeypatch, changed):
    _dictation_model_ready(controller, monkeypatch)
    _stub_dictation_capture(controller, monkeypatch)
    monkeypatch.setattr(controller._local_stt, "transcribe", lambda _: pytest.fail("Stale recording must not be transcribed"))
    assert controller.startInterviewDictation("local-sensevoice", False)
    assert not controller.startInterviewDictation("local-sensevoice", False)
    assert controller.stopInterviewRecording()
    if changed == "profile":
        controller._profile_id = "another-synthetic-profile"
    elif changed == "question":
        controller._interview["question"] = {**controller.interview["question"], "question_id": "q-002"}
    else:
        controller._interview["status"] = "incomplete"
    QTest.qWait(80)
    assert not controller.busy and not controller._voice_auto_transcription


def test_dictation_remote_consent_is_explicit_and_only_for_one_recording(controller, monkeypatch):
    _stub_dictation_capture(controller, monkeypatch)
    calls = []
    monkeypatch.setattr(controller, "transcribeInterviewRecording", lambda *args: calls.append(args))
    assert not controller.startInterviewDictation("speech-api", False)
    assert "明确授权" in controller.interviewVoice["error"]
    assert controller.startInterviewDictation("speech-api", True)
    assert controller.stopInterviewRecording()
    QTest.qWait(80)
    assert calls == [("speech-api", True)]
    controller._voice_recorder.ready.emit(str(controller._voice_recorder.path))
    QTest.qWait(20)
    assert len(calls) == 1
    assert not controller.startInterviewDictation("speech-api", False)


def test_dictation_failure_keeps_draft_and_audio_and_retries(scene, monkeypatch):
    window, controller = scene
    _dictation_model_ready(controller, monkeypatch)
    _stub_dictation_capture(controller, monkeypatch)
    answer = _find(window, "interviewAnswerEditor")
    answer.setProperty("text", "已有文字不能丢失。")

    def fail(_):
        raise RuntimeError("未听到清晰的人声，请重试。")

    monkeypatch.setattr(controller._local_stt, "transcribe", fail)
    _click(window, _find(window, "toggleInterviewVoice"))
    _click(window, _find(window, "finishInterviewDictation"))
    for _ in range(100):
        QTest.qWait(20)
        time.sleep(.005)
        if controller.interviewVoice["transcription_state"] == "error":
            break
    assert not controller.busy
    assert "人声" in _find(window, "interviewVoiceError").property("text")
    assert answer.property("text") == "已有文字不能丢失。"
    audio = controller._voice_recorder.path
    digest = hashlib.sha256(audio.read_bytes()).hexdigest()
    monkeypatch.setattr(controller._local_stt, "transcribe", lambda _: "重试的合成结果。")
    retry = _find(window, "transcribeInterviewRecording")
    assert retry.isVisible() and retry.isEnabled()
    _scroll_to_voice_control(window, retry)
    _click(window, retry)
    for _ in range(100):
        QTest.qWait(20)
        time.sleep(.005)
        if controller.interviewVoice["transcription_state"] == "transcribed":
            break
    assert answer.property("text") == "已有文字不能丢失。\n重试的合成结果。"
    assert hashlib.sha256(audio.read_bytes()).hexdigest() == digest
    assert not controller.interview["answer_locked"]


def test_recording_start_reaches_recorder_with_profile_local_path(controller, monkeypatch):
    destinations = []
    errors = []
    monkeypatch.setattr(controller._voice_recorder, "start", destinations.append)
    monkeypatch.setattr(controller, "_show_error", errors.append)
    assert controller.startInterviewRecording(), [
        f"{type(error).__name__}: {error}" for error in errors
    ]
    assert len(destinations) == 1
    from llm_interview_lab.workspace import profile_paths
    expected = profile_paths(controller.repo_root, controller.profileId).interviews_root
    assert destinations[0].parent == expected / controller.interview["interview_id"] / "audio"
    assert destinations[0].name.startswith("q-001-")
    assert destinations[0].suffix == ".wav"


@pytest.mark.parametrize("failure,expected", [
    (RuntimeError("未检测到可用麦克风；你仍可直接输入文字回答"), "麦克风"),
    (PermissionError("private-path-must-not-leak"), "目录不可写"),
    (NameError("private-path-must-not-leak"), "RECORDING_FAILED"),
])
def test_recording_failure_is_inline_and_logged(controller, monkeypatch, caplog, failure, expected):
    def fail(_path):
        raise failure
    monkeypatch.setattr(controller._voice_recorder, "start", fail)
    assert not controller.startInterviewRecording()
    assert controller.interviewVoice["state"] == "error"
    assert expected in controller.interviewVoice["error"]
    assert "error_type=" + type(failure).__name__ in caplog.text
    assert "private-path-must-not-leak" not in caplog.text + controller.interviewVoice["error"]
    assert "操作未完成" not in controller.interviewVoice["error"]
    assert not controller.busy


def test_recording_ticks_do_not_refresh_application_or_probe_stt(scene, monkeypatch):
    window, controller = scene
    _click(window, _find(window, "toggleInterviewVoice"))
    QTest.qWait(100)
    all_changes, voice_changes = [], []
    controller.stateChanged.connect(lambda: all_changes.append(True))
    controller.interviewVoiceChanged.connect(lambda: voice_changes.append(True))

    def unexpected_probe():
        pytest.fail("A QML refresh must not scan STT model files or Python import paths")

    monkeypatch.setattr(controller._local_stt, "ready", unexpected_probe)
    monkeypatch.setattr(controller._local_stt, "runtime_available", unexpected_probe)
    for duration in range(10, 4011, 10):
        controller._voice_recorder._duration_changed(duration)
        assert "ready" in controller.localStt
    assert not all_changes
    assert len(voice_changes) == 4
    assert controller.interviewVoice["duration_ms"] == 4010
    assert "04" in _find(window, "interviewVoiceDuration").property("text")


def test_interview_preferences_survive_process_restart_and_stay_profile_local(controller, tmp_path):
    from llm_interview_lab.workspace import init_profile
    # Existing users inherit their actual last session, then changes are saved
    # before starting another one. No materials/consent/secret belong in this map.
    assert controller.interviewPreferences()["difficulty"] == "hard"
    assert controller.interviewPreferences()["seniority"] == "intern"
    saved = dict(role_id="ai_product_manager", seniority="mid", difficulty="easy",
                 ai_mode="provider", connection_id="second-api", transcription_connection_id="speech-api")
    controller.saveInterviewPreferences({**saved, "consent": True, "api_key": "do-not-store"})
    assert controller.interviewPreferences() == saved
    controller.setCodexModel("persisted-synthetic-model")
    controller.setCodexReasoningEffort("low")
    controller._settings.sync()
    code = """
import json, sys
from pathlib import Path
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
import llm_interview_lab.desktop.controller as module
app = QApplication(['preference-restart'])
module.QSettings = lambda *args: QSettings(sys.argv[2], QSettings.IniFormat)
module.AppController.refreshCodexAvailability = lambda self: None
controller = module.AppController(Path(sys.argv[1]))
print(json.dumps({'profile': controller.profileId, 'preferences': controller.interviewPreferences(),
                  'model': controller.codexModel, 'effort': controller.codexReasoningEffort}))
controller.shutdown()
"""
    env = {**os.environ, "PYTHONPATH": str(REPO / "src"), "QT_QPA_PLATFORM": "offscreen"}
    result = subprocess.run([sys.executable, "-c", code, str(controller.repo_root), controller._settings.fileName()],
                            env=env, capture_output=True, text=True, timeout=40)
    assert result.returncode == 0, result.stderr
    restored = json.loads(result.stdout.strip().splitlines()[-1])
    assert restored == dict(profile=controller.profileId, preferences=saved,
                            model="persisted-synthetic-model", effort="low")
    previous_profile = controller.profileId
    other = "prefs-other-" + uuid4().hex[:8]
    init_profile(controller.repo_root, other)
    assert controller.switchProfile(other)
    assert controller.interviewPreferences()["ai_mode"] == "disabled"
    assert controller.interviewPreferences()["connection_id"] == ""
    controller.saveInterviewPreferences({"difficulty": "medium", "ai_mode": "codex"})
    assert controller.switchProfile(previous_profile)
    assert controller.interviewPreferences() == saved
    assert "do-not-store" not in Path(controller._settings.fileName()).read_text(encoding="utf-8")


def test_interview_setup_remembers_user_choices_after_navigation_and_connection_refresh(scene):
    window, controller = scene
    assert controller.saveConnection("first-api", "ollama", "synthetic-a", "第一个连接", "http://localhost:11434", "", "")
    assert controller.saveConnection("second-api", "ollama", "synthetic-b", "第二个连接", "http://localhost:11434", "", "")
    controller.finishInterview()
    QTest.qWait(80)
    _click(window, _find(window, "configureAnotherInterview"))
    QTest.qWait(60)

    def select(name, index):
        item = _find(window, name)
        item.forceActiveFocus()
        QTest.keyClick(window, Qt.Key_Space)
        QTest.keyClick(window, Qt.Key_Home)
        for _ in range(index):
            QTest.keyClick(window, Qt.Key_Down)
        QTest.keyClick(window, Qt.Key_Return)
        QTest.qWait(30)
        assert item.property("currentIndex") == index

    select("interviewSenioritySelector", 2)
    select("interviewDifficultySelector", 0)
    select("interviewAiModeSelector", 1)
    select("personalizedInterviewConnection", 1)
    connection = _find(window, "personalizedInterviewConnection").property("currentValue")
    saved = controller.interviewPreferences()
    assert (saved["seniority"], saved["difficulty"], saved["ai_mode"], saved["connection_id"]) == ("mid", "easy", "provider", connection)
    controller.navigate("home")
    QTest.qWait(50)
    controller.navigate("interview")
    QTest.qWait(100)
    assert _find(window, "interviewSenioritySelector").property("currentValue") == "mid"
    assert _find(window, "interviewDifficultySelector").property("currentValue") == "easy"
    assert _find(window, "interviewAiModeSelector").property("currentValue") == "provider"
    controller.refresh()
    QTest.qWait(100)
    assert _find(window, "personalizedInterviewConnection").property("currentValue") == connection
    assert controller.deleteConnection(connection)
    QTest.qWait(100)
    assert _find(window, "personalizedInterviewConnection").property("currentIndex") == -1
    assert controller.interviewPreferences()["connection_id"] == connection
    assert not _find(window, "interviewMaterialConsent").property("checked")


@pytest.mark.parametrize("size", [(900, 620), (1280, 800)])
def test_voice_error_and_transcription_choices_use_real_capabilities(scene, monkeypatch, size):
    window, controller = scene
    monkeypatch.setattr("llm_interview_lab.ai.credentials.KeyringCredentialStore.save",
                        lambda self, profile, connection, key: "synthetic-reference-" + connection)
    assert controller.saveConnection("text-api", "deepseek", "synthetic-text-model", "DeepSeek", "", "synthetic-key", "none")
    assert controller.transcriptionConnections == []
    window.resize(*size)
    window.setProperty("displayFontScaleOverride", 1.25)
    QTest.qWait(150)
    _dictation_model_ready(controller, monkeypatch)
    from llm_interview_lab.desktop import voice as voice_module
    monkeypatch.setattr(voice_module.QMediaDevices, "audioInputs", staticmethod(lambda: []))
    _click(window, _find(window, "toggleInterviewVoice"))
    QTest.qWait(100)
    assert _find(window, "interviewVoiceState").property("text") == "语音输入未完成"
    error = _find(window, "interviewVoiceError")
    assert error.isVisible() and "麦克风" in error.property("text")
    assert error.property("contentHeight") <= error.height() + 1
    viewport = _find(window, "interviewVoiceCard")
    assert 0 <= error.mapToItem(viewport, QPointF()).y()
    assert error.mapToItem(viewport, QPointF(0, error.height())).y() <= viewport.height()
    _click(window, _find(window, "interviewVoiceSettings"))
    QTest.qWait(100)
    assert "本地模型已下载" in _find(window, "interviewLocalSttStatus").property("text")
    assert _find(window, "interviewVoiceConnection").property("count") == 1
    assert _find(window, "interviewVoiceConnection").property("currentValue") == "local-sensevoice"
    assert not _find(window, "interviewVoiceRemoteConsent").isVisible()
    assert _find(window, "downloadLocalSttModel").isEnabled()
    assert not _find(window, "transcribeInterviewRecording").isVisible()
    _capture(window, f"voice-missing-microphone-{size[0]}")
    assert controller.saveConnection("speech-api", "openai-compatible", "synthetic-chat-model", "语音连接", "http://localhost:8080/v1", "synthetic-key", "")
    assert [c["connection_id"] for c in controller.transcriptionConnections] == ["speech-api"]


@pytest.mark.skipif(os.environ.get("LLM_LAB_TEST_MICROPHONE") != "1", reason="Explicit opt-in required for real microphone capture")
def test_real_microphone_start_stop_from_production_page(scene, monkeypatch):
    import wave
    window, controller = scene
    window.resize(1280, 800)
    _dictation_model_ready(controller, monkeypatch)
    # Exercise the real microphone but do not decode ambient/private speech.
    # The real decoder is independently checked using the public Chinese WAV.
    monkeypatch.setattr(controller._local_stt, "transcribe", lambda _: "合成转录测试结果。")
    QTest.qWait(150)
    recordings = []
    capture_graphs = []
    for cycle in range(3):
        _click(window, _find(window, "toggleInterviewVoice"))
        assert controller.interviewVoice["state"] == "recording", controller.interviewVoice
        recorder = controller._voice_recorder
        capture_graphs.append((recorder._capture, recorder._audio_input, recorder._recorder))
        assert len(recorder.children()) == 3, "Native capture objects must not accumulate between answers"
        assert not controller.startInterviewRecording(), "Duplicate start must not replace the active recorder"
        QTest.qWait(1700)
        first_tick = controller.interviewVoice["duration_ms"]
        assert first_tick >= 1000, "Recording must advance before Stop, not only when the file closes"
        QTest.qWait(1700)
        assert controller.interviewVoice["duration_ms"] > first_tick
        display = _find(window, "interviewVoiceDuration").property("text")
        assert display != "0:00"
        _capture(window, f"voice-recording-windows-{cycle + 1}")
        stopped_at = time.perf_counter()
        _click(window, _find(window, "finishInterviewDictation"))
        for _ in range(50):
            QTest.qWait(20)
            if controller.interviewVoice["state"] != "recording":
                break
        stop_seconds = time.perf_counter() - stopped_at
        assert controller.interviewVoice["audio_ready"], controller.interviewVoice
        assert stop_seconds < 2, f"Stop blocked the UI for {stop_seconds:.2f} seconds"
        path = controller._voice_recorder.path
        with wave.open(str(path), "rb") as audio:
            duration = audio.getnframes() / audio.getframerate()
            assert duration >= 2, duration
            print(f"REAL_MICROPHONE_OK cycle={cycle + 1} stop_seconds={stop_seconds:.3f} duration={duration:.2f}s bytes={path.stat().st_size} channels={audio.getnchannels()} rate={audio.getframerate()}")
        recordings.append((path, hashlib.sha256(path.read_bytes()).hexdigest()))
        for _ in range(100):
            QTest.qWait(20)
            time.sleep(.005)
            if controller.interviewVoice["transcription_state"] == "transcribed":
                break
        assert controller.interviewVoice["transcription_state"] == "transcribed"
        assert not controller.busy and not controller.interview["answer_locked"]
        assert not _find(window, "interviewVoiceRemoteConsent").property("checked")
        editor = _find(window, "interviewAnswerEditor")
        _click(window, editor)
        QTest.keyClick(window, Qt.Key_End, Qt.ControlModifier)
        QTest.keyClick(window, Qt.Key_O)
        QTest.keyClick(window, Qt.Key_K)
        assert editor.property("text").endswith("ok"), "UI must accept input after Stop"
        _capture(window, f"voice-recorded-windows-{cycle + 1}")
    assert len({path for path, _ in recordings}) == 3
    assert capture_graphs[0] == capture_graphs[1] == capture_graphs[2]
    assert all(hashlib.sha256(path.read_bytes()).hexdigest() == digest for path, digest in recordings)


def test_local_stt_model_download_is_single_background_action(scene, monkeypatch):
    import threading
    from llm_interview_lab.ai.local_transcription import DownloadCancelled

    window, controller = scene
    calls = []
    release = threading.Event()

    def download(progress, cancel):
        calls.append(True)
        progress(40)
        assert release.wait(5)
        if cancel.is_set():
            raise DownloadCancelled()

    monkeypatch.setattr(controller._local_stt, "download", download)
    window.resize(900, 620)
    _click(window, _find(window, "toggleInterviewVoice"))
    QTest.qWait(100)
    # Use the real production button, then try a repeated invocation.
    button = _find(window, "downloadLocalSttModel")
    _scroll_to_voice_control(window, button)
    _capture(window, "local-stt-download-900")
    _click(window, button)
    controller.downloadLocalSttModel()
    try:
        for _ in range(100):
            QTest.qWait(10)
            if controller.localStt["progress"] == 40:
                break
        assert len(calls) == 1 and controller.localStt["downloading"]
        assert not controller.busy, "Downloading must not block the user's typed answer"
        assert not button.isEnabled()
        assert "40%" in _find(window, "interviewLocalSttStatus").property("text")
        QMetaObject.invokeMethod(_find(window, "cancelLocalSttDownload"), "clicked", Qt.DirectConnection)
    finally:
        release.set()
    for _ in range(100):
        QTest.qWait(10)
        if not controller.localStt["downloading"]:
            break
    assert not controller.localStt["downloading"] and not controller.localStt["error"]
    assert button.isEnabled()


def test_local_stt_missing_model_and_remote_consent_preserve_recording(controller, monkeypatch, tmp_path):
    from llm_interview_lab.ai.local_transcription import LOCAL_STT_ID

    audio = tmp_path / "synthetic.wav"
    audio.write_bytes(b"synthetic-recording")
    controller._voice_recorder.path = audio
    controller._voice_recorder.state = "recorded"
    monkeypatch.setattr(controller._local_stt, "transcribe", lambda _: pytest.fail("No inference without model"))
    controller.transcribeInterviewRecording(LOCAL_STT_ID, False)
    assert "请先点击下载" in controller.interviewVoice["error"]
    assert audio.exists() and controller.interviewVoice["audio_ready"] and not controller.busy
    errors = []
    monkeypatch.setattr(controller, "_show_error", errors.append)
    controller.transcribeInterviewRecording("speech-api", False)
    assert "明确授权" in errors[-1]
    assert not controller._voice_transcription_operation_id


@pytest.mark.parametrize("switch_question", [False, True])
def test_local_stt_draft_result_is_single_and_question_scoped(controller, monkeypatch, tmp_path, switch_question):
    import threading
    from llm_interview_lab.ai.local_transcription import LOCAL_STT_ID

    release = threading.Event()
    calls = []
    results = []
    controller.interviewTranscriptReady.connect(results.append)
    controller._voice_recorder.path = tmp_path / "synthetic.wav"
    controller._voice_recorder.state = "recorded"
    monkeypatch.setattr(controller._local_stt, "ready", lambda: True)

    def transcribe(_):
        calls.append(True)
        assert release.wait(5)
        return "合成转录结果，仅用于验证异步归属。"

    monkeypatch.setattr(controller._local_stt, "transcribe", transcribe)
    controller.transcribeInterviewRecording(LOCAL_STT_ID, False)
    controller.transcribeInterviewRecording(LOCAL_STT_ID, False)
    if switch_question:
        # The shared result guard must reject a different question, even if
        # the decoder was still processing the previous recording.
        controller._interview["question"] = {**controller.interview["question"], "question_id": "q-002"}
    release.set()
    for _ in range(200):
        QTest.qWait(10)
        if not controller.busy:
            break
    assert len(calls) == 1 and not controller.busy
    assert len(results) == (0 if switch_question else 1)
    assert not controller.interview["answer_locked"], "STT must not submit the answer"


@pytest.mark.skipif(not os.environ.get("LLM_LAB_TEST_LOCAL_STT_MODEL_ROOT"), reason="Explicit public model/audio paths required")
@pytest.mark.parametrize("size", [(900, 620), (1280, 800)])
def test_real_local_stt_from_production_page(scene, monkeypatch, size):
    import socket
    from llm_interview_lab.ai.local_transcription import LocalSpeechTranscriber

    window, controller = scene
    controller._local_stt = LocalSpeechTranscriber(Path(os.environ["LLM_LAB_TEST_LOCAL_STT_MODEL_ROOT"]))
    controller._refresh_local_stt_status()
    source = Path(os.environ["LLM_LAB_TEST_LOCAL_STT_AUDIO"])
    # Public Chinese sample stands in for a microphone recording. This test
    # does not capture ambient sound or touch the user's existing Profile.
    _stub_dictation_capture(controller, monkeypatch, source)
    controller.stateChanged.emit()
    def unexpected_network(*args, **kwargs):
        raise AssertionError("Local STT must not open a connection or load an API Key")
    monkeypatch.setattr(socket.socket, "connect", unexpected_network)
    monkeypatch.setattr("llm_interview_lab.ai.credentials.KeyringCredentialStore.load", unexpected_network)
    window.resize(*size)
    if size[0] == 900:
        window.setProperty("displayFontScaleOverride", 1.25)
    answer = _find(window, "interviewAnswerEditor")
    answer.setProperty("text", "先保留这句已输入的回答。")
    _click(window, _find(window, "toggleInterviewVoice"))
    QTest.qWait(150)
    assert controller.interviewVoice["state"] == "recording"
    combo = _find(window, "interviewVoiceConnection")
    assert combo.property("currentValue") == "local-sensevoice"
    assert not _find(window, "interviewVoiceRemoteConsent").isVisible()
    button = _find(window, "finishInterviewDictation")
    assert button.isEnabled() and _within_window(window, button)
    _capture(window, f"local-stt-ready-{size[0]}")
    started = time.perf_counter()
    _click(window, button)
    assert controller.interviewVoice["transcription_state"] == "transcribing"
    assert not button.isVisible()
    assert not _find(window, "toggleInterviewVoice").isVisible()
    for _ in range(300):
        QTest.qWait(30)
        # Unlike app.exec(), QTest.qWait repeatedly holds the Python GIL.
        # Let the cold native-module imports on the worker thread progress.
        time.sleep(0.01)
        if not controller.busy:
            break
    assert controller.interviewVoice["transcription_state"] == "transcribed", controller.interviewVoice
    answer = _find(window, "interviewAnswerEditor")
    assert "早上9点至下午5点" in answer.property("text")
    assert answer.property("text").startswith("先保留这句已输入的回答。\n")
    assert _find(window, "interviewVoiceState").property("text") == "已添加到回答框"
    assert not answer.property("readOnly") and not controller.interview["answer_locked"]
    assert controller._voice_recorder.path.read_bytes() == source.read_bytes()
    print(f"LOCAL_STT_QML width={size[0]} seconds={time.perf_counter() - started:.2f}")
    _capture(window, f"local-stt-transcribed-{size[0]}")


def test_corrected_coding_selection_opens_editor_and_shows_notice(scene):
    window, controller = scene
    window.resize(1080, 680)
    _enter_coding_round(controller, "AI-INVENTED-404")
    assert controller.interview["coding_selection_corrected"] is True
    notice = _find(window, "interviewCodingSelectionNotice")
    assert notice.isVisible() and "改选" in notice.property("text")
    assert notice.property("contentHeight") <= notice.height() + 1
    assert controller.interview["question"]["source"]["id"] in controller.service.catalog.problems
    _capture(window, "coding-corrected-question")
    _click(window, _find(window, "toggleInterviewCodingPrompt"))
    assert _find(window, "interviewCodingEditor").isVisible()
    assert controller.interview["coding_text"]
    _capture(window, "coding-corrected-editor")


@pytest.mark.parametrize("size,theme", [
    ((900, 620), "dark"), ((1080, 680), "light"),
    ((1280, 800), "dark"), ((1440, 900), "light"),
])
def test_connections_compact_rows_align_and_actions_work(scene, monkeypatch, size, theme):
    window, controller = scene
    monkeypatch.setattr("llm_interview_lab.ai.credentials.KeyringCredentialStore.save",
                        lambda *args: "synthetic-key-reference")
    assert controller.saveConnection("layout-api", "deepseek", "synthetic-model", "DeepSeek · 布局验收", "", "synthetic-key", "none")
    controller.navigate("connections")
    controller.setTheme(theme)
    window.resize(*size)
    if size[0] == 900:
        window.setProperty("displayFontScaleOverride", 1.25)
    window.findChild(QObject, "globalToast").setProperty("visible", False)
    QTest.qWait(150)
    saved = _find(window, "savedConnectionCard")
    codex = _find(window, "codexConnectionCard")
    notice = _find(window, "localTrainingNotice")
    assert abs(saved.width() - codex.width()) <= 1
    assert abs(saved.mapToScene(QPointF()).x() - codex.mapToScene(QPointF()).x()) <= 1
    assert codex.mapToScene(QPointF()).y() >= saved.mapToScene(QPointF(0, saved.height())).y() + 8
    assert notice.height() < 70, "Local availability is a small notice, not an empty status card"
    assert codex.height() < 220
    for card in (saved, codex):
        for item in _items(card):
            if item.isVisible() and item.property("text"):
                start = item.mapToItem(card, QPointF())
                end = item.mapToItem(card, QPointF(item.width(), item.height()))
                assert start.x() >= 0 and start.y() >= 0
                assert end.x() <= card.width() + 1 and end.y() <= card.height() + 1
    assert _within_window(window, codex)
    assert _within_window(window, notice)
    _capture(window, f"connections-compact-{size[0]}-{theme}")
    _click(window, _find(window, "openCodexModelSettings"))
    assert controller.currentPage == "settings"


def test_connections_found_codex_keeps_connect_and_model_actions(scene, monkeypatch):
    window, controller = scene
    assert controller.saveConnection("layout-local", "ollama", "synthetic-model", "布局验收连接", "http://localhost:11434", "", "")
    controller._codex_available = True  # Explicit discovery fixture; no real Codex login or API call.
    controller.aiStateChanged.emit()
    calls = []
    monkeypatch.setattr(controller, "connectCodex", calls.append)
    controller.navigate("connections")
    window.resize(900, 620)
    window.setProperty("displayFontScaleOverride", 1.25)
    window.findChild(QObject, "globalToast").setProperty("visible", False)
    QTest.qWait(150)
    connect = _find(window, "connectCodexInterviewer")
    model = _find(window, "openCodexModelSettings")
    refresh = _find(window, "refreshCodexConnection")
    for button in (connect, model, refresh):
        assert button.isVisible() and _within_window(window, button)
    assert model.property("text") == "模型与推理强度"
    _capture(window, "connections-codex-discovery-fixture-900")
    _click(window, connect)
    assert calls == ["interviewer"]
    _click(window, model)
    assert controller.currentPage == "settings"


def test_material_refresh_keeps_tested_connection_but_not_across_profiles(scene, monkeypatch, tmp_path):
    from llm_interview_lab.ai.base import ConnectionResult
    from llm_interview_lab.ai.connections import save_connection
    from llm_interview_lab.workspace import init_profile

    class Provider:
        async def test_connection(self):
            return ConnectionResult(True, "Synthetic test succeeded", 1)

    monkeypatch.setattr("llm_interview_lab.desktop.controller.create_chat_provider", lambda *args, **kwargs: Provider())
    window, controller = scene
    assert controller.saveConnection("local-main", "ollama", "synthetic-model", "本地面试", "http://localhost:11434", "", "")
    controller.testConnection("local-main")
    for _ in range(60):
        QTest.qWait(20)
        time.sleep(0.005)
        if not controller.busy:
            break
    assert controller.connections[0]["ready"] is True
    material = tmp_path / "synthetic-resume.txt"
    material.write_text("合成材料，仅用于验证界面刷新，不会发送给 AI。", encoding="utf-8")
    assert controller.addMaterial(str(material), "resume", "本地材料", False)
    assert controller.connections[0]["ready"] is True
    controller.navigate("connections")
    QTest.qWait(50)
    assert _find(window, "globalAiStatus").property("text") == "AI 服务就绪"

    other = "connection-other-" + uuid4().hex[:8]
    init_profile(controller.repo_root, other)
    save_connection(controller.repo_root, other, connection_id="local-main", provider_id="ollama",
                    model="synthetic-model", display_name="本地面试", base_url="http://localhost:11434")
    assert controller.switchProfile(other)
    assert controller.connections[0]["ready"] is False


@pytest.mark.parametrize("with_material", [False, True])
def test_restarted_profile_starts_from_form_with_saved_key(controller, monkeypatch, tmp_path, with_material):
    from llm_interview_lab.ai.base import ChatEvent, ConnectionResult
    from llm_interview_lab.ai.credentials import KeyringCredentialStore

    secrets, probes, conversations = {}, [], []
    class Keyring:
        def set_password(self, service, reference, secret): secrets[reference] = secret
        def get_password(self, service, reference): return secrets.get(reference)
    store = KeyringCredentialStore(Keyring())
    monkeypatch.setattr("llm_interview_lab.ai.connections.KeyringCredentialStore", lambda: store)
    monkeypatch.setattr("llm_interview_lab.desktop.controller.KeyringCredentialStore", lambda: store)
    assert controller.saveConnection("deepseek-main", "deepseek", "deepseek-v4-flash", "DeepSeek", "", "synthetic-stored-key", "none")
    if with_material:
        source = tmp_path / "synthetic-resume.txt"
        source.write_text("合成简历：独立完成偏好数据去重练习；目标是后训练实习。", encoding="utf-8")
        assert controller.addMaterial(str(source), "resume", "合成简历", True)
    controller.finishInterview()
    previous_interview = controller.interview["interview_id"]
    profile = controller.profileId
    controller.shutdown()

    # Real controller restoration, same settings + data. No saveConnection or
    # direct start call is permitted after this point.
    restored = AppController(controller.repo_root, log_root=tmp_path / "restart-logs")
    assert restored.profileId == profile and not restored.onboardingRequired
    assert restored.connections[0]["ready"] is False
    skill = next(iter(restored.service.roles.roles["post_training_engineer"].skill_weights))
    class Provider:
        async def test_connection(self):
            probes.append(True)
            return ConnectionResult(True, "synthetic connection", 1)
        async def stream_chat(self, messages, *, json_mode=False):
            assert json_mode is True
            conversations.append(messages)
            question = restored.interview["question"]
            yield ChatEvent("delta", text=json.dumps({
                "scores": {name: 3 for name in question["rubric"]["dimensions"]},
                "evidence": "候选人说明做过偏好数据去重练习，希望应聘后训练实习，尚未展开项目细节。", "confidence": "medium", "fatal_issues": [],
                "next_stage": "experience", "follow_up": "先聊聊这次去重练习，你自己负责了哪一部分？",
                "next_skill_ids": [skill], "coding_problem_id": "",
            }))
    def provider(config, *, api_key):
        assert api_key == "synthetic-stored-key"
        return Provider()
    monkeypatch.setattr("llm_interview_lab.desktop.controller.create_chat_provider", provider)
    engine = QQmlApplicationEngine()
    errors = []
    engine.warnings.connect(lambda values: errors.extend(v.toString() for v in values))
    engine.rootContext().setContextProperty("backend", restored)
    engine.load(QUrl.fromLocalFile(str(QML)))
    assert engine.rootObjects(), errors
    window = engine.rootObjects()[0]
    window.resize(1080, 680)
    window.show()
    try:
        restored.navigate("connections")
        QTest.qWait(100)
        assert _find(window, "savedConnectionCard").isVisible()
        assert _within_window(window, _find(window, "editConnection"))
        assert not _find(window, "connectionForm").isVisible()
        assert "重启后" in _find(window, "savedConnectionKeyStatus").property("text")
        _capture(window, "saved-key-after-restart")
        restored.navigate("interview")
        QTest.qWait(100)
        _click(window, _find(window, "configureAnotherInterview"))
        _find(window, "interviewAiModeSelector").setProperty("currentIndex", 1)
        _find(window, "interviewDifficultySelector").setProperty("currentIndex", 2)
        _find(window, "interviewUseMaterials").setProperty("checked", with_material)
        _find(window, "interviewMaterialConsent").setProperty("checked", with_material)
        assert not _find(window, "interviewUseAdditionalMaterial").property("checked")
        QTest.qWait(80)
        start = _find(window, "startConfiguredInterview")
        assert start.isEnabled() and _within_window(window, start)
        _click(window, start)
        for _ in range(150):
            QTest.qWait(10)
            time.sleep(0.005)
            if window.findChild(QObject, "personalizedInterviewContextDialog").property("visible"):
                break
        assert probes == [True], restored.connectionError
        confirm = _find(window, "confirmInterviewSetupContext")
        assert confirm.isVisible() and confirm.isEnabled()
        _capture(window, "restart-setup-context-with-material" if with_material else "restart-setup-context")
        _click(window, confirm)
        QTest.qWait(120)
        assert restored.interview["interview_id"] != previous_interview
        assert restored.interview["question"]["question_id"] == "q-001"
        assert restored.interview["connection_id"] == "deepseek-main"
        assert bool(restored.interview["material_refs"]) == with_material
        answer = _find(window, "interviewAnswerEditor")
        answer.forceActiveFocus()
        event = QInputMethodEvent()
        event.setCommitString("我做过偏好数据去重练习，希望应聘后训练实习。")
        QCoreApplication.sendEvent(answer, event)
        _click(window, _find(window, "lockInterviewAnswer"))
        for _ in range(150):
            QTest.qWait(10)
            time.sleep(0.005)
            if not restored.busy: break
        assert restored.interview["question"]["question_id"] == "q-002", restored.interview.get("ai_error")
        assert len(conversations) == 1 and probes == [True]
        assert not errors
    finally:
        window.close()
        restored.shutdown()
        engine.deleteLater()
        QCoreApplication.sendPostedEvents()
        QCoreApplication.processEvents()


def test_missing_interview_prompt_is_inline_and_retryable(scene, monkeypatch):
    window, controller = scene
    controller.finishInterview()
    QTest.qWait(80)
    _click(window, _find(window, "configureAnotherInterview"))
    _find(window, "interviewAiModeSelector").setProperty("currentIndex", 2)
    context = controller.service.dynamic_interview_context
    def missing(*args, **kwargs):
        raise FileNotFoundError("coach/prompts/dynamic-interviewer.md")
    monkeypatch.setattr(controller.service, "dynamic_interview_context", missing)
    _click(window, _find(window, "startConfiguredInterview"))
    assert controller.interviewPlanPreview["error_code"] == "PUBLIC_ASSETS_MISSING"
    notice = _find(window, "dynamicInterviewError")
    assert notice.isVisible() and "重新启动" in notice.property("text")
    assert "操作未完成" not in notice.property("text")
    assert _within_window(window, notice)
    assert _within_window(window, _find(window, "startConfiguredInterview"))
    _capture(window, "missing-prompt-actionable-error")
    monkeypatch.setattr(controller.service, "dynamic_interview_context", context)
    _click(window, _find(window, "startConfiguredInterview"))
    assert _find(window, "confirmInterviewSetupContext").isVisible()


def test_saved_key_form_preserves_replaces_and_confirms_deletion(scene, monkeypatch):
    from llm_interview_lab.ai.base import ConnectionResult
    from llm_interview_lab.ai.credentials import KeyringCredentialStore
    secrets, used_keys = {}, []
    class Keyring:
        def set_password(self, service, reference, secret): secrets[reference] = secret
        def get_password(self, service, reference): return secrets.get(reference)
        def delete_password(self, service, reference): secrets.pop(reference, None)
    store = KeyringCredentialStore(Keyring())
    monkeypatch.setattr("llm_interview_lab.ai.connections.KeyringCredentialStore", lambda: store)
    monkeypatch.setattr("llm_interview_lab.desktop.controller.KeyringCredentialStore", lambda: store)
    class Provider:
        async def test_connection(self): return ConnectionResult(True, "synthetic success", 1)
    def provider(config, *, api_key):
        used_keys.append(api_key)
        return Provider()
    monkeypatch.setattr("llm_interview_lab.desktop.controller.create_chat_provider", provider)
    window, controller = scene
    assert controller.saveConnection("deepseek-main", "deepseek", "deepseek-v4-flash", "DeepSeek", "", "first-test-key", "none")
    controller.navigate("connections")
    QTest.qWait(80)
    _click(window, _find(window, "editConnection"))
    QTest.qWait(150)
    page = _find(window, "connectionsPage")
    secret = _find(window, "connectionSecretField")
    assert secret.property("text") == ""
    assert "留空保留" in secret.property("placeholderText")
    assert _find(window, "savedApiKeyNotice").isVisible()
    _capture(window, "edit-saved-key")
    for key in ("", "replacement-test-key"):
        secret.setProperty("text", key)
        _click(window, _find(window, "saveAndTestConnection"))
        for _ in range(100):
            QTest.qWait(10)
            time.sleep(0.005)
            if not controller.busy: break
        assert secret.property("text") == ""
    assert used_keys == ["first-test-key", "replacement-test-key"]
    assert list(secrets.values()) == ["replacement-test-key"]
    # Adding another service must not silently overwrite the existing Key.
    page.setProperty("contentY", 0)
    QTest.qWait(100)
    _click(window, _find(window, "newConnection"))
    assert page.property("hasSavedKey") is False
    assert controller.connections[0]["connection_id"] == "deepseek-main"
    _click(window, _find(window, "deleteSavedConnection"))
    dialog = window.findChild(QObject, "deleteConnectionDialog")
    assert dialog.property("visible") and secrets
    assert QMetaObject.invokeMethod(dialog, "accept")
    QTest.qWait(100)
    assert controller.connections == [] and not secrets


def test_resaving_same_connection_invalidates_ready_even_with_unchanged_reference(controller):
    assert controller.saveConnection("local-main", "ollama", "synthetic-model", "本地面试", "http://localhost:11434", "", "")
    controller._connections[0].update(ready=True, status="已连接")
    assert controller.saveConnection("local-main", "ollama", "synthetic-model", "本地面试", "http://localhost:11434", "", "")
    assert controller.connections[0]["ready"] is False


@pytest.mark.parametrize("size", [(900, 620), (1080, 680), (1280, 800), (1440, 900)])
def test_coding_actions_stay_visible_while_reading_question(scene, size):
    window, controller = scene
    window.resize(*size)
    _enter_coding_round(controller)
    viewport = _find(window, "interviewQuestionScroll").property("contentItem")
    for theme, scale in (("dark", 1.25), ("light", 1.0)):
        controller.setTheme(theme)
        window.setProperty("displayFontScaleOverride", scale)
        for show_code in (False, True):
            if show_code:
                _click(window, _find(window, "toggleInterviewCodingPrompt"))
            viewport.setProperty("contentY", 0)
            QTest.qWait(80)
            for name in ("runInterviewGrader", "runInterviewScript", "submitInterviewCode", "toggleInterviewCodingPrompt"):
                assert _within_window(window, _find(window, name)), name
            status = _find(window, "interviewCodingStatus")
            assert status.property("contentHeight") <= status.height() + 1
            assert viewport.height() > 130
            _capture(window, f"coding-{'editor' if show_code else 'question'}-{size[0]}-{theme}")
        _click(window, _find(window, "toggleInterviewCodingPrompt"))


def test_edit_saved_connection_reveals_form(scene):
    window, controller = scene
    window.resize(900, 620)
    window.setProperty("displayFontScaleOverride", 1.25)
    assert controller.saveConnection("ux-local", "ollama", "synthetic-model", "本地模型（未测试）",
                                     "http://localhost:11434", "", "low")
    controller.navigate("connections")
    QTest.qWait(150)
    button = _find(window, "editConnection")
    page = button.parentItem()
    while page.property("editingConnectionId") is None:
        page = page.parentItem()
    page.setProperty("contentY", max(0, page.property("contentHeight") - page.height()))
    QTest.qWait(100)
    _click(window, button)
    QTest.qWait(150)
    window.findChild(QObject, "globalToast").setProperty("visible", False)
    _capture(window, "connection-edit-small")
    assert page.property("editingConnectionId") == "ux-local"
    for name in ("saveAndTestConnection", "connectionModelField"):
        control = _find(window, name)
        top = control.mapToItem(page, QPointF()).y()
        assert 0 <= top and top + control.height() <= page.height()
    assert _find(window, "connectionModelField").hasActiveFocus()
    assert _find(window, "saveAndTestConnection").property("variant") == "primary"


def test_saved_connection_card_fits_large_text_and_never_implies_ready(scene):
    window, controller = scene
    window.resize(900, 620)
    window.setProperty("displayFontScaleOverride", 1.25)
    assert controller.saveConnection("ux-local", "ollama", "synthetic-model", "本地模型（尚未测试连接）",
                                     "http://localhost:11434", "", "low")
    controller.navigate("connections")
    QTest.qWait(150)
    card = _find(window, "savedConnectionCard")
    page = card.parentItem()
    while page.property("editingConnectionId") is None:
        page = page.parentItem()
    page.setProperty("contentY", max(0, page.property("contentHeight") - page.height()))
    window.findChild(QObject, "globalToast").setProperty("visible", False)
    QTest.qWait(80)
    pill = _find(window, "savedConnectionStatus")
    assert controller.connections[0]["ready"] is False
    assert pill.property("tone") == page.property("theme").property("muted")
    for item in _items(card):
        if item.isVisible() and (item.property("text") or item.objectName() == "editConnection"):
            assert item.mapToItem(card, QPointF(0, item.height())).y() <= card.height() + 1
    _capture(window, "connection-saved-small")


def test_interview_coding_runs_visible_revision_and_shows_failure(scene):
    window, controller = scene
    window.resize(1080, 680)
    _enter_coding_round(controller)
    # Practice output must never appear as the current interview's evidence.
    controller._test_output = "unrelated Practice PASS"
    controller.stateChanged.emit()
    assert "unrelated" not in _find(window, "interviewCodingOutput").property("text")
    _click(window, _find(window, "toggleInterviewCodingPrompt"))
    editor = _find(window, "interviewCodingEditor")
    editor.forceActiveFocus()
    QTest.keyClick(window, Qt.Key_End, Qt.ControlModifier)
    edit = QInputMethodEvent()
    edit.setCommitString("\n# UAT latest editor revision\n")
    QCoreApplication.sendEvent(editor, edit)
    latest = editor.property("text")
    assert "UAT latest editor revision" in latest
    digest = hashlib.sha256(latest.encode()).hexdigest()
    _click(window, _find(window, "runInterviewGrader"))
    deadline = time.monotonic() + 30
    while controller.busy and time.monotonic() < deadline:
        QTest.qWait(50)
        time.sleep(0.01)
    assert not controller.busy
    assert controller.interview["coding_tested_revision"] == digest
    assert controller.interview["coding_test_status"] == "failed"  # Intentionally incomplete starter, real Grader.
    status = _find(window, "interviewCodingStatus")
    assert "测试未通过" in status.property("text") and digest[:7] in status.property("text")
    assert status.property("tone") == "danger"
    assert "FAILED" in _find(window, "interviewCodingOutput").property("text")
    assert not _find(window, "recordInterviewCodingRound").isVisible()
    assert _find(window, "submitInterviewCode").isEnabled()
    viewport = _find(window, "interviewQuestionScroll").property("contentItem")
    viewport.setProperty("contentY", max(0, viewport.property("contentHeight") - viewport.height()))
    QTest.qWait(100)
    _capture(window, "coding-public-tests-failed")
    editor.forceActiveFocus()
    edit.setCommitString("# modified after test\n")
    QCoreApplication.sendEvent(editor, edit)
    assert not _find(window, "recordInterviewCodingRound").isEnabled()
    assert "代码已修改" in status.property("text")
    # Reload reads only this question's persisted result, not the global output.
    controller._test_output = "unrelated Practice PASS"
    controller._load_interview(controller.interview["interview_id"])
    assert controller.interview["coding_test_status"] == "failed"
    assert "unrelated" not in controller.interview["coding_test_output"]


@pytest.mark.parametrize("mode", ["codex", "provider"])
def test_real_coding_ui_runs_own_example_and_submits_to_interviewer(scene, monkeypatch, mode):
    """Real QML, disk and Python execution; transport replies are synthetic."""
    from llm_interview_lab.ai.base import ChatEvent

    window, controller = scene
    window.resize(1080, 680)
    controller.setTheme("dark" if mode == "codex" else "light")
    if mode == "provider":
        assert controller.saveConnection("coding-api", "ollama", "selected-model", "合成 API", "http://127.0.0.1:11434", "", "high")
        controller.finishInterview()
        preview = controller.dynamicInterviewContextPreview("post_training_engineer", "intern", "hard", "", False)
        controller.startDynamicPersonalizedInterview("post_training_engineer", "intern", "hard", "coding-api", "", False, preview["context_sha256"])
    _enter_coding_round(controller)
    _click(window, _find(window, "toggleInterviewCodingPrompt"))
    editor = _find(window, "interviewCodingEditor")
    code = "def total(xs):\n    return sum(xs)\n# 自己构造数据，不依赖测试框架\nprint(total([2, 3, 4]))\n"
    editor.setProperty("text", code)
    QTest.qWait(80)
    # Button and shortcut execute the same real Python path.
    if mode == "codex":
        _click(window, _find(window, "runInterviewScript"))
    else:
        QTest.keyClick(window, Qt.Key_R, Qt.ControlModifier)
    deadline = time.monotonic() + 10
    while controller.busy and time.monotonic() < deadline:
        QTest.qWait(30)
        time.sleep(0.005)
    run = controller.interview.get("coding_run", {})
    assert run.get("stdout") == "9\n", run
    assert run["exit_code"] == 0
    assert run["submission_sha256"] == hashlib.sha256(code.encode()).hexdigest()
    iid = controller.interview["interview_id"]
    qid = controller.interview["question"]["question_id"]
    assert not controller.service.interview_session(controller.profileId, iid)["coding_evidence"]
    output = _find(window, "interviewCodingOutput")
    assert "退出码：0" in output.property("text") and "9" in output.property("text")
    assert _find(window, "submitInterviewCode").isEnabled()
    # View-only regression setup: this is not a real Grader PASS claim.
    old_sha = run["submission_sha256"]
    controller._interview.update(coding_test_status="passed", coding_tested_revision=old_sha, coding_test_current=True)
    controller.stateChanged.emit()
    code += "# revision B\n"
    editor.setProperty("text", code)
    _click(window, _find(window, "runInterviewScript"))
    deadline = time.monotonic() + 10
    while controller.busy and time.monotonic() < deadline:
        QTest.qWait(30)
    assert controller.interview["coding_test_current"] is False
    assert "测试通过" not in _find(window, "interviewCodingStatus").property("text")
    assert controller.interview["coding_run"]["submission_sha256"] == hashlib.sha256(code.encode()).hexdigest()
    viewport = _find(window, "interviewQuestionScroll")
    panel = _find(window, "interviewCodingOutputPanel")
    assert panel.mapToItem(viewport, QPointF(0, panel.height())).y() <= viewport.height() + 1
    _capture(window, f"self-run-{mode}")

    response = {"scores": {"core_logic": 3, "reasoning": 2, "validation": 3},
                "evidence": "合成评分：return sum(xs) 与样例输出 9 一致，但没有实现完整题面；局部逻辑不能证明整题正确。",
                "confidence": "medium", "fatal_issues": [], "next_stage": "finish",
                "follow_up": "", "coding_problem_id": "", "next_skill_ids": []}
    requests = []
    if mode == "codex":
        class Backend:
            async def start_thread(self, **kwargs):
                return {"thread": {"id": "coding-test-thread"}}
            async def start_turn(self, *args, **kwargs):
                requests.append((args, kwargs))
                return {"turn": {"id": "coding-test-turn"}}
        controller._codex_backend = Backend()
        controller._codex_thread_id = "coding-test-thread"
        controller._codex_thread_mode = "interviewer"
        controller._codex_pump_started = True
        controller._ensure_codex_loop()
    else:
        class Provider:
            async def stream_chat(self, messages):
                requests.append(messages)
                yield ChatEvent("delta", text=json.dumps(response))
        def provider(config, **kwargs):
            assert config.model == "selected-model" and config.reasoning_effort == "high"
            return Provider()
        monkeypatch.setattr("llm_interview_lab.desktop.controller.create_chat_provider", provider)

    _click(window, _find(window, "submitInterviewCode"))
    QTest.qWait(50)
    assert controller.interview.get("answer_locked") or controller.interview.get("question") is None
    for _ in range(200):
        QTest.qWait(10)
        time.sleep(0.005)
        if requests and (mode == "provider" and not controller.busy or controller._codex_interview_turn_id == "coding-test-turn"):
            break
    assert len(requests) == 1, controller.interview.get("ai_error")
    if mode == "codex":
        assert editor.property("readOnly")
        assert not controller.submitInterviewCode(code, "codex", False)
        sent = requests[0][0][1]
        assert requests[0][1]["output_schema"]["properties"]["next_stage"]["enum"] == ["finish"]
        for method, extra in (("turn/started", {}), ("item/agentMessage/delta", {"delta": json.dumps(response)}),
                              ("turn/completed", {"status": "completed"})):
            controller._handle_codex_event(CodexEvent(method, {"turnId": "coding-test-turn", **extra}))
            QCoreApplication.processEvents()
    else:
        sent = str(requests[0])
    assert "core_logic" in sent and "self_run" in sent and "不等于核心逻辑全错" in sent
    QTest.qWait(100)
    assert controller.interview.get("question") is None, controller.interview.get("ai_error")
    controller.finishInterview()
    final = controller.service.interview_session(controller.profileId, iid)
    assert final["status"] == "completed"
    assert final["assessments"][qid]["source"] == "ai"
    assert final["coding_evidence"] == {}
    assert "退出码 0" in controller.interview["result"]["assessment_evidence"][-1]["coding_execution_summary"]
    _capture(window, f"self-run-report-{mode}")


def test_interview_completion_copy_matches_session_state(scene):
    window, controller = scene
    controller.finishInterview()
    QTest.qWait(100)
    assert not _find(window, "finishInterviewButton").isVisible()
    assert _find(window, "configureAnotherInterview").isVisible()
    assert "选择岗位" not in _find(window, "interviewQuestionPrompt").property("text")
    assert _find(window, "interviewQuestionTitle").property("text") == "本场复盘"
    _capture(window, "interview-finished")


def test_profile_switch_preserves_unsent_interview_answer(scene, tmp_path):
    window, controller = scene
    original_profile = controller.profileId
    other_id = "other-" + uuid4().hex[:10]
    other = AppController(controller.repo_root, profile_id=other_id, log_root=tmp_path / "other-logs")
    try:
        assert other.completeOnboarding(other_id, "post_training_engineer", "intern", "codex", "{}")
        preview = other.dynamicInterviewContextPreview("post_training_engineer", "intern", "hard", "", False)
        other.startDynamicPersonalizedInterview("post_training_engineer", "intern", "hard", "codex", "", False,
                                               preview["context_sha256"])
        assert other.interview["interview_id"] == controller.interview["interview_id"]
    finally:
        other.shutdown()
    editor = _find(window, "interviewAnswerEditor")
    _click(window, editor)
    edit = QInputMethodEvent()
    edit.setCommitString("尚未提交的合成回答，不应带入其他学习档案。")
    QCoreApplication.sendEvent(editor, edit)
    controller.navigate("settings")
    assert not controller.switchProfile(other_id), "Switch must not silently discard or carry over an unsent answer"
    assert controller.profileId == original_profile
    controller.navigate("interview")
    assert "尚未提交" in editor.property("text")
    controller.lockInterviewAnswer(editor.property("text"))
    QTest.qWait(50)
    assert controller.switchProfile(other_id)
    controller.navigate("interview")
    QTest.qWait(50)
    assert editor.property("text") == ""
    assert controller.switchProfile(original_profile)
    controller.navigate("interview")
    QTest.qWait(50)
    assert "尚未提交" in editor.property("text")


@pytest.mark.parametrize("size", [(900, 620), (1280, 800)])
def test_long_toast_grows_without_clipping(scene, size):
    window, controller = scene
    window.resize(*size)
    window.setProperty("displayFontScaleOverride", 1.25)
    controller.toast.emit("当前模型要求更新版本的 Codex，连接成功不代表模型可用。请到设置中选择新版 Codex，或换用当前 Codex 支持的模型，再重新连接。回答已保留。")
    QTest.qWait(200)
    popup = window.findChild(QObject, "globalToast")
    content = popup.property("contentItem")
    assert popup.property("visible")
    assert content.property("contentHeight") <= content.height() + 1
    assert popup.property("height") >= content.property("implicitHeight") + 28
    _capture(window, f"long-error-{size[0]}")


def test_settings_saves_model_and_reasoning_from_the_same_edit(scene):
    window, controller = scene
    controller.setCodexModel("")
    controller.setCodexReasoningEffort("")
    controller.navigate("settings")
    QTest.qWait(100)
    _find(window, "codexModelField").setProperty("text", "selected-model")
    _find(window, "codexReasoningEffort").setProperty("currentIndex", 1)
    button = _find(window, "saveCodexModelPreferences")
    ancestor = button.parentItem()
    while ancestor:
        if ancestor.property("contentY") is not None:
            ancestor.setProperty("contentY", button.mapToItem(ancestor, QPointF()).y() - 50)
        ancestor = ancestor.parentItem()
    QTest.qWait(50)
    _click(window, button)
    assert controller.codexModel == "selected-model"
    assert controller.codexReasoningEffort == "low"
    controller.navigate("home")
    controller.navigate("settings")
    QTest.qWait(50)
    assert _find(window, "codexReasoningEffort").property("currentValue") == "low"


def test_setup_requires_consent_for_resume_and_jd(scene, tmp_path):
    window, controller = scene
    for name, kind in (("resume", "resume"), ("jd", "job_description")):
        source = tmp_path / (name + ".txt")
        source.write_text("合成材料：后训练实习岗位，偏好数据与实验评估。", encoding="utf-8")
        assert controller.addMaterial(str(source), kind, name, True)
    controller.finishInterview()
    QTest.qWait(80)
    _click(window, _find(window, "configureAnotherInterview"))
    _find(window, "interviewAiModeSelector").setProperty("currentIndex", 2)
    _find(window, "interviewUseMaterials").setProperty("checked", True)
    _find(window, "interviewPrimaryMaterial").setProperty("currentIndex", 0)
    _find(window, "interviewUseAdditionalMaterial").setProperty("checked", True)
    _find(window, "interviewAdditionalMaterial").setProperty("currentIndex", 1)
    QTest.qWait(80)
    button = _find(window, "startConfiguredInterview")
    assert not button.isEnabled()
    _find(window, "interviewMaterialConsent").setProperty("checked", True)
    assert button.isEnabled()
    _click(window, button)
    QTest.qWait(100)
    _click(window, _find(window, "confirmInterviewSetupContext"))
    QTest.qWait(100)
    session = controller.service.interview_session(controller.profileId, controller.interview["interview_id"])
    assert session["status"] == "active" and len(session["questions"]) == 1
    assert {ref["kind"] for ref in session["material_refs"]} == {"resume", "job_description"}


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_report_recognizes_qvariant_evidence_as_scored(scene, theme):
    window, controller = scene
    controller.setTheme(theme)
    window.resize(1280, 800)
    interview_id = controller.interview["interview_id"]
    for index, evidence in enumerate((
        "回答描述了独立留出评估和数据去重过程，缺少具体量化结果。",
        "能够区分训练数据与评估数据；需要进一步解释近重复样本的判定阈值。",
        "提出了对照实验和回滚条件，但尚未说明如何区分数据变化与服务异常。",
    )):
        question = controller.interview["question"]
        controller.lockInterviewAnswer("合成回答：先隔离训练与评估数据，再通过对照实验核对效果。")
        controller.service.score_interview(
            controller.profileId, interview_id, question["question_id"],
            {name: 3 for name in question["rubric"]["dimensions"]},
            evidence=evidence, source="ai", confidence="medium",
        )
        if index < 2:
            current = controller.service.interview_session(controller.profileId, interview_id)
            controller.service.append_dynamic_interview_question(
                controller.profileId, interview_id,
                question={"kind": question["kind"], "title": ("数据质量与评估隔离", "上线验证与失败定位")[index],
                          "prompt": "请说明你会如何验证这个结论，以及什么结果会让你改变判断。"},
                context_sha256=current["plan_context_sha256"],
            )
            controller._load_interview(interview_id)
    controller.finishInterview()
    QTest.qWait(80)
    summary = _find(window, "interviewResultSummary").property("text")
    assert "部分证据分数" in summary and "尚未评分" not in summary
    score = _find(window, "interviewResultScore").property("text")
    assert format(controller.interview["result"]["overall_score"], "g") in score
    for size, scale in (((1280, 800), 1.0), ((900, 620), 1.25)):
        window.resize(*size)
        window.setProperty("displayFontScaleOverride", scale)
        QTest.qWait(80)
        viewport = _find(window, "interviewQuestionScroll").property("contentItem")
        viewport.setProperty("contentY", 0)
        rows = [item for item in _items(window.contentItem()) if item.objectName() == "interviewEvidenceRow"]
        assert len(rows) == 3
        assert all(row.width() > 0 and row.height() > 0 for row in rows)
        assert all(a.y() + a.height() <= b.y() for a, b in zip(rows, rows[1:]))
        for row in rows:
            for item in _items(row):
                if item.isVisible() and item.property("text"):
                    assert item.property("contentHeight") <= item.height() + 1
                    assert item.mapToItem(row, QPointF(0, item.height())).y() <= row.height()
        _capture(window, f"report-{size[0]}-{theme}")
        viewport.setProperty("contentY", max(0, viewport.property("contentHeight") - viewport.height()))
        QTest.qWait(50)
        assert rows[-1].mapToItem(viewport, QPointF(0, rows[-1].height())).y() <= viewport.height() + 1
        assert _within_window(window, _find(window, "configureAnotherInterview"))


def test_onboarding_does_not_preview_a_nonexistent_practice_task(qapp, public_repo, tmp_path, monkeypatch):
    monkeypatch.setattr("llm_interview_lab.desktop.controller.QSettings", lambda *args: QSettings(str(tmp_path / "fresh-settings.ini"), QSettings.IniFormat))
    monkeypatch.setattr(AppController, "refreshCodexAvailability", lambda self: None)
    profile = "fresh-" + uuid4().hex[:10]
    controller = AppController(public_repo, profile_id=profile)
    messages = []
    controller.toast.connect(messages.append)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", controller)
    engine.load(QUrl.fromLocalFile(str(QML)))
    window = engine.rootObjects()[0]
    try:
        window.show()
        QTest.qWait(80)
        assert controller.completeOnboarding(profile, "post_training_engineer", "intern", "disabled", "{}")
        QTest.qWait(80)
        assert controller.currentTask.get("problem_id")
        assert not messages, messages
        previous_page = controller.currentPage
        controller.navigate("coach")
        QTest.qWait(80)
        assert controller.currentPage == previous_page
        assert window.findChild(QObject, "coachPage") is None
        assert window.findChild(QObject, "exerciseCoachDrawer") is None
    finally:
        controller.shutdown()
        window.close()
        engine.deleteLater()
        QCoreApplication.sendPostedEvents()


@pytest.mark.parametrize("action", ["stop", "timeout"])
def test_codex_request_can_stop_without_losing_the_locked_answer(scene, action):
    window, controller = scene
    window.resize(900, 620)
    window.setProperty("displayFontScaleOverride", 1.25)
    controller.setTheme("dark")
    controller.lockInterviewAnswer("合成回答：我先划分训练集与验证集，再检查相互之间的数据泄漏。")
    interview_id = controller.interview["interview_id"]
    saved_answer = controller.interview["answer_text"]

    class Transport:
        closed = False
        interrupts = []

        async def start_thread(self, **kwargs):
            return {"thread": {"id": "thread-stop-test"}}

        async def start_turn(self, *args, **kwargs):
            return {"turn": {"id": "turn-stop-test"}}

        async def interrupt(self, thread_id, turn_id):
            self.interrupts.append((thread_id, turn_id))
            controller._codexEventReceived.emit(CodexEvent("turn/completed", {
                "turnId": turn_id, "turn": {"id": turn_id, "status": "interrupted"},
            }))
            return {}

        async def close(self):
            self.closed = True

    backend = Transport()
    controller._codex_backend = backend
    controller._codex_thread_id = "thread-stop-test"
    controller._codex_thread_mode = "interviewer"
    controller._ensure_codex_loop()
    controller.aiStateChanged.emit()
    controller.interviewContextPreview(saved_answer, False)
    assert controller.sendCodexInterviewAnswer(saved_answer, False)
    for _ in range(50):
        QTest.qWait(20)
        if controller._codex_interview_turn_id == "turn-stop-test":
            break
    operation = controller._codex_interview_operation_id
    assert _within_window(window, _find(window, "stopCodexInterviewRequest"))
    _capture(window, f"waiting-900-{action}")
    if action == "stop":
        _click(window, _find(window, "stopCodexInterviewRequest"))
    else:
        controller._expire_codex_interview_turn("old-operation")
        assert controller.busy and controller._codex_backend is backend
        controller._expire_codex_interview_turn(operation)
    for _ in range(50):
        QTest.qWait(20)
        if not controller.busy and (backend.interrupts if action == "stop" else backend.closed):
            break
    assert not controller.busy
    assert controller.interview["question"]["question_id"] == "q-001"
    assert controller.service.interview_answer_text(controller.profileId, interview_id, "q-001") == saved_answer
    assert not controller.service.interview_session(controller.profileId, interview_id)["assessments"]
    assert "回答已保留" in controller.interview["ai_error"]
    assert _within_window(window, _find(window, "lockInterviewAnswer"))
    _capture(window, f"request-{action}-900")
    assert _find(window, "globalAiStatus").property("text") == ("AI 已停止" if action == "stop" else "AI 请求失败")
    if action == "stop":
        assert backend.interrupts == [("thread-stop-test", "turn-stop-test")]
    else:
        assert backend.closed and controller._codex_backend is None


def test_answer_hint_hides_on_focus_ime_and_committed_text(scene):
    window, controller = scene
    controller.setTheme("dark")
    answer = _find(window, "interviewAnswerEditor")
    assert _visible_hints(answer), "An empty, unfocused input should offer a hint"
    _click(window, answer)
    _capture(window, "answer-focused-before-input")
    assert not _visible_hints(answer), "Focusing an input must hide its hint before IME starts"
    event = QInputMethodEvent("hong", [])
    QCoreApplication.sendEvent(answer, event)
    assert answer.property("preeditText") == "hong"
    assert not _visible_hints(answer)
    committed = QInputMethodEvent()
    committed.setCommitString("这是一份合成测试回答。")
    QCoreApplication.sendEvent(answer, committed)
    QCoreApplication.processEvents()
    assert answer.property("text") == "这是一份合成测试回答。"
    assert not _visible_hints(answer)
    assert answer.property("topInset") == 0
    _capture(window, "answer-typed-dark")
    answer.setProperty("text", "")
    answer.setProperty("focus", False)
    QCoreApplication.processEvents()
    assert _visible_hints(answer), "Clearing and leaving the input restores the hint"


def test_question_switch_clears_drafts_without_touching_saved_answer(scene):
    window, controller = scene
    answer = _find(window, "interviewAnswerEditor")
    evidence = _find(window, "interviewEvidenceEditor")
    followup = _find(window, "interviewFollowupEditor")
    draft = "Synthetic answer: held-out evaluation and a rollback threshold."
    answer.setProperty("text", draft)
    evidence.setProperty("text", "Old local evidence draft")
    followup.setProperty("text", "Old local follow-up draft")
    controller.navigate("home")
    controller.navigate("interview")
    QCoreApplication.processEvents()
    assert answer.property("text") == draft
    controller.lockInterviewAnswer(draft)
    interview_id = controller.interview["interview_id"]
    controller.service.score_interview(
        controller.profileId, interview_id, "q-001",
        {key: 3 for key in controller.interview["question"]["rubric"]["dimensions"]},
        evidence="The answer names held-out evaluation and a rollback threshold.",
        source="ai", confidence="medium",
    )
    current = controller.service.interview_session(controller.profileId, interview_id)
    controller.service.append_dynamic_interview_question(
        controller.profileId, interview_id,
        question={"kind": current["questions"][0]["kind"], "title": "合成追问", "prompt": "怎样验证这次改动的实际效果？"},
        context_sha256=current["plan_context_sha256"],
    )
    controller._load_interview(interview_id)
    QTest.qWait(30)
    assert answer.property("text") == ""
    assert evidence.property("text") == ""
    assert followup.property("text") == ""
    session = controller.service.interview_session(controller.profileId, interview_id)
    assert "q-001" in session["answers"] and "q-001" in session["assessments"]
    assert controller.service.interview_answer_text(controller.profileId, interview_id, "q-001") == draft


@pytest.mark.parametrize("size", [(900, 620), (1280, 800)])
def test_ui_single_submit_codex_response_enters_next_question(scene, size):
    window, controller = scene
    window.resize(*size)
    window.setProperty("displayFontScaleOverride", 1.25)
    errors = []
    controller.toast.connect(errors.append)

    class FakeCodex:
        calls = []

        async def start_thread(self, **kwargs):
            return {"thread": {"id": "thread-input-fresh"}}

        async def start_turn(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            return {"turn": {"id": "turn-input-test"}}

    backend = FakeCodex()
    controller._codex_backend = backend
    controller._codex_thread_id = "thread-input-test"
    controller._codex_thread_mode = "interviewer"
    controller._codex_pump_started = True
    controller._ai_status = "Codex 已连接"
    controller._ensure_codex_loop()
    controller.aiStateChanged.emit()
    controller.setTheme("dark")
    answer = _find(window, "interviewAnswerEditor")
    draft = "合成回答：我先测量失败率，再在独立验证集上核对改动效果。"
    answer.setProperty("text", draft)
    _click(window, _find(window, "lockInterviewAnswer"))
    dialog = window.findChild(QObject, "lockInterviewAnswerDialog")
    assert not dialog.property("visible"), "Submitting a dynamic answer must not require a second click"
    assert controller.interview["answer_locked"]
    assert not _find(window, "recordSelfAssessment").isVisible()
    continuation = _find(window, "continueCodexInterview")
    assert not continuation.isVisible(), "No separate continue step for dynamic interviews"
    submit = _find(window, "lockInterviewAnswer")
    pos = submit.mapToScene(QPointF())
    assert 0 <= pos.y() and pos.y() + submit.height() <= window.height()
    viewport = _find(window, "interviewQuestionScroll")
    assert pos.y() >= viewport.mapToScene(QPointF(0, viewport.height())).y()
    preview = window.findChild(QObject, "interviewAnswerContextDialog")
    assert not preview.property("visible"), errors
    assert not submit.isEnabled()
    assert not controller.submitInterviewAnswer(draft, "codex", True), "Double clicks must not send twice"
    for _ in range(30):
        QTest.qWait(20)
        time.sleep(0.01)
        if controller._codex_interview_turn_id == "turn-input-test":
            break
    assert len(backend.calls) == 1
    assert draft in backend.calls[0][0][1]
    assert backend.calls[0][1]["output_schema"]["properties"]["next_stage"]["enum"] == ["experience"]
    result = {
        "scores": {key: 3 for key in controller.interview["question"]["rubric"]["dimensions"]},
        "evidence": "候选人说明了先测量失败率，并使用独立验证集核对改动效果。",
        "confidence": "medium", "fatal_issues": [],
        "follow_up": "你怎样选择验证集，并排除训练数据泄漏？",
        "next_stage": "experience", "coding_problem_id": "",
        "next_skill_ids": [next(iter(controller.service.roles.roles["post_training_engineer"].skill_weights))],
    }
    for method, extra in (
        ("turn/started", {}),
        ("item/agentMessage/delta", {"delta": json.dumps(result)}),
        ("turn/completed", {"status": "completed"}),
    ):
        controller._handle_codex_event(CodexEvent(method, {"turnId": "turn-input-test", **extra}))
        QCoreApplication.processEvents()
    QTest.qWait(80)
    assert controller.interview["question"]["question_id"] == "q-002"
    assert controller.interview["question"]["prompt"] == result["follow_up"]
    assert answer.property("text") == ""
    assert controller.busy is False
    _capture(window, "dynamic-second-question-dark")


def test_single_submit_retries_saved_answer_after_malformed_response(controller):
    captured = []
    async def start_thread(**kwargs):
        return {"thread": {"id": "retry-thread"}}
    async def start_turn(*args, **kwargs):
        captured.append(args)
        return {"turn": {"id": "retry-turn"}}
    from types import SimpleNamespace
    controller._codex_backend = SimpleNamespace(start_thread=start_thread, start_turn=start_turn)
    controller._codex_thread_id = "retry-thread"
    controller._codex_thread_mode = "interviewer"
    controller._codex_pump_started = True
    controller._ensure_codex_loop()
    draft = "合成回答：我负责按用户和语义簇隔离训练评测，避免数据泄漏。"
    assert controller.submitInterviewAnswer(draft, "codex", False)
    for _ in range(60):
        QTest.qWait(10)
        time.sleep(0.01)
        if controller._codex_interview_turn_id == "retry-turn": break
    controller._codex_interview_buffer = '{"follow_up":"missing required fields"}'
    controller._finish_codex_interview_assessment(controller._codex_interview_identity)
    assert "AI_RESPONSE_INVALID" in controller.interview["ai_error"]
    assert "操作未完成" not in controller.interview["ai_error"]
    assert controller.interview["answer_text"] == draft
    assert not controller.busy
    assert controller.submitInterviewAnswer("不能用重试篡改已提交回答", "codex", False)
    for _ in range(60):
        QTest.qWait(10)
        time.sleep(0.01)
        if len(captured) == 2: break
    assert draft in captured[-1][1] and "不能用重试篡改" not in captured[-1][1]
    session = controller.service.interview_session(controller.profileId, controller.interview["interview_id"])
    assert list(session["answers"]) == ["q-001"] and session["assessments"] == {}
    controller._finish_codex_interview_assessment(controller._codex_interview_identity, error="Codex 请求已停止")


def test_single_submit_missing_consent_never_locks_or_sends(scene, monkeypatch):
    window, controller = scene
    key, _ = controller._interview_conversation_consent("codex", True)
    controller._settings.remove(key)  # Old sessions did not grant the conversation scope.
    sent = []
    monkeypatch.setattr(controller, "sendCodexInterviewAnswer", lambda *args: sent.append(args) or True)
    controller._codex_backend = object()
    controller._codex_thread_id = "consent-thread"
    controller._codex_thread_mode = "interviewer"
    controller._codex_pump_started = True
    editor = _find(window, "interviewAnswerEditor")
    editor.setProperty("text", "合成回答：我负责训练数据去重与独立评测。")
    _click(window, _find(window, "lockInterviewAnswer"))
    dialog = window.findChild(QObject, "interviewAnswerContextDialog")
    assert dialog.property("visible")
    assert not controller.interview["answer_locked"] and not sent
    QTest.qWait(150)
    _click(window, _find(window, "confirmInterviewAnswerContext"))
    assert len(sent) == 1 and controller.interview["answer_locked"]
    assert controller._settings.value(key)


def test_single_submit_connects_then_sends_and_cancel_never_sends(controller, monkeypatch):
    connected, sent = [], []
    monkeypatch.setattr(controller, "connectCodex", lambda mode: connected.append(mode))
    monkeypatch.setattr(controller, "sendCodexInterviewAnswer", lambda *args: sent.append(args) or True)
    assert controller.submitInterviewAnswer("合成回答：我负责数据清洗和实验对照。", "codex", False)
    assert connected == ["interviewer"] and controller.busy and not sent
    assert not controller.submitInterviewAnswer("重复点击", "codex", False)
    controller.cancelCodex()
    assert not controller.busy and controller._pending_interview_submission is None
    controller._handle_codex_connect_ready({"backend": object(), "thread_id": "late", "mode": "interviewer"})
    assert not sent
    controller._codex_backend = None
    controller._codex_thread_id = None
    assert controller.submitInterviewAnswer("重试", "codex", False)
    controller._handle_codex_connect_ready({"backend": object(), "thread_id": "current", "mode": "interviewer"})
    assert len(sent) == 1 and sent[0][0] == controller.interview["answer_text"]
    assert not controller.busy


def test_single_submit_save_failure_keeps_editor_and_never_sends(scene, monkeypatch):
    window, controller = scene
    editor = _find(window, "interviewAnswerEditor")
    editor.setProperty("text", "合成未保存回答：数据清洗和训练评测隔离。")
    def fail(*args, **kwargs):
        raise PermissionError("synthetic save denied")
    monkeypatch.setattr(controller.service, "answer_interview", fail)
    _click(window, _find(window, "lockInterviewAnswer"))
    assert editor.property("text") == "合成未保存回答：数据清洗和训练评测隔离。"
    assert not controller.interview["answer_locked"] and not controller.busy
    assert "ANSWER_SAVE_FAILED" in controller.interview["ai_error"]
    assert controller._pending_interview_submission is None


def test_interview_send_preconditions_show_inline_action_not_generic_toast(controller):
    errors = []
    controller.toast.connect(errors.append)
    controller.lockInterviewAnswer("合成回答：我负责数据清洗与独立评测，下一步解释验证方法。")
    assert not controller.sendCodexInterviewAnswer("", False)
    assert "Codex 尚未连接" in controller.interview["ai_error"]
    assert "INTERVIEW_REQUEST_FAILED" in controller.interview["ai_error"]
    assert not errors
    controller._codex_thread_mode = "coach"
    assert not controller.sendCodexInterviewAnswer("", False)
    assert "面试官模式" in controller.interview["ai_error"]
    assert "操作未完成" not in controller.interview["ai_error"]
    assert not errors


def test_single_submit_provider_preserves_selected_connection_and_advances(controller, monkeypatch):
    from llm_interview_lab.ai.base import ChatEvent
    assert controller.saveConnection("local-first", "ollama", "unused-model", "未选择服务", "http://127.0.0.1:11434", "", "low")
    assert controller.saveConnection("local-selected", "ollama", "selected-model", "所选服务", "http://127.0.0.1:11434", "", "high")
    controller.finishInterview()
    preview = controller.dynamicInterviewContextPreview("post_training_engineer", "intern", "hard", "", False)
    controller.startDynamicPersonalizedInterview("post_training_engineer", "intern", "hard", "local-selected", "", False, preview["context_sha256"])
    assert controller.interview["connection_id"] == "local-selected"
    calls = []
    response = {
        "scores": {d: 3 for d in controller.interview["question"]["rubric"]["dimensions"]},
        "evidence": "合成测试：回答明确提到数据去重和按用户隔离训练评测。", "confidence": "medium", "fatal_issues": [],
        "follow_up": "你如何核对按用户隔离后不存在语义重复？", "next_stage": "experience", "coding_problem_id": "",
        "next_skill_ids": [next(iter(controller.service.roles.roles["post_training_engineer"].skill_weights))],
    }
    class Provider:
        async def stream_chat(self, messages):
            calls.append(messages)
            yield ChatEvent("delta", text=json.dumps(response))
    configs = []
    def provider(config, **kwargs):
        configs.append(config)
        return Provider()
    monkeypatch.setattr("llm_interview_lab.desktop.controller.create_chat_provider", provider)
    assert controller.submitInterviewAnswer("我负责数据去重，并按用户隔离训练和评测数据。", "local-selected", False)
    for _ in range(150):
        QTest.qWait(10)
        time.sleep(0.01)
        if not controller.busy: break
    assert controller.interview["question"]["question_id"] == "q-002", controller.interview.get("ai_error")
    assert len(calls) == 1 and configs[0].model == "selected-model" and configs[0].reasoning_effort == "high"
    controller._load_interview(controller.interview["interview_id"])
    assert controller.interview["connection_id"] == "local-selected"
    assert next(c for c in controller.connections if c["connection_id"] == "local-selected")["ready"] is True


def test_single_submit_rejects_revoked_material_and_retains_scene_consent(controller, tmp_path, monkeypatch):
    from llm_interview_lab.materials import set_material_ai_access
    path = tmp_path / "synthetic-resume.txt"
    path.write_text("合成简历：我负责 DPO 数据清洗，没有论文。", encoding="utf-8")
    assert controller.addMaterial(str(path), "resume", "合成简历", True)
    mid = controller.materials[0]["id"]
    controller.finishInterview()
    preview = controller.dynamicInterviewContextPreview("post_training_engineer", "intern", "hard", mid, True)
    controller.startDynamicPersonalizedInterview("post_training_engineer", "intern", "hard", "codex", mid, True, preview["context_sha256"])
    key, scope = controller._interview_conversation_consent("codex", True)
    controller._settings.sync()
    reopened = QSettings(controller._settings.fileName(), QSettings.IniFormat)
    assert reopened.value(key) == scope, "Scene consent must survive application restart"
    set_material_ai_access(controller.repo_root, controller.profileId, mid, False)
    sent = []
    monkeypatch.setattr(controller, "sendCodexInterviewAnswer", lambda *args: sent.append(args))
    assert not controller.submitInterviewAnswer("我负责 DPO 数据清洗和独立验证。", "codex", True)
    assert "MATERIAL_CONSENT_CHANGED" in controller.interview["ai_error"]
    assert not controller.interview["answer_locked"] and not sent


def test_deepseek_high_real_adapter_ui_retries_then_advances(scene, monkeypatch):
    """Production QML/controller/HTTP parser; SSE and Keyring are isolated doubles."""
    import httpx
    from llm_interview_lab.ai.credentials import KeyringCredentialStore
    from llm_interview_lab.ai.providers import OpenAICompatibleChatProvider

    window, controller = scene
    secrets, requests, clients = {}, [], []
    class Keyring:
        def set_password(self, service, reference, secret): secrets[reference] = secret
        def get_password(self, service, reference): return secrets.get(reference)
    store = KeyringCredentialStore(Keyring())
    monkeypatch.setattr("llm_interview_lab.ai.connections.KeyringCredentialStore", lambda: store)
    monkeypatch.setattr("llm_interview_lab.desktop.controller.KeyringCredentialStore", lambda: store)
    assert controller.saveConnection("deepseek-high", "deepseek", "deepseek-v4-flash", "合成 DeepSeek", "", "test-only-key", "high")
    controller.finishInterview()
    preview = controller.dynamicInterviewContextPreview("post_training_engineer", "intern", "hard", "", False)
    controller.startDynamicPersonalizedInterview("post_training_engineer", "intern", "hard", "deepseek-high", "", False, preview["context_sha256"])
    window.resize(1080, 680)
    controller.setTheme("dark")
    reply = {}

    def respond(request):
        payload = json.loads(request.content)
        requests.append(payload)
        assert payload["model"] == "deepseek-v4-flash" and payload["reasoning_effort"] == "high"
        assert payload["thinking"] == {"type": "enabled"} and "response_format" not in payload
        assert "JSON" in payload["messages"][-1]["content"]
        content = "" if len(requests) == 1 else json.dumps(reply, ensure_ascii=False)
        chunks = [{"choices": [{"delta": {"reasoning_content": "synthetic reasoning, not an answer"}}]},
                  {"choices": [{"delta": {"content": content}, "finish_reason": "stop"}]}]
        return httpx.Response(200, text="\n\n".join("data: " + json.dumps(c) for c in chunks) + "\n\ndata: [DONE]\n\n")

    def client(**kw):
        value = httpx.AsyncClient(transport=httpx.MockTransport(respond), **kw)
        clients.append(value)
        return value

    monkeypatch.setattr("llm_interview_lab.desktop.controller.create_chat_provider",
                        lambda config, **kw: OpenAICompatibleChatProvider(config, client_factory=client, **kw))
    answer = _find(window, "interviewAnswerEditor")
    draft = "合成简历背景：负责偏好数据清洗、GRPO 消融和独立评测。"
    answer.setProperty("text", draft)
    submit = _find(window, "lockInterviewAnswer")
    _click(window, submit)
    deadline = time.monotonic() + 8
    while controller.busy and time.monotonic() < deadline:
        QTest.qWait(20)
        time.sleep(0.005)
    assert "仅返回思考" in controller.interview.get("ai_error", "")
    assert controller.interview["answer_locked"] and answer.property("text") == draft
    assert submit.isEnabled() and "重试" in submit.property("text")
    assert not any(item.isVisible() and "完成测试，再返回" in str(item.property("text") or "")
                   for item in _items(window.contentItem()))
    assert not controller.service.interview_session(controller.profileId, controller.interview["interview_id"])["assessments"]
    _capture(window, "deepseek-high-empty-retry")
    for index in (2, 3):
        reply.update(scores={d: 3 for d in controller.interview["question"]["rubric"]["dimensions"]},
                     evidence="合成回答明确说明个人负责偏好数据清洗，并以独立验证集检查数据泄漏。", confidence="medium", fatal_issues=[],
                     follow_up=f"第 {index} 问：你怎样验证按用户划分没有数据泄漏？", next_stage="experience",
                     coding_problem_id="", next_skill_ids=[next(iter(controller.service.roles.roles["post_training_engineer"].skill_weights))])
        if index == 3:
            answer.setProperty("text", "合成补充：我对分组划分做了重复度检查，保留独立测试集。")
        _click(window, submit)
        deadline = time.monotonic() + 8
        while controller.busy and time.monotonic() < deadline:
            QTest.qWait(20)
            time.sleep(0.005)
        QTest.qWait(80)  # Let the production Qt.callLater editor reset reach the next frame.
        assert controller.interview["question"]["question_id"] == f"q-{index:03d}", controller.interview.get("ai_error")
        assert not controller.interview.get("ai_error") and answer.property("text") == ""
        final = controller.service.interview_session(controller.profileId, controller.interview["interview_id"])
        assert len(final["answers"]) == len(final["assessments"]) == index - 1
    assert len(requests) == 3 and all(c.is_closed for c in clients)
    assert requests[0]["messages"] == requests[1]["messages"], "Retry reuses the saved answer/context"
    _capture(window, "deepseek-high-next-question")


def test_provider_deadline_releases_retry_and_keeps_locked_answer(controller, monkeypatch):
    import asyncio
    import threading
    from llm_interview_lab.ai.base import ChatEvent
    assert controller.saveConnection("deadline-api", "ollama", "synthetic-model", "Synthetic", "http://127.0.0.1:11434", "", "high")
    controller.finishInterview()
    preview = controller.dynamicInterviewContextPreview("post_training_engineer", "intern", "hard", "", False)
    controller.startDynamicPersonalizedInterview("post_training_engineer", "intern", "hard", "deadline-api", "", False, preview["context_sha256"])
    closed = threading.Event()
    class Provider:
        async def stream_chat(self, messages):
            try:
                while True:
                    yield ChatEvent("heartbeat")
                    await asyncio.sleep(0.01)
            finally:
                closed.set()
    monkeypatch.setattr("llm_interview_lab.desktop.controller.create_chat_provider", lambda *a, **kw: Provider())
    monkeypatch.setattr(controller, "_PROVIDER_INTERVIEW_TIMEOUT_SECONDS", 0.05)
    assert controller.submitInterviewAnswer("合成回答：我负责数据划分与独立验证。", "deadline-api", False)
    deadline = time.monotonic() + 5
    while controller.busy and time.monotonic() < deadline:
        QTest.qWait(20)
        time.sleep(0.005)
    assert not controller.busy and closed.is_set()
    assert not controller._interview_provider_operation_id
    assert "等待超时" in controller.interview.get("ai_error", "")
    assert controller.interview["answer_locked"] and controller.interview["question"]["question_id"] == "q-001"
    assert not controller.service.interview_session(controller.profileId, controller.interview["interview_id"])["assessments"]


@pytest.mark.parametrize("mode", ["codex", "provider"])
def test_dynamic_followups_advance_once_without_duplicate_scoring(controller, monkeypatch, mode):
    errors = []
    controller.toast.connect(errors.append)
    interview_id = controller.interview["interview_id"]
    for index in (1, 2):
        question_id = f"q-{index:03d}"
        controller.lockInterviewAnswer("I measured the failure rate and tested a held-out baseline.")
        controller.interviewContextPreview(controller.interview["answer_text"], False)
        result = {
            "scores": {name: 3 for name in controller.interview["question"]["rubric"]["dimensions"]},
            "evidence": "The answer describes measuring failure rates and testing a held-out baseline.",
            "confidence": "medium", "fatal_issues": [],
            "follow_up": f"第 {index + 1} 问：你怎样验证这次改动的效果？",
            "next_stage": "experience", "coding_problem_id": "",
            "next_skill_ids": [next(iter(controller.service.roles.roles["post_training_engineer"].skill_weights))],
        }
        if mode == "codex":
            operation = f"test-followup-{index}"
            identity = (controller.profileId, interview_id, question_id, operation, "codex")
            controller._codex_interview_identity = identity
            controller._codex_interview_operation_id = operation
            controller._codex_interview_buffer = json.dumps(result)
            controller._codex_interview_include_materials = False
            controller._finish_codex_interview_assessment(identity)
        else:
            monkeypatch.setattr(controller, "_background", lambda operation, complete, failed=None: complete(result))
            controller.assessInterviewWithProvider("", "fake-connection", False)
        assert not errors, errors
        assert controller.interview["question"]["question_id"] == f"q-{index + 1:03d}"
        session = controller.service.interview_session(controller.profileId, interview_id)
        assert len(session["questions"]) == index + 1
        assert len(session["assessments"]) == index


@pytest.mark.parametrize("size", [(900, 620), (1080, 680), (1280, 800), (1440, 900)])
def test_answer_geometry_at_supported_sizes(scene, size):
    window, controller = scene
    window.resize(*size)
    for theme, scale in (("light", 1.0), ("dark", 1.0), ("light", 1.25), ("dark", 1.25)):
        controller.setTheme(theme)
        window.setProperty("displayFontScaleOverride", scale)
        QTest.qWait(50)
        answer = _find(window, "interviewAnswerEditor")
        _click(window, answer)
        answer.setProperty("text", "合成测试回答：说明本人完成的工作、实验依据与结果。")
        QCoreApplication.processEvents()
        rectangle = answer.property("cursorRectangle")
        assert answer.property("topInset") == 0
        assert rectangle.y() >= answer.property("topPadding") - 1
        assert rectangle.bottom() < answer.height()
        assert answer.width() >= 260
        assert not _visible_hints(answer)
        button = _find(window, "lockInterviewAnswer")
        button_start = button.mapToScene(QPointF(0, 0))
        composer = _find(window, "interviewPhaseGuidance")
        reply_viewport = _find(window, "interviewReplyViewport")
        assert reply_viewport.mapToScene(QPointF(0, reply_viewport.height())).y() <= button_start.y()
        assert button.mapToItem(composer, QPointF(0, button.height())).y() <= composer.height() - 8
        scope = _find(window, "inspectInterviewContext")
        voice = _find(window, "toggleInterviewVoice")
        assert scope.mapToScene(QPointF(scope.width(), 0)).x() <= voice.mapToScene(QPointF()).x()
        assert voice.mapToScene(QPointF(voice.width(), 0)).x() <= button_start.x()
        assert button.isEnabled()
        assert button.property("resolvedBackground") != button.property("resolvedForeground")
        title = _find(window, "interviewQuestionTitle")
        prompt = _find(window, "interviewQuestionPrompt")
        assert title.property("contentHeight") <= title.height() + 1
        assert prompt.property("contentHeight") <= prompt.height() + 1
        assert title.mapToScene(QPointF(0, title.height())).y() <= prompt.mapToScene(QPointF()).y()
        reading = _find(window, "interviewQuestionScroll")
        assert reading.property("clip") and reply_viewport.property("clip")
        assert reading.mapToScene(QPointF(0, reading.height())).y() <= composer.mapToScene(QPointF()).y()
        for view, name in ((reading, "interviewQuestionScrollBar"), (reply_viewport, "interviewReplyScrollBar")):
            bar = _find(window, name)
            assert bar.mapToItem(view, QPointF(bar.width(), 0)).x() == pytest.approx(view.width())
            assert bar.height() == pytest.approx(view.property("availableHeight"))
        _capture(window, f"interview-{size[0]}x{size[1]}-{theme}-{scale}")
        viewport = _find(window, "interviewQuestionScroll")
        flickable = viewport.property("contentItem")
        # The primary action stays below the question viewport, even when a
        # long question or enlarged text requires scrolling the reading area.
        assert button_start.y() >= viewport.mapToScene(QPointF(0, viewport.height())).y()
        flickable.setProperty("contentY", max(0, flickable.property("contentHeight") - flickable.height()))
        QTest.qWait(30)
        point = button.mapToScene(QPointF(button.width() / 2, button.height() / 2))
        assert 0 <= point.x() - button.width() / 2
        assert point.x() + button.width() / 2 <= window.width()
        assert 0 <= point.y() - button.height() / 2
        assert point.y() + button.height() / 2 <= window.height()
        if size == (900, 620):
            _capture(window, f"interview-900x620-{theme}-{scale}-submit")
        flickable.setProperty("contentY", 0)


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_conversation_long_answer_scrolls_without_moving_submit(scene, theme):
    window, controller = scene
    window.resize(900, 620)
    window.setProperty("displayFontScaleOverride", 1.25)
    controller.setTheme(theme)
    answer = _find(window, "interviewAnswerEditor")
    reading = _find(window, "interviewQuestionScroll")
    prompt = _find(window, "interviewQuestionPrompt")
    prompt.setProperty("text", "请根据刚才提到的评估过程，说明怎样避免数据泄漏，以及你会如何核对上线前后的结果。\n\n" * 12)
    answer.setProperty("text", "合成回答：我先按用户和时间划分数据，再对语义相近的样本去重。\n" * 40)
    QTest.qWait(100)
    _click(window, answer)
    QTest.keyClick(window, Qt.Key_End, Qt.ControlModifier)
    QTest.qWait(80)
    viewport = _find(window, "interviewReplyViewport")
    flickable = viewport.property("contentItem")
    cursor = answer.property("cursorRectangle")
    cursor_bottom = answer.mapToItem(viewport, cursor.bottomRight()).y()
    assert 0 < cursor_bottom <= viewport.height() + 1, "Typing cursor must follow the independently scrolling answer"
    assert flickable.property("contentY") > 0
    assert viewport.height() <= 180
    button = _find(window, "lockInterviewAnswer")
    button_y = button.mapToScene(QPointF()).y()
    assert _within_window(window, button)
    assert not _visible_hints(answer)
    _capture(window, f"long-answer-900-{theme}")
    reading.property("contentItem").setProperty("contentY", 200)
    QTest.qWait(30)
    assert button.mapToScene(QPointF()).y() == button_y
    QTest.keyClick(window, Qt.Key_Home, Qt.ControlModifier)
    QTest.qWait(50)
    assert flickable.property("contentY") == 0
    assert answer.property("text").count("合成回答") == 40


@pytest.mark.parametrize("size", [(900, 620), (1280, 800)])
def test_context_dialog_long_labels_scale_without_overlap(scene, size):
    window, controller = scene
    window.resize(*size)
    window.setProperty("displayFontScaleOverride", 1.25)
    controller.setTheme("dark")
    controller.lockInterviewAnswer("合成回答：在独立验证集上评估，不能使用训练数据证明效果。")
    page = _find(window, "interviewAnswerEditor")
    while page.property("aiPreview") is None:
        page = page.parentItem()
    parts = [
        {"id": "policy", "selected": True},
        {"id": "candidate_answer", "selected": True},
        {"id": "material:synthetic", "label": "授权材料：合成测试材料 · 后训练实习项目与评测记录（多行长标题用于排版验证，不含真实材料）" * 2,
         "selected": True, "sensitive": True, "sha256": "a" * 64},
    ]
    for property_name, dialog_name, list_name in (
        ("aiPreview", "interviewAnswerContextDialog", "interviewAnswerContextList"),
        ("planContext", "personalizedInterviewContextDialog", "interviewSetupContextList"),
    ):
        page.setProperty(property_name, {"parts": parts, "estimated_tokens": 1500})
        dialog = window.findChild(QObject, dialog_name)
        QMetaObject.invokeMethod(dialog, "open")
        QTest.qWait(180)
        listing = _find(window, list_name)
        rows = sorted((item for item in _items(listing) if item.objectName() == "contextPreviewRow"), key=lambda item: item.y())
        assert len(rows) == 3
        for row in rows:
            labels = [item for item in _items(row) if item.objectName() in ("contextPreviewLabel", "contextPreviewDetail") and item.isVisible()]
            for label in labels:
                assert label.property("contentHeight") <= label.height() + 1
                assert label.mapToItem(row, QPointF(0, label.height())).y() <= row.height()
            if len(labels) == 2:
                assert labels[0].mapToScene(QPointF(0, labels[0].height())).y() <= labels[1].mapToScene(QPointF()).y()
        assert all(a.y() + a.height() <= b.y() for a, b in zip(rows, rows[1:]))
        assert dialog.property("height") <= window.height()
        button_name = "confirmInterviewAnswerContext" if property_name == "aiPreview" else "confirmInterviewSetupContext"
        button = _find(window, button_name)
        background = dialog.property("background")
        assert button.mapToItem(background, QPointF(0, button.height())).y() <= background.height() - 12
        _capture(window, f"context-{property_name}-{size[0]}-dark-1.25")
        listing.setProperty("contentY", max(0, listing.property("contentHeight") - listing.height()))
        QTest.qWait(50)
        last = rows[-1]
        bottom = last.mapToItem(listing, QPointF(0, last.height())).y()
        assert bottom <= listing.height() + 1, "The complete material row must be reachable by scrolling"
        QMetaObject.invokeMethod(dialog, "reject")
        QTest.qWait(150)


def test_composer_tools_preserve_the_answer_and_never_send_on_inspection(scene):
    window, controller = scene
    window.resize(900, 620)
    window.setProperty("displayFontScaleOverride", 1.25)
    answer = _find(window, "interviewAnswerEditor")
    draft = "合成回答：我负责数据去重和独立评估。"
    answer.setProperty("text", draft)
    _click(window, _find(window, "inspectInterviewContext"))
    QTest.qWait(80)
    dialog = window.findChild(QObject, "interviewAnswerContextDialog")
    assert dialog.property("visible")
    assert not controller.busy and not controller.interview["answer_locked"]
    QMetaObject.invokeMethod(dialog, "reject")
    QTest.qWait(180)
    _click(window, _find(window, "toggleInterviewVoice"))
    QTest.qWait(100)
    assert _find(window, "interviewVoiceCard").isVisible()
    assert _find(window, "interviewVoiceSettingsScroll").isVisible(), "First-use voice should reveal model setup"
    close = _find(window, "closeInterviewVoiceSettings")
    assert _within_window(window, close)
    _capture(window, "voice-options-900")
    _click(window, close)
    QTest.qWait(100)
    assert not _find(window, "interviewVoiceConnection").isVisible()
    assert answer.property("text") == draft
    assert not controller.busy and not controller.interview["answer_locked"]


def test_interview_removes_details_and_reconfigure_preserves_results(scene):
    window, controller = scene
    assert not any(item.objectName() == "openInterviewSessionInfo" for item in _items(window.contentItem()))
    assert _find(window, "interviewQuestionPosition").property("text") == "第 1 问 · 逐问面试"
    controller.finishInterview()
    QTest.qWait(100)
    previous_id = controller.interview["interview_id"]
    assert _find(window, "interviewConversation").isVisible()
    _click(window, _find(window, "configureAnotherInterview"))
    assert _find(window, "interviewRoleSelector").isVisible()
    back = next(item for item in _items(window.contentItem()) if item.isVisible() and item.property("text") == "返回上一场结果" and hasattr(item, "clicked"))
    back.clicked.emit()
    QTest.qWait(50)
    assert _find(window, "interviewConversation").isVisible()
    assert controller.interview["interview_id"] == previous_id


def test_codex_reuses_interview_thread_until_model_or_material_scope_changes(controller, monkeypatch):
    from dataclasses import replace
    from llm_interview_lab.ai.base import ContextPart
    class Backend:
        threads = []
        turns = []
        async def start_thread(self, **kwargs):
            self.threads.append(kwargs)
            return {"thread": {"id": f"scope-{len(self.threads)}"}}
        async def start_turn(self, thread_id, *args, **kwargs):
            self.turns.append(thread_id)
            return {"turn": {"id": f"turn-{len(self.turns)}"}}
    backend = Backend()
    controller._codex_backend = backend
    controller._codex_thread_id = "connected-interviewer"
    controller._codex_thread_mode = "interviewer"
    controller._codex_pump_started = True
    controller._ensure_codex_loop()
    original_context = controller._confirmed_interview_context
    add_material = [True]
    def preview(include_materials):
        value = original_context(include_materials)
        if add_material[0]:
            value = replace(value, parts=(*value.parts, ContextPart("material:synthetic", "Synthetic", "synthetic", "abc")))
        return value
    monkeypatch.setattr(controller, "_confirmed_interview_context", preview)
    for index in range(4):
        if index == 2: add_material[0] = False
        if index == 3: controller.setCodexModel("changed-model")
        assert controller.submitInterviewAnswer("合成回答：我通过独立验证集和按用户划分避免数据泄漏。", "codex", False)
        for _ in range(80):
            QTest.qWait(10)
            time.sleep(0.005)
            if controller._codex_interview_turn_id == f"turn-{index + 1}": break
        assert len(backend.turns) == index + 1
        result = {"scores": {d: 3 for d in controller.interview["question"]["rubric"]["dimensions"]},
                  "evidence": "合成回答明确说明独立验证集和按用户划分。", "confidence": "medium", "fatal_issues": [],
                  "follow_up": f"请说明第 {index + 1} 次划分如何避免泄漏？", "next_stage": "experience",
                  "coding_problem_id": "", "next_skill_ids": [next(iter(controller.service.roles.roles["post_training_engineer"].skill_weights))]}
        controller._codex_interview_buffer = json.dumps(result)
        controller._finish_codex_interview_assessment(controller._codex_interview_identity)
        assert not controller.busy and not controller.interview.get("ai_error")
    assert backend.turns == ["scope-1", "scope-1", "scope-2", "scope-3"]


def test_deepseek_connection_controls_and_coding_language_are_real(scene, monkeypatch, tmp_path):
    from llm_interview_lab.ai.base import ConnectionResult
    from llm_interview_lab.ai.credentials import KeyringCredentialStore
    saved_secrets, requests = {}, []
    class Keyring:
        def set_password(self, service, reference, secret): saved_secrets[reference] = secret
        def get_password(self, service, reference): return saved_secrets.get(reference)
    store = KeyringCredentialStore(Keyring())
    monkeypatch.setattr("llm_interview_lab.ai.connections.KeyringCredentialStore", lambda: store)
    monkeypatch.setattr("llm_interview_lab.desktop.controller.KeyringCredentialStore", lambda: store)
    class Provider:
        async def test_connection(self): return ConnectionResult(True, "synthetic connection", 12)
    def provider(config, **kwargs):
        requests.append(config)
        return Provider()
    monkeypatch.setattr("llm_interview_lab.desktop.controller.create_chat_provider", provider)
    window, controller = scene
    controller.navigate("connections")
    QTest.qWait(100)
    assert _find(window, "connectionProviderChoice").property("currentText") == "deepseek"
    choices = _find(window, "deepseekModelChoice")
    choices.forceActiveFocus()
    QTest.keyClick(window, Qt.Key_Down)
    QCoreApplication.processEvents()
    field = _find(window, "connectionModelField")
    assert choices.property("currentText") == "deepseek-v4-pro"
    assert field.property("text") == "deepseek-v4-pro"
    efforts = _find(window, "providerReasoningEffort")
    assert efforts.property("currentValue") == "none"
    efforts.forceActiveFocus()
    QTest.keyClick(window, Qt.Key_Down)
    assert efforts.property("currentValue") == "low"
    for size, theme in (((900, 620), "light"), ((1280, 800), "dark")):
        window.resize(*size)
        controller.setTheme(theme)
        QTest.qWait(60)
        assert _within_window(window, _find(window, "saveAndTestConnection"))
        _capture(window, f"deepseek-connections-{theme}")
    _find(window, "connectionSecretField").setProperty("text", "fake-key-for-ui-test")
    _click(window, _find(window, "saveAndTestConnection"))
    for _ in range(60):
        QTest.qWait(10)
        time.sleep(0.005)
        if not controller.busy: break
    assert len(requests) == 1
    assert (requests[0].provider_id, requests[0].model, requests[0].reasoning_effort) == ("deepseek", "deepseek-v4-pro", "low")
    assert _find(window, "connectionSecretField").property("text") == ""
    assert _find(window, "globalAiStatus").property("text") == "AI 服务就绪"
    # A human-readable label is never a connection readiness signal.
    controller._connections[0].update(ready=False, status="已连接")
    controller.stateChanged.emit()
    QCoreApplication.processEvents()
    assert _find(window, "globalAiStatus").property("text") == "No-AI 可用"
    controller.navigate("interview")
    material_path = tmp_path / "synthetic-material.txt"
    material_path.write_text("合成经历：负责偏好数据去重与留出集评估。", encoding="utf-8")
    assert controller.addMaterial(str(material_path), "resume", "合成布局材料", True)
    material_id = controller.materials[0]["id"]
    controller.finishInterview()
    preview = controller.dynamicInterviewContextPreview("post_training_engineer", "intern", "hard", material_id, True)
    controller.startDynamicPersonalizedInterview("post_training_engineer", "intern", "hard", "deepseek-main", material_id, True, preview["context_sha256"])
    QTest.qWait(80)
    connection_choice = _find(window, "interviewActiveProvider")
    consent_choice = _find(window, "includeInterviewMaterialsToggle")
    assert connection_choice.isVisible() and consent_choice.isVisible()
    assert connection_choice.mapToScene(QPointF(0, connection_choice.height()/2)).y() == pytest.approx(consent_choice.mapToScene(QPointF(0, consent_choice.height()/2)).y())
    _capture(window, "composer-aligned-dark")
    _enter_coding_round(controller)
    text = _find(window, "interviewQuestionPrompt")
    assert "sample_id" in text.property("text") and "校验" in text.property("text")
    assert "## Goal" not in text.property("text")
    toggle = _find(window, "toggleInterviewQuestionLanguage")
    # Long task scroll positions do not change the underlying language action.
    toggle.clicked.emit()
    QCoreApplication.processEvents()
    assert "## Goal" in text.property("text")
    toggle.clicked.emit()
    QCoreApplication.processEvents()
    assert "校验" in text.property("text")
    controller.setLanguage("en")
    QCoreApplication.processEvents()
    assert "## Goal" in text.property("text")
    controller.setLanguage("zh-CN")
    QCoreApplication.processEvents()
    assert "校验" in text.property("text")
    _capture(window, "coding-chinese-dark")


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_shell_setup_home_and_settings_have_readable_controls(scene, theme):
    window, controller = scene
    window.resize(1280, 800)
    window.setProperty("displayFontScaleOverride", 1.0)
    controller.setTheme(theme)
    for page_id in ("home", "settings", "progress", "connections"):
        controller.navigate(page_id)
        QTest.qWait(150)
        assert _find(window, page_id + "Page").isVisible()
        assert window.findChild(QObject, "coachPage") is None
        title = _find(window, "shellRouteTitle")
        assert title.width() > 0 and title.height() >= title.property("contentHeight") - 1
        _capture(window, f"{page_id}-1280x800-{theme}")
    controller.navigate("interview")
    controller.finishInterview()
    QTest.qWait(80)
    _click(window, _find(window, "configureAnotherInterview"))
    selector = _find(window, "interviewAiModeSelector")
    selector.setProperty("currentIndex", 2)
    for size in ((900, 620), (1080, 680), (1280, 800), (1440, 900)):
        window.resize(*size)
        window.setProperty("displayFontScaleOverride", 1.25 if size[0] == 900 else 1.0)
        QTest.qWait(100)
        start = _find(window, "startConfiguredInterview")
        pos = start.mapToScene(QPointF())
        assert start.isVisible() and start.isEnabled()
        assert pos.y() >= 0 and pos.y() + start.height() <= window.height()
        assert pos.x() >= 0 and pos.x() + start.width() <= window.width()
        _capture(window, f"setup-{size[0]}x{size[1]}-{theme}")
        viewport = _find(window, "interviewSetupScroll").property("contentItem")
        view = _find(window, "interviewSetupScroll")
        bar = _find(window, "interviewSetupScrollBar")
        assert bar.mapToItem(view, QPointF(bar.width(), 0)).x() == pytest.approx(view.width())
        assert bar.height() == pytest.approx(view.property("availableHeight"))
        viewport.setProperty("contentY", max(0, viewport.property("contentHeight") - viewport.height()))
        QTest.qWait(80)
        materials = _find(window, "interviewUseMaterials")
        assert _within_window(window, materials), "The optional background section remains reachable"
        assert materials.mapToScene(QPointF(0, materials.height())).y() <= start.mapToScene(QPointF()).y()
        if size == (900, 620):
            _capture(window, f"setup-scrolled-900-{theme}")
        viewport.setProperty("contentY", 0)


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_small_home_keeps_text_inside_controls(scene, theme):
    window, controller = scene
    window.resize(900, 620)
    window.setProperty("displayFontScaleOverride", 1.25)
    controller.setTheme(theme)
    controller.navigate("home")
    QTest.qWait(100)
    _capture(window, f"home-900x620-{theme}-1.25")
    for name in ("homeTodayFocus", "homeEvidenceRail"):
        card = _find(window, name)
        for item in _items(card):
            if item.isVisible() and item.property("text") and item.property("contentHeight") is not None:
                assert item.property("contentHeight") <= item.height() + 1, item.property("text")
                assert item.mapToItem(card, QPointF(0, item.height())).y() <= card.height(), item.property("text")


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_home_layout_and_real_entry_points(scene, theme):
    window, controller = scene
    controller.setTheme(theme)
    controller.navigate("home")
    for width, height in ((900, 620), (1080, 680), (1280, 800), (1440, 900)):
        window.resize(width, height)
        window.setProperty("displayFontScaleOverride", 1.25 if width == 900 else 1.0)
        QTest.qWait(120)
        page = _find(window, "homePage")
        page.setProperty("contentY", 0)
        primary = _find(window, "homePrimaryAction")
        assert _within_window(window, primary)
        focus = _find(window, "homeTodayFocus")
        evidence = _find(window, "homeEvidenceRail")
        assert focus.mapToScene(QPointF(0, focus.height())).y() < evidence.mapToScene(QPointF()).y()
        for card in (focus, evidence):
            for item in _items(card):
                if item.isVisible() and item.property("text") and item.property("contentHeight") is not None:
                    assert item.property("contentHeight") <= item.height() + 1, item.property("text")
                    assert item.mapToItem(card, QPointF(item.width(), item.height())).y() <= card.height() + 1
                    assert item.mapToItem(card, QPointF(item.width(), 0)).x() <= card.width() + 1
        assert "Post-Training" not in _find(window, "homeFocusTitle").property("text")
        _capture(window, f"home-polish-{width}x{height}-{theme}")
        page.setProperty("contentY", max(0, page.property("contentHeight") - page.height()))
        QTest.qWait(30)
        assert _within_window(window, _find(window, "homeEvidenceNote"))
        page.setProperty("contentY", 0)
    QTest.qWait(80)
    primary = _find(window, "homePrimaryAction")
    clicks = []
    errors = []
    primary.clicked.connect(lambda: clicks.append(True))
    controller.toast.connect(errors.append)
    assert primary.isEnabled(), (controller.busy, primary.property("busy"))
    _click(window, primary)
    QTest.qWait(120)
    assert clicks, (primary.mapToScene(QPointF()), primary.width(), primary.height())
    assert not errors, errors
    assert controller.currentPage == "interview"
    assert _find(window, "interviewAnswerEditor").isVisible()
    controller.navigate("home")
    QTest.qWait(100)
    _click(window, _find(window, "homeBrowseTraining"))
    QTest.qWait(100)
    assert controller.currentPage == "learn"
    controller.navigate("home")
    QTest.qWait(100)
    _click(window, _find(window, "homeProgressAction"))
    QTest.qWait(100)
    assert _find(window, "progressPage").isVisible()
    controller.finishInterview()
    controller.navigate("home")
    QTest.qWait(80)
    _capture(window, f"home-practice-1440x900-{theme}")
    _click(window, _find(window, "homePrimaryAction"))
    QTest.qWait(100)
    assert controller.currentPage == "exercise"
    assert _find(window, "exerciseEditorFrame").isVisible()
