"""Small Qt Multimedia recorder for profile-local interview answers."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import (
    QAudioInput,
    QMediaCaptureSession,
    QMediaDevices,
    QMediaFormat,
    QMediaRecorder,
)


class InterviewVoiceRecorder(QObject):
    """Record one real local WAV without owning interview domain state."""

    changed = Signal()
    ready = Signal(str)
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.state = "idle"
        self.duration_ms = 0
        self.error_message = ""
        self.path: Path | None = None
        self._capture: QMediaCaptureSession | None = None
        self._audio_input: QAudioInput | None = None
        self._recorder: QMediaRecorder | None = None

    def start(self, destination: Path) -> None:
        if self.state == "recording":
            raise RuntimeError("录音已经开始")
        inputs = QMediaDevices.audioInputs()
        if not inputs:
            raise RuntimeError("未检测到可用麦克风；你仍可直接输入文字回答")
        destination.parent.mkdir(parents=True, exist_ok=True)
        self.path = destination
        self.duration_ms = 0
        self.error_message = ""
        self._capture = QMediaCaptureSession(self)
        self._audio_input = QAudioInput(QMediaDevices.defaultAudioInput(), self)
        self._recorder = QMediaRecorder(self)
        media_format = QMediaFormat()
        media_format.setFileFormat(QMediaFormat.FileFormat.Wave)
        media_format.setAudioCodec(QMediaFormat.AudioCodec.Wave)
        if not media_format.isSupported(QMediaFormat.ConversionMode.Encode):
            raise RuntimeError("当前系统的 Qt Multimedia 不支持 WAV 录音；请改用文字回答")
        self._recorder.setMediaFormat(media_format)
        self._recorder.setQuality(QMediaRecorder.Quality.NormalQuality)
        self._recorder.setOutputLocation(QUrl.fromLocalFile(str(destination)))
        self._capture.setAudioInput(self._audio_input)
        self._capture.setRecorder(self._recorder)
        self._recorder.durationChanged.connect(self._duration_changed)
        self._recorder.errorOccurred.connect(self._error)
        self._recorder.recorderStateChanged.connect(self._state_changed)
        self.state = "recording"
        self.changed.emit()
        self._recorder.record()

    def stop(self) -> None:
        if self.state != "recording" or self._recorder is None:
            raise RuntimeError("当前没有正在进行的录音")
        self._recorder.stop()

    def reset(self) -> None:
        if self._recorder is not None and self.state == "recording":
            self._recorder.stop()
        self.state = "idle"
        self.duration_ms = 0
        self.error_message = ""
        self.path = None
        self.changed.emit()

    def _duration_changed(self, value: int) -> None:
        self.duration_ms = max(0, int(value))
        self.changed.emit()

    def _state_changed(self, value: QMediaRecorder.RecorderState) -> None:
        if value != QMediaRecorder.RecorderState.StoppedState or self.state != "recording":
            return
        if self.path is None or not self.path.is_file() or self.path.stat().st_size == 0:
            self._error_message("录音没有生成有效音频；请检查麦克风权限或改用文字回答")
            return
        self.state = "recorded"
        self.changed.emit()
        self.ready.emit(str(self.path))

    def _error(self, _error: QMediaRecorder.Error, message: str) -> None:
        self._error_message(message or "录音失败；请检查麦克风权限或改用文字回答")

    def _error_message(self, message: str) -> None:
        self.state = "error"
        self.error_message = message
        self.changed.emit()
        self.failed.emit(message)
