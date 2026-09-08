from __future__ import annotations

from pathlib import Path
import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtWidgets import QApplication
from PySide6.QtMultimedia import QtAudio, QAudioFormat
import wave

from llm_interview_lab.desktop import voice as voice_module
from llm_interview_lab.desktop.voice import InterviewVoiceRecorder


pytestmark = pytest.mark.infrastructure


@pytest.fixture(scope="module")
def qapp():
    # Audio tests may precede the production QML tests in the same process.
    application = QApplication.instance() or QApplication(["voice-tests"])
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


def _pcm_recorder(tmp_path):
    recorder = InterviewVoiceRecorder()
    recorder.path = tmp_path / "中文录音.wav"
    recorder.state = "recording"
    recorder._format.setSampleRate(16000)
    recorder._format.setChannelCount(1)
    recorder._format.setSampleFormat(QAudioFormat.SampleFormat.Int16)
    recorder._wav = wave.open(str(recorder.path), "wb")
    recorder._wav.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
    recorder._device = QBuffer(recorder)
    recorder._device.open(QIODevice.ReadWrite)
    class Source:
        def stop(self): pass
        def reset(self): pass
        def error(self): return QtAudio.Error.NoError
        def state(self): return QtAudio.State.ActiveState
    recorder._source = Source()
    return recorder


def test_stop_drains_pcm_to_both_wav_and_stream_once(tmp_path, qapp):
    recorder = _pcm_recorder(tmp_path)
    pcm = b"\x01\x00" * 17000
    recorder._device.write(QByteArray(pcm))
    recorder._device.seek(0)
    ready: list[str] = []
    chunks = []
    recorder.ready.connect(ready.append)
    recorder.pcmReady.connect(lambda data, rate, channels: chunks.append((data, rate, channels)))
    recorder.stop()
    assert recorder.state == "recorded"
    assert ready == [str(recorder.path)]
    assert chunks == [(pcm, 16000, 1)]
    assert recorder.duration_ms == 1062
    with wave.open(str(recorder.path)) as audio:
        assert audio.readframes(20000) == pcm
    with pytest.raises(RuntimeError, match="没有正在进行"):
        recorder.stop()
    assert len(chunks) == 1


def test_stopped_recording_without_output_emits_actionable_failure(
    tmp_path: Path, qapp
) -> None:
    del qapp
    recorder = _pcm_recorder(tmp_path)
    errors: list[str] = []
    recorder.failed.connect(errors.append)

    recorder.stop()

    assert recorder.state == "error"
    assert errors
    assert "录音" in errors[0]


def test_audio_packet_updates_only_notify_on_displayed_second(qapp):
    del qapp
    recorder = InterviewVoiceRecorder()
    changes = []
    recorder.changed.connect(lambda: changes.append(recorder.duration_ms))
    # Real Windows recorder emits roughly every 10 ms, not once per second.
    for duration in range(10, 2991, 10):
        recorder._duration_changed(duration)
    assert changes == [1000, 2000]
    assert recorder.duration_ms == 2990, "Keep actual audio time; do not fake an elapsed timer"


def test_device_failure_keeps_partial_wav_retryable_without_ready(tmp_path, qapp):
    recorder = _pcm_recorder(tmp_path)
    recorder._device.write(QByteArray(b"\x01\x00" * 1600))
    recorder._device.seek(0)
    recorder._read_frames()
    ready, errors = [], []
    recorder.ready.connect(ready.append)
    recorder.failed.connect(errors.append)
    recorder._error_message("麦克风已断开")
    assert recorder.state == "recorded" and errors == ["麦克风已断开"]
    assert not ready, "Failure must not trigger an upload or a finished transcript"
    with wave.open(str(recorder.path)) as audio:
        assert audio.getnframes() == 1600
