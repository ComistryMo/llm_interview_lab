"""One Qt PCM microphone capture, shared by the local WAV and live STT."""

from __future__ import annotations

from array import array
from pathlib import Path
import wave

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtMultimedia import QtAudio, QAudioFormat, QAudioSource, QMediaDevices


class InterviewVoiceRecorder(QObject):
    """Capture PCM without an encoder shutdown or inference on the UI thread."""

    changed = Signal()
    ready = Signal(str)
    failed = Signal(str)
    pcmReady = Signal(bytes, int, int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.state = "idle"
        self.duration_ms = 0
        self.error_message = ""
        self.path: Path | None = None
        self._source: QAudioSource | None = None
        self._device = None
        self._device_id = None
        self._format = QAudioFormat()
        self._wav = None
        self._pending = b""
        self._frames = 0
        self._poll = QTimer(self)
        self._poll.setInterval(80)
        self._poll.timeout.connect(self._read_frames)

    def start(self, destination: Path) -> None:
        if self.state == "recording":
            raise RuntimeError("录音已经开始")
        if not QMediaDevices.audioInputs():
            raise RuntimeError("未检测到可用麦克风；你仍可直接输入文字回答")
        device = QMediaDevices.defaultAudioInput()
        audio_format = QAudioFormat()
        audio_format.setSampleRate(16000)
        audio_format.setChannelCount(1)
        audio_format.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        if not device.isFormatSupported(audio_format):
            audio_format = device.preferredFormat()
        if not audio_format.isValid():
            raise RuntimeError("麦克风没有可用的音频格式，请在系统设置选择其他输入设备，或直接输入文字")
        destination.parent.mkdir(parents=True, exist_ok=True)
        self.path = destination
        self.duration_ms = self._frames = 0
        self.error_message = ""
        self._pending = b""
        if self._source is None or self._device_id != device.id() or self._format != audio_format:
            if self._source is not None:
                self._source.deleteLater()
            self._source = QAudioSource(device, audio_format, self)
            self._source.setBufferSize(audio_format.bytesForDuration(800_000))
            self._device_id = device.id()
            self._format = audio_format
        self._wav = wave.open(str(destination), "wb")
        self._wav.setnchannels(audio_format.channelCount())
        self._wav.setsampwidth(2)
        self._wav.setframerate(audio_format.sampleRate())
        self.state = "recording"
        self._device = self._source.start()
        if self._device is None or self._source.error() != QtAudio.Error.NoError:
            self._error_message("无法打开麦克风；请检查系统麦克风权限及默认输入设备，或直接输入文字回答")
            return
        self._poll.start()
        self.changed.emit()

    def _read_frames(self) -> None:
        if self.state != "recording" or self._device is None:
            return
        # Poll alongside PCM: current Qt uses QtAudio enums, whereas some
        # PySide wheels still expose stateChanged's legacy QAudio signature.
        if self._source.error() != QtAudio.Error.NoError or self._source.state() == QtAudio.State.StoppedState:
            self._error_message("麦克风已断开或录音失败；请检查系统输入设备后重新录音，已写入的音频保留在本机")
            return
        try:
            self._pending += bytes(self._device.readAll())
            frame_bytes = self._format.bytesPerFrame()
            length = len(self._pending) // frame_bytes * frame_bytes
            if not length:
                return
            data, self._pending = self._pending[:length], self._pending[length:]
            sample_format = self._format.sampleFormat()
            if sample_format == QAudioFormat.SampleFormat.Float:
                data = array("h", (max(-32768, min(32767, int(v * 32768))) for v in array("f", data))).tobytes()
            elif sample_format == QAudioFormat.SampleFormat.Int32:
                data = array("h", (v >> 16 for v in array("i", data))).tobytes()
            elif sample_format == QAudioFormat.SampleFormat.UInt8:
                data = array("h", ((v - 128) << 8 for v in data)).tobytes()
            self._wav.writeframesraw(data)
            self._frames += length // frame_bytes
            self._duration_changed(self._frames * 1000 // self._format.sampleRate())
            self.pcmReady.emit(data, self._format.sampleRate(), self._format.channelCount())
        except Exception:
            self._error_message("录音读取或保存失败；请检查麦克风和磁盘空间，已写入的音频保留在本机")

    def stop(self) -> None:
        if self.state != "recording" or self._source is None:
            raise RuntimeError("当前没有正在进行的录音")
        self._poll.stop()
        self._read_frames()  # Keep the final incomplete timer interval.
        if self.state != "recording":
            return
        self.state = "stopping"
        self._source.stop()
        self._device = None
        self._close_wav()
        if not self._frames:
            self._error_message("录音中没有音频；请检查麦克风权限，稍后重新录音或直接输入文字")
            return
        self.state = "recorded"
        self.changed.emit()
        self.ready.emit(str(self.path))

    def reset(self) -> None:
        if self.state == "recording":
            self.stop()
        self.state = "idle"
        self.duration_ms = 0
        self._frames = 0
        self._pending = b""
        self.error_message = ""
        self.path = None
        self.changed.emit()

    def _close_wav(self) -> None:
        if self._wav is not None:
            self._wav.close()
            self._wav = None

    def _duration_changed(self, value: int) -> None:
        previous_second = self.duration_ms // 1000
        self.duration_ms = max(0, int(value))
        if self.duration_ms // 1000 != previous_second:
            self.changed.emit()

    def _error_message(self, message: str) -> None:
        self.state = "error"
        self.error_message = message
        self._poll.stop()
        if self._source is not None:
            self._source.reset()
        self._device = None
        self._close_wav()
        if self._frames:
            self.state = "recorded"  # Keep a completed partial WAV retryable.
        self.changed.emit()
        self.failed.emit(message)
