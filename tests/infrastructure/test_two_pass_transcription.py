"""Production two-pass scheduling, PCM continuity and per-recording isolation."""

from concurrent.futures import Future, ThreadPoolExecutor
import hashlib
import io
import threading

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")
from scipy.signal import resample_poly

from llm_interview_lab.ai import local_transcription as local
from llm_interview_lab.ai.two_pass_transcription import mono_16k, stream_two_pass
from llm_interview_lab.ai.transcription import TranscriptionError


class Preview:
    class Stream:
        last = 0

        def accept_waveform(self, rate, samples):
            assert rate == 16000
            if len(samples) and samples[0]:
                self.last = round(float(samples[0]) * 32768)

        def input_finished(self):
            pass

    def create_stream(self):
        return self.Stream()

    def is_ready(self, stream):
        return False

    def get_result(self, stream):
        # Segment 2 has speech that the fast decoder fails to recognize.
        return f"预览{stream.last}" if stream.last and stream.last != 2 else ""

    def reset(self, stream):
        stream.last = 0


class Pauses:
    """Fixture audio treats each nonzero block as one acoustic speech segment."""
    ready = False

    def accept_waveform(self, samples):
        self.ready = bool(np.any(samples))

    def empty(self):
        return not self.ready

    def is_speech_detected(self):
        return self.ready

    def pop(self):
        self.ready = False

    def flush(self):
        pass


def pcm(value, samples=1600):
    return np.full(samples, value, dtype="<i2").tobytes(), 16000, 1


def test_acoustic_segments_include_unrecognized_preview_and_replace_in_order():
    updates, received = [], []

    def correct(samples, cancel):
        value = round(float(samples[0]) * 32768)
        received.append(value)
        future = Future()
        future.set_result(f"校准{value}")
        return future

    result = stream_two_pass([pcm(1), pcm(2), pcm(3)], updates.append, threading.Event(), Preview(), Pauses(), correct)
    assert received == [1, 2, 3], "Empty preview must not discard speech PCM"
    assert result == "校准1\n校准2\n校准3"
    assert updates[-1] == result and "预览" not in result


def test_preview_continues_during_correction_and_cancel_restart_does_not_wait(tmp_path, monkeypatch):
    transcriber = local.LocalSpeechTranscriber(tmp_path)
    monkeypatch.setattr(transcriber, "_load", Preview)
    monkeypatch.setattr(transcriber, "_new_vad", Pauses)
    inflight, release, later_audio, new_audio = (threading.Event() for _ in range(4))
    cancel = threading.Event()
    old_updates, new_updates, calls = [], [], []

    def correct(samples, event):
        value = round(float(samples[0]) * 32768)
        calls.append(value)
        if value == 1:
            inflight.set()
            assert release.wait(5)
        return f"校准{value}"

    def old_blocks():
        yield pcm(1)
        assert inflight.wait(5)
        yield pcm(3)
        later_audio.set()

    def new_blocks():
        yield pcm(4)
        new_audio.set()

    monkeypatch.setattr(transcriber, "_correct", correct)
    with ThreadPoolExecutor(max_workers=2) as callers:
        try:
            old = callers.submit(transcriber.stream, old_blocks(), old_updates.append, cancel)
            assert later_audio.wait(5)
            assert any("预览3" in text for text in old_updates)
            cancel.set()
            assert old.result(timeout=1) == "", "Cancel must not join native correction"
            snapshot = list(old_updates)
            new = callers.submit(transcriber.stream, new_blocks(), new_updates.append, threading.Event())
            assert new_audio.wait(2), "The next preview can start before the old native job drains"
            assert "预览4" in new_updates[-1]
            release.set()
            assert new.result(timeout=3) == "校准4"
            assert old_updates == snapshot
            assert 3 not in calls, "Cancelled queued corrections must not run"
        finally:
            release.set()
            cancel.set()
            transcriber._correction_pool.shutdown(wait=True, cancel_futures=True)


