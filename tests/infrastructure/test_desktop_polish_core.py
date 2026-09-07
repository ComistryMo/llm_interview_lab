"""Scoped clock and recording lifecycle checks; never access a real microphone."""

from collections import Counter
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QCoreApplication, QEvent, QObject, Signal
from PySide6.QtMultimedia import QMediaFormat, QMediaRecorder
from PySide6.QtTest import QTest

from llm_interview_lab.ai.local_transcription import LOCAL_STT_ID
from llm_interview_lab.desktop import voice

# Reuse the production-page fixtures: temporary public repo, synthetic Profile,
# explicit INI QSettings and no Codex discovery, not a second test state model.
from .test_interview_input_runtime import (
    _dictation_model_ready,
    _find,
    _stub_dictation_capture,
    controller,
    public_repo,
    qapp,
    scene,
)


pytestmark = pytest.mark.infrastructure


def _leave_answering(controller, monkeypatch, action):
    if action == "pause":
        assert controller.pauseInterview()
    elif action == "expired":
        def expired(*args):
            raise RuntimeError("role interview time has expired")
        monkeypatch.setattr(controller.service, "current_interview", expired)
        controller.refreshInterviewClock()
    else:
        controller.shutdown()


def test_clock_updates_only_changed_interview_state(controller, monkeypatch):
    counts = Counter()
    controller.stateChanged.connect(lambda: counts.update(["global"]))
    controller.interviewChanged.connect(lambda: counts.update(["interview"]))
    controller.interviewVoiceChanged.connect(lambda: counts.update(["voice"]))
    remaining = controller.interview["remaining_seconds"]
    current = {"question": controller.interview["question"], "remaining_seconds": remaining}
    reads = []

    def authoritative_clock(*args):
        reads.append(args)
        return current

    monkeypatch.setattr(controller.service, "current_interview", authoritative_clock)
    for _ in range(40):
        controller.refreshInterviewClock()
    assert len(reads) == 40, "Continue checking the authoritative session"
    assert counts == {}
    current["remaining_seconds"] -= 1
    controller.refreshInterviewClock()
    assert controller.interview["remaining_seconds"] == remaining - 1
    assert counts == {"interview": 1}
    controller.stateChanged.emit()
    assert counts == {"interview": 2, "global": 1, "voice": 1}


def test_clock_still_loads_an_authoritative_question_change(controller, monkeypatch):
    calls = []
    monkeypatch.setattr(controller.service, "current_interview", lambda *args: {
        "question": {"question_id": "q-002"}, "remaining_seconds": 120,
    })
    monkeypatch.setattr(controller, "_load_interview", calls.append)
    controller.refreshInterviewClock()
    assert calls == [controller.interview["interview_id"]]


@pytest.mark.parametrize("action", ["pause", "expired", "shutdown"])
def test_leaving_answering_stops_capture_without_upload(controller, monkeypatch, action):
    _stub_dictation_capture(controller, monkeypatch)
    transcriptions = []
    monkeypatch.setattr(controller, "transcribeInterviewRecording", lambda *args: transcriptions.append(args))
    assert controller.startInterviewDictation("synthetic-remote", True)
    recorder = controller._voice_recorder
    path = recorder.path
    original = path.read_bytes()
    _leave_answering(controller, monkeypatch, action)
    QCoreApplication.processEvents()
    assert recorder.state == "recorded"
    assert recorder.path == path and path.read_bytes() == original
    assert controller._voice_auto_transcription is None
    assert controller._voice_transcription_operation_id == ""
    assert not transcriptions
    if action == "pause":
        controller.resumeInterview()
        QCoreApplication.processEvents()
        assert controller.interview["status"] == "active"
        assert controller.interviewVoice["audio_ready"]
        assert recorder.path == path
        assert not transcriptions, "Resume must not renew remote audio consent"
    elif action == "expired":
        assert controller.interview["status"] == "timed_out"
        assert controller.interview["expired"]
        assert controller.interview["question"] is None


@pytest.mark.parametrize("action", ["pause", "expired", "shutdown"])
def test_late_transcription_is_discarded_and_paused_audio_can_retry(controller, monkeypatch, action):
    _dictation_model_ready(controller, monkeypatch)
    _stub_dictation_capture(controller, monkeypatch)
    assert controller.startInterviewRecording()
    assert controller.stopInterviewRecording()
    path = controller._voice_recorder.path
    original = path.read_bytes()
    callbacks = []
    transcripts = []
    monkeypatch.setattr(controller, "_background", lambda operation, complete, failed: callbacks.append((complete, failed)))
    controller.interviewTranscriptReady.connect(transcripts.append)
    controller.transcribeInterviewRecording(LOCAL_STT_ID, False)
    operation_id = controller._voice_transcription_operation_id
    assert operation_id and controller.interviewVoice["transcription_state"] == "transcribing"
    _leave_answering(controller, monkeypatch, action)
    if action == "pause":
        controller.resumeInterview()
    callbacks[0][0]("late text must not change the answer")
    callbacks[0][1]("late error must not overwrite the resumed state")
    assert not transcripts
    assert not controller._voice_transcription_operation_id
    assert controller.interviewVoice["transcription_state"] == "idle"
    assert not controller.interviewVoice["error"]
    assert path.read_bytes() == original
    if action == "pause":
        controller.transcribeInterviewRecording(LOCAL_STT_ID, False)
        assert controller._voice_transcription_operation_id != operation_id
        assert controller._voice_transcription_operation_id
        callbacks[-1][0]("Explicit retry of the retained synthetic recording")
        assert transcripts == ["Explicit retry of the retained synthetic recording"]


