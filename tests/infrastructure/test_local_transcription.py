"""Streaming STT boundaries; real model checks never auto-download."""

from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
import socket
import threading
import time

import pytest

from llm_interview_lab.ai import local_transcription as local
from llm_interview_lab.ai.transcription import TranscriptionError


@pytest.fixture
def model_download(tmp_path, monkeypatch):
    payloads = {"weights.onnx": b"synthetic-model", "tokens.txt": b"synthetic-tokens"}
    files = tuple((name, "https://example.invalid/" + name, len(body), hashlib.sha256(body).hexdigest())
                  for name, body in payloads.items())
    monkeypatch.setattr(local, "MODEL_FILES", files)
    monkeypatch.setattr(local, "DOWNLOAD_BYTES", sum(item[2] for item in files))
    requests = []

    def request(value, *, timeout):
        requests.append(value.full_url)
        return io.BytesIO(payloads[value.full_url.rsplit("/", 1)[-1]])

    monkeypatch.setattr(local.urllib.request, "urlopen", request)
    return local.LocalSpeechTranscriber(tmp_path / "模型"), payloads, requests


def test_download_verifies_and_reuses_complete_public_files(model_download):
    transcriber, payloads, requests = model_download
    progress = []
    transcriber.download(progress.append, threading.Event())
    assert transcriber.ready()
    assert progress[-1] == 100 and progress == sorted(progress)
    assert len(requests) == len(payloads)
    assert {p.name for p in transcriber.model_root.iterdir()} == set(payloads)
    transcriber.download(progress.append, threading.Event())
    assert len(requests) == len(payloads), "No network on an already installed, verified model"


@pytest.mark.parametrize("body", [b"too-short", b"X" * len(b"synthetic-model")])
def test_incomplete_or_wrong_hash_download_cannot_be_used(model_download, monkeypatch, body):
    transcriber, _, _ = model_download
    monkeypatch.setattr(local.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(body))
    with pytest.raises(TranscriptionError, match="校验失败"):
        transcriber.download(lambda _: None, threading.Event())
    assert not transcriber.ready()
    assert list(transcriber.model_root.iterdir()) == []


def test_cancel_keeps_valid_files_and_retry_finishes(model_download):
    transcriber, payloads, requests = model_download
    cancel = threading.Event()
    # The first file is already safely installed; cancellation must preserve it.
    transcriber.model_root.mkdir(parents=True)
    name, body = next(iter(payloads.items()))
    (transcriber.model_root / name).write_bytes(body)
    with pytest.raises(local.DownloadCancelled):
        transcriber.download(lambda _: cancel.set(), cancel)
    assert (transcriber.model_root / name).read_bytes() == body
    assert not requests
    cancel.clear()
    transcriber.download(lambda _: None, cancel)
    assert transcriber.ready() and len(requests) == 1


def test_cancel_during_download_removes_only_its_partial(model_download, monkeypatch):
    transcriber, payloads, _ = model_download
    cancel = threading.Event()

    class Response(io.BytesIO):
        def read(self, size=-1):
            cancel.set()
            return super().read(size)

    monkeypatch.setattr(local.urllib.request, "urlopen", lambda *a, **k: Response(next(iter(payloads.values()))))
    with pytest.raises(local.DownloadCancelled):
        transcriber.download(lambda _: None, cancel)
    assert not transcriber.ready()
    assert list(transcriber.model_root.iterdir()) == []


def test_download_network_error_is_actionable_without_raw_credentials(model_download, monkeypatch):
    transcriber, _, _ = model_download

    def fail(*args, **kwargs):
        raise TimeoutError("private-proxy-credential")

    monkeypatch.setattr(local.urllib.request, "urlopen", fail)
    with pytest.raises(TranscriptionError) as error:
        transcriber.download(lambda _: None, threading.Event())
    assert "TimeoutError" in str(error.value) and "检查网络" in str(error.value)
    assert "private-proxy-credential" not in str(error.value)
    assert list(transcriber.model_root.iterdir()) == []


def test_missing_model_does_not_download_or_upload(tmp_path, monkeypatch):
    transcriber = local.LocalSpeechTranscriber(tmp_path / "missing")
    monkeypatch.setattr(local.urllib.request, "urlopen", lambda *a, **k: pytest.fail("Unexpected network"))
    with pytest.raises(TranscriptionError, match="下载本地模型"):
        transcriber.transcribe(tmp_path / "not-read.wav")
    assert not transcriber.model_root.exists()


def test_missing_runtime_has_install_guidance(tmp_path, monkeypatch):
    transcriber = local.LocalSpeechTranscriber(tmp_path)
    monkeypatch.setattr(transcriber, "ready", lambda: True)
    monkeypatch.setattr(transcriber, "runtime_available", lambda: False)
    with pytest.raises(TranscriptionError, match="desktop 依赖"):
        transcriber.transcribe(tmp_path / "not-read.wav")


