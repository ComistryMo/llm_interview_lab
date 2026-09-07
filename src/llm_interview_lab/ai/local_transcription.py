"""Opt-in model download and offline SenseVoiceSmall transcription on CPU.

Only download() accesses the network. transcribe() never sends audio, opens
a provider connection, or downloads missing assets. See docs/local-stt.md.
"""

from __future__ import annotations

import hashlib
from importlib.util import find_spec
import math
import os
from pathlib import Path
import threading
from typing import Callable
import urllib.request
from uuid import uuid4

from .transcription import TranscriptionError


LOCAL_STT_ID = "local-sensevoice"
MODEL_NAME = "SenseVoiceSmall · 本地中文转录"
MODEL_REVISION = "2365baeacb507f821a0c8120fcee3d484dba7a07"
MODEL_BASE_URL = (
    "https://huggingface.co/csukuangfj/"
    "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/resolve/"
    + MODEL_REVISION + "/"
)
MODEL_LICENSE_URL = "https://github.com/modelscope/FunASR/blob/main/MODEL_LICENSE"
# Fixed files, sizes and SHA-256: partial downloads cannot become ready models.
MODEL_FILES = (
    ("model.int8.onnx", MODEL_BASE_URL + "model.int8.onnx", 239233841,
     "c71f0ce00bec95b07744e116345e33d8cbbe08cef896382cf907bf4b51a2cd51"),
    ("tokens.txt", MODEL_BASE_URL + "tokens.txt", 315894,
     "f449eb28dc567533d7fa59be34e2abca8784f771850c78a47fb731a31429a1dc"),
    ("LICENSE", MODEL_BASE_URL + "LICENSE", 71,
     "221c6df10b0931a5629adad671ea48fb7747e034c414b6d2bfa275bc3dd4ea17"),
    ("silero_vad.onnx",
     "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx",
     643854, "9e2449e1087496d8d4caba907f23e0bd3f78d91fa552479bb9c23ac09cbb1fd6"),
    ("FunASR-MODEL-LICENSE.txt",
     "https://raw.githubusercontent.com/modelscope/FunASR/e19029adca384a06a2f60bd8c18cb98f1a0499aa/MODEL_LICENSE",
     5306, "7dba975a2069691db4992b0592d70828b330d2f8a30a71450f4e152a554e84f8"),
    ("Silero-LICENSE.txt",
     "https://raw.githubusercontent.com/snakers4/silero-vad/867c2aa692646a1f1de3e94a15c9dd9f614c0acb/LICENSE",
     1075, "2e63e9a38b6e8fc0c7bc37ce174caca1862870856c6daf5697cfb785e925520b"),
)
DOWNLOAD_BYTES = sum(item[2] for item in MODEL_FILES)


class DownloadCancelled(Exception):
    """An explicit cancellation, not an inference or provider failure."""


class LocalSpeechTranscriber:
    def __init__(self, model_root: Path) -> None:
        self.model_root = model_root
        self._recognizer = None

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
            if target.is_file() and target.stat().st_size == size and self._sha256(target) == digest:
                received += size
                progress(int(100 * received / DOWNLOAD_BYTES))
                continue
            temporary = target.with_name(f".{name}.{uuid4().hex}.part")
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

        if self._recognizer is None:
            for name, _url, _size, digest in MODEL_FILES:
                if self._sha256(self.model_root / name) != digest:
                    raise TranscriptionError("本地模型校验失败。请重新下载模型；录音保留在本机。")
            self._recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                model=str(self.model_root / "model.int8.onnx"),
                tokens=str(self.model_root / "tokens.txt"),
                language="auto", use_itn=True, provider="cpu", num_threads=2,
            )
        return self._recognizer

    def transcribe(self, audio_path: Path) -> str:
        """Decode speech segments locally; preserve the original WAV unchanged."""
        try:
            recognizer = self._load()
            import numpy as np
            import sherpa_onnx
            import soundfile as sf
            from scipy.signal import resample_poly

            config = sherpa_onnx.VadModelConfig()
            config.silero_vad.model = str(self.model_root / "silero_vad.onnx")
            config.silero_vad.min_silence_duration = 0.5
            config.silero_vad.max_speech_duration = 20
            config.sample_rate = 16000
            vad = sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=30)
            parts: list[str] = []

            def decode_segments() -> None:
                while not vad.empty():
                    stream = recognizer.create_stream()
                    stream.accept_waveform(16000, vad.front.samples)
                    vad.pop()
                    recognizer.decode_stream(stream)
                    content = stream.result.text.strip()
                    if content:
                        parts.append(content)

            # Stream file input and let VAD split pauses / long monologues.
            # Qt may produce stereo 48 kHz; resampling never changes the WAV.
            with sf.SoundFile(str(audio_path)) as source:
                if len(source) == 0:
                    raise TranscriptionError("录音中没有音频，请重新录音或直接输入文字。")
                divisor = math.gcd(source.samplerate, 16000)
                # Eight seconds resamples to 128000 samples: exactly 250 VAD
                # windows. Feeding an entire block to Silero loses its speech
                # boundaries; it expects 512-sample windows, not whole files.
                window_size = config.silero_vad.window_size
                for block in source.blocks(blocksize=source.samplerate * 8, dtype="float32", always_2d=True):
                    samples = block.mean(axis=1)
                    if source.samplerate != 16000:
                        samples = resample_poly(samples, 16000 // divisor, source.samplerate // divisor).astype(np.float32)
                    for offset in range(0, len(samples), window_size):
                        window = samples[offset:offset + window_size]
                        if len(window) < window_size:
                            window = np.pad(window, (0, window_size - len(window)))
                        vad.accept_waveform(window)
                        decode_segments()
                vad.flush()
                decode_segments()
            transcript = "\n".join(parts).strip()
            if not transcript:
                raise TranscriptionError("没有识别到清晰的人声。请检查麦克风音量后重新录音，或直接输入文字。")
            return transcript
        except TranscriptionError:
            raise
        except Exception as error:
            raise TranscriptionError(
                f"本地转录失败（{type(error).__name__}）。请检查录音或重试；音频没有上传，也不会改用远程服务。"
            ) from error
