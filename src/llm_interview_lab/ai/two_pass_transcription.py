"""Worker-only PCM preview and acoustic-pause correction, without UI state."""

from concurrent.futures import Future
from math import gcd

from .transcription import TranscriptionError


def mono_16k(blocks, cancel):
    """Downmix PCM16 and resample with continuous filter context when needed.

    Microphones normally provide 16 kHz. Preferred-format devices may instead
    deliver 44.1/48 kHz in arbitrarily sized chunks. Keep 10 ms filter context
    on both sides of each 100 ms block, not a discontinuity at every callback.
    """
    import numpy as np

    rate = None
    buffered = np.empty(0, dtype=np.float32)
    for pcm, sample_rate, channels in blocks:
        if cancel.is_set():
            return
        if not pcm:
            yield np.empty(0, dtype=np.float32)  # Worker wake-up, not audio.
            continue
        if rate is None:
            rate = sample_rate
            if rate != 16000:
                from scipy.signal import resample_poly
            divisor = gcd(rate, 16000)
            up, down = 16000 // divisor, rate // divisor
            context = down * max(1, round(rate / 100 / down))
            step = down * max(1, round(rate / 10 / down))
            left = np.zeros(context, dtype=np.float32)
        if sample_rate != rate:
            raise TranscriptionError("录音采样率发生变化，请重新开始录音；已有文字保留。")
        samples = np.frombuffer(pcm, dtype="<i2").astype(np.float32).reshape(-1, channels).mean(axis=1) / 32768
        if rate == 16000:
            yield samples
            continue
        buffered = np.concatenate((buffered, samples))
        while len(buffered) >= step + context:
            wave = np.concatenate((left, buffered[:step + context]))
            result = resample_poly(wave, up, down)
            yield result[context * up // down:(context + step) * up // down]
            left = buffered[step - context:step].copy()
            buffered = buffered[step:]
    if rate and rate != 16000 and len(buffered) and not cancel.is_set():
        wave = np.concatenate((left, buffered, np.zeros(context, dtype=np.float32)))
        start = context * up // down
        count = (len(buffered) * up + down - 1) // down
        yield resample_poly(wave, up, down)[start:start + count]


def stream_two_pass(blocks, update, cancel, recognizer, vad, submit_correction):
    """Replace each segment's preview exactly once; never publish after cancel.

    Only this caller publishes cumulative text. Correction workers return
    values through per-recording futures, so a late old result cannot reach a
    subsequent recording. Waiting for native inference never blocks Qt.
    """
    import numpy as np

    stream = recognizer.create_stream()
    values: list[str] = []
    pending: dict[int, Future] = {}
    pcm_parts = []
    sample_count = 0
    current = previous = ""
    heard_speech = False

    def publish():
        nonlocal previous
        if cancel.is_set():
            return
        for key, future in list(pending.items()):
            if future.done():
                values[key] = future.result()
                del pending[key]
        text = "\n".join(value for value in [*values, current] if value)
        if text != previous and not cancel.is_set():
            previous = text
            update(text)

    def decode():
        nonlocal current
        while recognizer.is_ready(stream) and not cancel.is_set():
            recognizer.decode_stream(stream)
        current = recognizer.get_result(stream).strip()
        publish()

    def seal():
        nonlocal current, sample_count, heard_speech
        if sample_count and not cancel.is_set():
            key = len(values)
            values.append(current)
            pending[key] = submit_correction(np.concatenate(pcm_parts), cancel)
        pcm_parts.clear()
        sample_count = 0
        heard_speech = False
        current = ""
        recognizer.reset(stream)
        publish()

    try:
        if cancel.is_set():
            return ""
        update("")  # Preview is ready. Qwen loads separately on its own worker.
        for samples in mono_16k(blocks, cancel):
            if cancel.is_set():
                return ""
            if not len(samples):
                publish()
                continue
            pcm_parts.append(samples)
            sample_count += len(samples)
            stream.accept_waveform(16000, samples)
            decode()
            vad.accept_waveform(samples)
            heard_speech = heard_speech or vad.is_speech_detected()
            if not vad.empty():
                # VAD, never an empty ASR hypothesis, decides audio boundaries.
                while not vad.empty():
                    vad.pop()
                seal()
            elif not heard_speech and sample_count > 32000:
                # Bound idle microphone storage, retaining onset context even
                # before VAD's minimum speech duration is reached.
                tail = np.concatenate(pcm_parts)[-16000:]
                pcm_parts[:] = [tail]
                sample_count = len(tail)
        if cancel.is_set():
            return ""
        stream.accept_waveform(16000, np.zeros(9600, dtype=np.float32))
        stream.input_finished()
        decode()
        vad.flush()
        if not vad.empty():
            seal()  # Stop must include speech without a final silence gap.
        else:
            current = ""  # Do not turn pure silence into Qwen hallucinations.
        while pending and not cancel.is_set():
            publish()
            cancel.wait(0.03)
        if cancel.is_set():
            return ""
        publish()
        if not previous.strip():
            raise TranscriptionError("没有识别到清晰的人声。请检查麦克风音量后重新录音，或直接输入文字。")
        return previous.strip()
    finally:
        # cancel() skips queued jobs; running native inference may finish, but
        # nobody consumes its result. Do not join it on Stop/cancel/Qt shutdown.
        for future in pending.values():
            future.cancel()
