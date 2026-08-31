from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QCoreApplication
from PySide6.QtMultimedia import QMediaDevices, QMediaRecorder

from llm_interview_lab.desktop import voice as voice_module
from llm_interview_lab.desktop.voice import InterviewVoiceRecorder


pytestmark = pytest.mark.infrastructure


@pytest.fixture(scope="module")
def qapp():
    application = QCoreApplication.instance() or QCoreApplication(["voice-tests"])
    yield application


def test_recorder_reports_missing_microphone_without_creating_audio(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, qapp
) -> None:
    del qapp
    monkeypatch.setattr(voice_module.QMediaDevices, "audioInputs", staticmethod(lambda: []))
    recorder = InterviewVoiceRecorder()

    with pytest.raises(RuntimeError, match="麦克风"):
        recorder.start(tmp_path / "answer.wav")

    assert recorder.state == "idle"
    assert not (tmp_path / "answer.wav").exists()


def test_stopped_recording_becomes_ready_only_when_a_nonempty_file_exists(
    tmp_path: Path, qapp
) -> None:
    del qapp
    recorder = InterviewVoiceRecorder()
    output = tmp_path / "answer.wav"
    output.write_bytes(b"RIFF test")
    recorder.path = output
    recorder.state = "recording"
    ready: list[str] = []
    recorder.ready.connect(ready.append)

    recorder._state_changed(QMediaRecorder.RecorderState.StoppedState)

    assert recorder.state == "recorded"
    assert ready == [str(output)]


def test_stopped_recording_without_output_emits_actionable_failure(
    tmp_path: Path, qapp
) -> None:
    del qapp
    recorder = InterviewVoiceRecorder()
    recorder.path = tmp_path / "missing.wav"
    recorder.state = "recording"
    errors: list[str] = []
    recorder.failed.connect(errors.append)

    recorder._state_changed(QMediaRecorder.RecorderState.StoppedState)

    assert recorder.state == "error"
    assert errors
    assert "录音" in errors[0]