def test_stop_without_pause_flushes_remaining_speech():
    class NoPause(Pauses):
        def accept_waveform(self, samples):
            self.ready = False

        def flush(self):
            self.ready = True

    def correct(samples, cancel):
        assert len(samples) == 1600, "Preview padding is not candidate speech"
        future = Future()
        future.set_result("完整尾句")
        return future

    assert stream_two_pass([pcm(1)], lambda _: None, threading.Event(), Preview(), NoPause(), correct) == "完整尾句"


def test_idle_tick_publishes_correction_without_more_audio():
    updates = []
    future = Future()

    def blocks():
        yield pcm(1)
        assert updates[-1] == "预览1"
        future.set_result("停句校准结果")
        yield b"", 16000, 1
        assert updates[-1] == "停句校准结果", "Do not wait for Stop or another spoken word"

    assert stream_two_pass(blocks(), updates.append, threading.Event(), Preview(), Pauses(),
                           lambda *_: future) == "停句校准结果"


def test_silence_never_calls_corrector():
    def unexpected(*_):
        pytest.fail("Do not feed silence to a generative ASR model")

    with pytest.raises(TranscriptionError, match="没有识别到清晰的人声"):
        stream_two_pass([pcm(0)] * 60, lambda _: None, threading.Event(), Preview(), Pauses(), unexpected)


def test_correction_error_retains_preview_and_is_not_silent_success():
    updates = []

    def fail(samples, cancel):
        result = Future()
        result.set_exception(TranscriptionError("本地校准失败，请重试转录"))
        return result

    with pytest.raises(TranscriptionError, match="本地校准失败"):
        stream_two_pass([pcm(1)], updates.append, threading.Event(), Preview(), Pauses(), fail)
    assert updates[-1] == "预览1"


@pytest.mark.parametrize("rate", [16000, 44100, 48000])
def test_resampling_preserves_length_filter_context_and_stereo(rate):
    samples = (10000 * np.sin(2 * np.pi * 431 * np.arange(rate + 71) / rate)).astype("<i2")
    stereo = np.column_stack((samples, samples))
    blocks = [(stereo[i:i + 997].tobytes(), rate, 2) for i in range(0, len(stereo), 997)]
    result = np.concatenate(list(mono_16k(blocks, threading.Event())))
    from math import gcd
    divisor = gcd(rate, 16000)
    expected = resample_poly(samples.astype(np.float32) / 32768, 16000 // divisor, rate // divisor)
    assert len(result) == len(expected)
    np.testing.assert_allclose(result, expected, atol=2e-5)


def test_upgrade_download_installs_nested_files_and_reuses_preview(tmp_path, monkeypatch):
    preview = b"existing-preview"
    correction = b"new-correction"
    files = (("preview.onnx", "https://example.invalid/preview", len(preview), hashlib.sha256(preview).hexdigest()),
             ("qwen/model/decoder.onnx", "https://example.invalid/correction", len(correction), hashlib.sha256(correction).hexdigest()))
    monkeypatch.setattr(local, "MODEL_FILES", files)
    monkeypatch.setattr(local, "DOWNLOAD_BYTES", len(preview) + len(correction))
    (tmp_path / "preview.onnx").write_bytes(preview)
    transcriber = local.LocalSpeechTranscriber(tmp_path)
    assert not transcriber.ready(), "Old preview-only install is not a ready two-pass bundle"
    urls = []

    def download(request, **_):
        urls.append(request.full_url)
        return io.BytesIO(correction)

    monkeypatch.setattr(local.urllib.request, "urlopen", download)
    transcriber.download(lambda _: None, threading.Event())
    assert transcriber.ready() and urls == ["https://example.invalid/correction"]
    assert (tmp_path / "preview.onnx").read_bytes() == preview
    assert (tmp_path / "qwen/model/decoder.onnx").read_bytes() == correction
