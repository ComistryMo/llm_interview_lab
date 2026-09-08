"""Local Zipformer preview plus Qwen3-ASR 0.6B acoustic-pause correction.

Only download() accesses the network. transcribe() never sends audio, opens
a provider connection, or downloads missing assets. See docs/local-stt.md.
"""

from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor
from importlib.util import find_spec
import os
from pathlib import Path
import threading
from typing import Callable, Iterable
import urllib.request
from uuid import uuid4

from .transcription import TranscriptionError
from .local_stt_assets import CORRECTION_FILES, VAD_FILE
from .two_pass_transcription import stream_two_pass


LOCAL_STT_ID = "local-zipformer-streaming"
MODEL_NAME = "流式预览 + Qwen3-ASR 0.6B · 本地校准"
MODEL_REVISION = "98590b7ed6443e77b714204da2757d75e1a642f4"
MODEL_BASE_URL = (
    "https://huggingface.co/csukuangfj/"
    "sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20/resolve/"
    + MODEL_REVISION + "/"
)
MODEL_LICENSE_URL = MODEL_BASE_URL.replace("/resolve/", "/blob/") + "README.md"
ENCODER_FILE = "encoder-epoch-99-avg-1.int8.onnx"
DECODER_FILE = "decoder-epoch-99-avg-1.onnx"
JOINER_FILE = "joiner-epoch-99-avg-1.int8.onnx"
# Fixed files, sizes and SHA-256: partial downloads cannot become ready models.
MODEL_FILES = (
    (ENCODER_FILE, MODEL_BASE_URL + ENCODER_FILE, 181895032,
     "8fa764187a261844f859d7143ebaa563af5d10adfece4c18a8f414c88cba2a9b"),
    (DECODER_FILE, MODEL_BASE_URL + DECODER_FILE, 13876452,
     "2e3b5ec371f8899ee6acd829fd753ba45772df57a91bdf37cde3136354e7db7d"),
    (JOINER_FILE, MODEL_BASE_URL + JOINER_FILE, 3228404,
     "1ed689c5ed19dbaa725d9d191bb4822b5f4855a39e1ffd28cbc1f340d25b2ee0"),
    ("tokens.txt", MODEL_BASE_URL + "tokens.txt", 56317,
     "a8e0e4ec53810e433789b54a5c0134a7eaa2ffca595a6334d54c00da858841d3"),
    ("README.md", MODEL_BASE_URL + "README.md", 296,
     "b6f9458f4208ae821beaaf11dc983486916a4089a2f3677b40f9ff06ec4e6440"),
) + CORRECTION_FILES
DOWNLOAD_BYTES = sum(item[2] for item in MODEL_FILES)


class DownloadCancelled(Exception):
    """An explicit cancellation, not an inference or provider failure."""