def test_pause_invalidates_an_already_queued_automatic_transcription(controller, monkeypatch):
    _stub_dictation_capture(controller, monkeypatch)
    transcriptions = []
    monkeypatch.setattr(controller, "transcribeInterviewRecording", lambda *args: transcriptions.append(args))
    assert controller.startInterviewDictation("synthetic-remote", True)
    assert controller.stopInterviewRecording()  # ready queues transcription on the Qt event loop
    assert controller.pauseInterview()
    controller.resumeInterview()  # Same Profile/question before the queued callback runs
    QCoreApplication.processEvents()
    assert controller.interviewVoice["audio_ready"]
    assert not transcriptions


def test_pausing_recording_keeps_the_production_answer_draft(scene, monkeypatch):
    window, controller = scene
    _stub_dictation_capture(controller, monkeypatch)
    answer = _find(window, "interviewAnswerEditor")
    answer.setProperty("text", "合成草稿：只验证暂停录音后文字保留。")
    assert controller.startInterviewDictation("synthetic-remote", True)
    assert controller.pauseInterview()
    QTest.qWait(30)
    assert answer.property("text") == "合成草稿：只验证暂停录音后文字保留。"
    assert controller._voice_recorder.state == "recorded"
    controller.resumeInterview()
    QTest.qWait(30)
    assert answer.property("text") == "合成草稿：只验证暂停录音后文字保留。"


def test_navigation_stops_capture_but_keeps_an_explicit_transcription(scene, monkeypatch):
    window, controller = scene
    _dictation_model_ready(controller, monkeypatch)
    _stub_dictation_capture(controller, monkeypatch)
    callbacks = []
    monkeypatch.setattr(controller, "_background", lambda operation, complete, failed: callbacks.append((complete, failed)))
    answer = _find(window, "interviewAnswerEditor")
    answer.setProperty("text", "离开页面之前的合成草稿。")
    assert controller.startInterviewDictation(LOCAL_STT_ID, False)
    path = controller._voice_recorder.path
    controller.navigate("connections")
    QTest.qWait(30)
    assert controller._voice_recorder.state == "recorded"
    assert controller._voice_auto_transcription is None
    assert not callbacks, "Leaving must not start an automatic transcription"
    assert path.is_file() and controller._voice_recorder.path == path
    controller.navigate("interview")
    assert answer.property("text") == "离开页面之前的合成草稿。"
    controller.transcribeInterviewRecording(LOCAL_STT_ID, False)
    assert len(callbacks) == 1
    operation_id = controller._voice_transcription_operation_id
    controller.navigate("connections")
    assert controller._voice_transcription_operation_id == operation_id
    callbacks[0][0]("手动重试识别得到的合成文字。")
    QTest.qWait(30)
    controller.navigate("interview")
    assert answer.property("text") == "离开页面之前的合成草稿。\n手动重试识别得到的合成文字。"


def test_repeated_recording_reuses_one_qt_capture_graph(qapp, tmp_path, monkeypatch):
    class Capture(QObject):
        def setAudioInput(self, value):
            self.audio = value
        def setRecorder(self, value):
            self.recorder = value

    class Input(QObject):
        def __init__(self, device, parent):
            super().__init__(parent)
            self.devices = [device]
        def setDevice(self, value):
            self.devices.append(value)

    class Recorder(QObject):
        durationChanged = Signal(int)
        errorOccurred = Signal(int, str)
        recorderStateChanged = Signal(object)
        Quality = QMediaRecorder.Quality
        RecorderState = QMediaRecorder.RecorderState
        def setMediaFormat(self, value):
            pass
        def setQuality(self, value):
            pass
        def setOutputLocation(self, value):
            self.output = Path(value.toLocalFile())
        def record(self):
            self.output.write_bytes(b"synthetic QObject recording fixture")
        def stop(self):
            self.recorderStateChanged.emit(self.RecorderState.StoppedState)

    class Format:
        FileFormat = QMediaFormat.FileFormat
        AudioCodec = QMediaFormat.AudioCodec
        ConversionMode = QMediaFormat.ConversionMode
        def setFileFormat(self, value):
            pass
        def setAudioCodec(self, value):
            pass
        def isSupported(self, value):
            return True

    monkeypatch.setattr(voice, "QMediaCaptureSession", Capture)
    monkeypatch.setattr(voice, "QAudioInput", Input)
    monkeypatch.setattr(voice, "QMediaRecorder", Recorder)
    monkeypatch.setattr(voice, "QMediaFormat", Format)
    monkeypatch.setattr(voice.QMediaDevices, "audioInputs", lambda: ["synthetic microphone"])
    monkeypatch.setattr(voice.QMediaDevices, "defaultAudioInput", lambda: "synthetic microphone")
    recorder = voice.InterviewVoiceRecorder()
    ready = []
    recorder.ready.connect(ready.append)
    identities = []
    for index in range(20):
        recorder.start(tmp_path / f"synthetic-{index}.wav")
        recorder.stop()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        QCoreApplication.processEvents()
        assert len(recorder.children()) == 3
        identities.append((id(recorder._capture), id(recorder._audio_input), id(recorder._recorder)))
    assert len(set(identities)) == 1
    assert len(ready) == 20, "Reusing the recorder must not duplicate signal connections"
    assert len(recorder._audio_input.devices) == 20
    recorder.reset()
    assert recorder.path is None and recorder.state == "idle"
    assert all(Path(path).read_bytes() == b"synthetic QObject recording fixture" for path in ready)