@pytest.mark.skipif(not os.environ.get("LLM_LAB_TEST_LOCAL_STT_MODEL_ROOT"), reason="Explicit local model/audio paths required")
def test_real_model_chinese_stereo_long_and_silence_offline(tmp_path, monkeypatch):
    """Use a downloaded public test clip, never microphone or a real Profile."""
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly

    model_root = Path(os.environ["LLM_LAB_TEST_LOCAL_STT_MODEL_ROOT"])
    source = Path(os.environ["LLM_LAB_TEST_LOCAL_STT_AUDIO"])
    original_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    transcriber = local.LocalSpeechTranscriber(model_root)
    assert transcriber.ready()
    def no_network(*a, **k):
        pytest.fail("Local inference must not access the network")
    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket.socket, "connect_ex", no_network)
    monkeypatch.setattr(local.urllib.request, "urlopen", no_network)
    start = time.perf_counter()
    transcript = transcriber.transcribe(source)
    assert "早上九点" in transcript and "下午五点" in transcript, transcript
    print(f"LOCAL_STT_COLD seconds={time.perf_counter() - start:.2f} text={transcript}")
    samples, rate = sf.read(source, dtype="float32")
    assert rate == 16000
    # Accept 48 kHz stereo as well as native 16 kHz PCM; endpoint resets must
    # neither duplicate sentences nor truncate the final segment.
    passage = np.concatenate([samples, np.zeros(16000, dtype=np.float32)])
    mono = resample_poly(np.tile(passage, 6), 3, 1)
    stereo = tmp_path / "中文录音 有空格.wav"
    sf.write(stereo, np.column_stack([mono, mono]), 48000, subtype="PCM_16")
    stereo_sha = hashlib.sha256(stereo.read_bytes()).hexdigest()
    start = time.perf_counter()
    transcript = transcriber.transcribe(stereo)
    assert transcript.count("早上九点") == 6 and transcript.count("下午五点") == 6, transcript
    print(f"LOCAL_STT_LONG seconds={time.perf_counter() - start:.2f} audio_seconds={len(mono) / 48000:.2f} segments=6")
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_sha
    assert hashlib.sha256(stereo.read_bytes()).hexdigest() == stereo_sha
    silence = tmp_path / "silence.wav"
    sf.write(silence, np.zeros(16000 * 2, dtype=np.float32), 16000)
    with pytest.raises(TranscriptionError, match="没有识别到清晰的人声"):
        transcriber.transcribe(silence)


@pytest.mark.skipif(not os.environ.get("LLM_LAB_TEST_LOCAL_STT_MODEL_ROOT"), reason="Explicit public model/audio paths required")
def test_real_stream_emits_text_before_input_finished(monkeypatch):
    import soundfile as sf
    transcriber = local.LocalSpeechTranscriber(Path(os.environ["LLM_LAB_TEST_LOCAL_STT_MODEL_ROOT"]))
    monkeypatch.setattr(socket.socket, "connect", lambda *a, **k: pytest.fail("Unexpected network"))
    monkeypatch.setattr(local.urllib.request, "urlopen", lambda *a, **k: pytest.fail("Unexpected download"))
    updates = []
    fed_seconds = 0
    eof = False
    loaded = time.perf_counter()
    def blocks():
        nonlocal fed_seconds, eof
        with sf.SoundFile(os.environ["LLM_LAB_TEST_LOCAL_STT_AUDIO"]) as source:
            for chunk in source.blocks(blocksize=source.samplerate // 10, dtype="int16", always_2d=True):
                fed_seconds += len(chunk) / source.samplerate
                yield chunk.tobytes(), source.samplerate, source.channels
        eof = True
    def update(value):
        if value:
            updates.append((eof, fed_seconds, value))
    text = transcriber.stream(blocks(), update, threading.Event())
    assert len([item for item in updates if not item[0]]) >= 3
    assert updates[0][1] < fed_seconds, "Speech must appear while input is still open"
    assert "下午五点" in text and text.count("早上九点") == 1
    assert updates[-1][2] == text
    print(f"STREAM_REAL first_audio_seconds={updates[0][1]:.2f} updates={len(updates)} decode_seconds={time.perf_counter()-loaded:.2f}")


def test_stream_cancel_does_not_flush_or_publish_late_text(tmp_path, monkeypatch):
    cancel = threading.Event()
    updates = []
    class Stream:
        def accept_waveform(self, *args): pytest.fail("Cancelled stream decoded input")
        def input_finished(self): pytest.fail("Cancelled stream flushed")
    class Recognizer:
        def create_stream(self): return Stream()
    transcriber = local.LocalSpeechTranscriber(tmp_path)
    monkeypatch.setattr(transcriber, "_load", lambda: Recognizer())
    cancel.set()
    assert transcriber.stream([], updates.append, cancel) == ""
    assert not [u for u in updates if u]