class LocalSpeechTranscriber:
    def __init__(self, model_root: Path) -> None:
        self.model_root = model_root
        self._recognizer = None
        self._corrector = None
        self._load_lock = threading.Lock()
        self._correction_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="local-asr-correction")

    @staticmethod
    def runtime_available() -> bool:
        return all(find_spec(name) is not None for name in ("sherpa_onnx", "numpy", "soundfile", "scipy"))

    def ready(self) -> bool:
        return all((self.model_root / name).is_file()
                   and (self.model_root / name).stat().st_size == size
                   for name, _url, size, _digest in MODEL_FILES)

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def download(self, progress: Callable[[int], None], cancel: threading.Event) -> None:
        """Fetch public model files only, after the user's download action."""
        self.model_root.mkdir(parents=True, exist_ok=True)
        received = 0
        for name, url, size, digest in MODEL_FILES:
            if cancel.is_set():
                raise DownloadCancelled()
            target = self.model_root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_file() and target.stat().st_size == size and self._sha256(target) == digest:
                received += size
                progress(int(100 * received / DOWNLOAD_BYTES))
                continue
            temporary = target.with_name(f".{target.name}.{uuid4().hex}.part")
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "LLMInterviewLab/local-stt"})
                downloaded = 0
                hasher = hashlib.sha256()
                with urllib.request.urlopen(request, timeout=20) as response, temporary.open("xb") as output:
                    while True:
                        if cancel.is_set():
                            raise DownloadCancelled()
                        block = response.read(1024 * 1024)
                        if not block:
                            break
                        downloaded += len(block)
                        if downloaded > size:
                            raise TranscriptionError("模型下载大小不匹配，请重试下载；原录音不受影响。")
                        hasher.update(block)
                        output.write(block)
                        progress(min(99, int(100 * (received + downloaded) / DOWNLOAD_BYTES)))
                if downloaded != size or hasher.hexdigest() != digest:
                    raise TranscriptionError("模型下载不完整或校验失败，请重试下载；不会使用损坏的模型。")
                os.replace(temporary, target)
                received += size
            except (TranscriptionError, DownloadCancelled):
                raise
            except Exception as error:
                raise TranscriptionError(
                    f"模型下载失败（{type(error).__name__}）。请检查网络和磁盘空间后重试；已校验文件会复用，录音保留在本机。"
                ) from error
            finally:
                temporary.unlink(missing_ok=True)
        progress(100)

    def _load(self):
        if not self.ready():
            raise TranscriptionError("请先点击“下载本地模型”，完成后即可离线转录。")
        if not self.runtime_available():
            raise TranscriptionError("本地语音组件未安装。请按桌面指南更新 desktop 依赖；模型和录音不会删除。")
        import sherpa_onnx

        with self._load_lock:
            if self._recognizer is None:
                for name, _url, _size, digest in MODEL_FILES:
                    if name in {item[0] for item in CORRECTION_FILES}:
                        continue  # Verify Qwen on its worker, not before preview.
                    if self._sha256(self.model_root / name) != digest:
                        raise TranscriptionError("本地模型校验失败。请重新下载模型；录音保留在本机。")
                self._recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
                    encoder=str(self.model_root / ENCODER_FILE),
                    decoder=str(self.model_root / DECODER_FILE),
                    joiner=str(self.model_root / JOINER_FILE),
                    tokens=str(self.model_root / "tokens.txt"),
                    provider="cpu", num_threads=2, model_type="zipformer",
                    enable_endpoint_detection=False,
                )
        return self._recognizer

    def _new_vad(self):
        import sherpa_onnx
        digest = next(item[3] for item in CORRECTION_FILES if item[0] == VAD_FILE)
        if self._sha256(self.model_root / VAD_FILE) != digest:
            raise TranscriptionError("本地人声检测模型校验失败。请重新下载模型；录音保留在本机。")
        config = sherpa_onnx.VadModelConfig()
        config.silero_vad.model = str(self.model_root / VAD_FILE)
        config.silero_vad.min_silence_duration = 0.8
        config.silero_vad.min_speech_duration = 0.25
        config.silero_vad.max_speech_duration = 30
        config.sample_rate = 16000
        config.num_threads = 1
        return sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=60)

    def _correct(self, samples, cancel) -> str:
        if cancel.is_set():
            return ""
        try:
            import sherpa_onnx
            if self._corrector is None:
                for name, _url, _size, digest in CORRECTION_FILES:
                    if self._sha256(self.model_root / name) != digest:
                        raise TranscriptionError("本地校准模型校验失败。请重新下载模型；录音保留在本机。")
                    if cancel.is_set():
                        return ""
                model = self.model_root / "qwen" / "model_0.6B"
                self._corrector = sherpa_onnx.OfflineRecognizer.from_qwen3_asr(
                    conv_frontend=str(model / "conv_frontend.onnx"),
                    encoder=str(model / "encoder.int8.onnx"),
                    decoder=str(model / "decoder.int8.onnx"),
                    tokenizer=str(model.parent / "tokenizer"),
                    num_threads=2, provider="cpu", max_new_tokens=256,
                )
            if cancel.is_set():
                return ""
            stream = self._corrector.create_stream()
            stream.accept_waveform(16000, samples)
            self._corrector.decode_stream(stream)
            text = stream.result.text.strip()
            if not text and not cancel.is_set():
                raise TranscriptionError("本地校准没有返回文字，请重试转录或重新录音；草稿和音频仍保留。")
            return text
        except TranscriptionError:
            raise
        except Exception as error:
            raise TranscriptionError(
                f"本地 0.6B 校准失败（{type(error).__name__}）。请重试转录；草稿和录音保留，不会改用云端。"
            ) from error

    def stream(
        self, blocks: Iterable[tuple[bytes, int, int]],
        update: Callable[[str], None], cancel: threading.Event,
    ) -> str:
        """Consume live PCM16 frames, publishing cumulative text before EOF.

        Each tuple contains interleaved PCM, sample rate and channel count.
        All model work belongs on the calling worker, never the Qt thread.
        """
        try:
            if cancel.is_set():
                return ""
            recognizer = self._load()
            return stream_two_pass(blocks, update, cancel, recognizer, self._new_vad(),
                                   lambda pcm, event: self._correction_pool.submit(self._correct, pcm, event))
        except TranscriptionError:
            raise
        except Exception as error:
            raise TranscriptionError(
                f"本地转录失败（{type(error).__name__}）。请检查录音或重试；音频没有上传，也不会改用远程服务。"
            ) from error

    def transcribe(self, audio_path: Path) -> str:
        """Explicit retry of a retained WAV, using the same two-pass pipeline."""
        # Check dependencies/model before opening audio; no implicit downloads.
        self._load()
        import soundfile as sf

        def blocks():
            with sf.SoundFile(str(audio_path)) as source:
                for block in source.blocks(blocksize=source.samplerate // 10, dtype="int16", always_2d=True):
                    yield block.astype("<i2").tobytes(), source.samplerate, source.channels

        return self.stream(blocks(), lambda _: None, threading.Event())
