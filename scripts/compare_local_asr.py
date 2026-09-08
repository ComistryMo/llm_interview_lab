"""Explicit, local-only ASR comparison; never opens a Profile or microphone.

Use a JSON manifest with cases: id, audio path, reference (optional), terms.
Synthetic speech measures repeatability, not accuracy on a real speaker.
Model acquisition is separate. No downloads, API calls, or app-setting writes.

Audio paths are relative to the manifest. Example:
{"cases": [{"id": "sample", "audio": "sample.wav", "reference": "你好"}]}
Omit reference when no independently verified transcript exists.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import socket
import time
import unicodedata

import numpy as np
import sherpa_onnx
import soundfile as sf


def normalized(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKC", text).lower()
                   if c.isalnum())


def edit_distance(left: str, right: str) -> int:
    row = list(range(len(right) + 1))
    for i, first in enumerate(left, 1):
        next_row = [i]
        for j, second in enumerate(right, 1):
            next_row.append(min(next_row[-1] + 1, row[j] + 1,
                                row[j - 1] + (first != second)))
        row = next_row
    return row[-1]


def peak_memory_mb() -> float | None:
    if os.name != "nt":
        return None
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in
            ("peak", "working", "peak_paged", "paged", "peak_nonpaged", "nonpaged", "pagefile", "peak_pagefile")]

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    process = ctypes.windll.kernel32.GetCurrentProcess
    process.restype = wintypes.HANDLE
    get_info = ctypes.windll.psapi.GetProcessMemoryInfo
    get_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    if get_info(process(), ctypes.byref(counters), counters.cb):
        return round(counters.peak / 1024**2, 1)
    return None


def load_model(kind: str, root: Path, threads: int):
    if kind == "qwen":
        return sherpa_onnx.OfflineRecognizer.from_qwen3_asr(
            conv_frontend=str(root / "conv_frontend.onnx"),
            encoder=str(root / "encoder.int8.onnx"),
            decoder=str(root / "decoder.int8.onnx"),
            tokenizer=str(root.parent / "tokenizer"),
            num_threads=threads, provider="cpu", max_new_tokens=256)
    if kind == "paraformer":
        return sherpa_onnx.OnlineRecognizer.from_paraformer(
            encoder=str(root / "encoder.int8.onnx"),
            decoder=str(root / "decoder.int8.onnx"),
            tokens=str(root / "tokens.txt"), num_threads=threads,
            provider="cpu", enable_endpoint_detection=True,
            rule2_min_trailing_silence=0.8, rule3_min_utterance_length=30)
    return sherpa_onnx.OnlineRecognizer.from_transducer(
        encoder=str(root / "encoder-epoch-99-avg-1.int8.onnx"),
        decoder=str(root / "decoder-epoch-99-avg-1.onnx"),
        joiner=str(root / "joiner-epoch-99-avg-1.int8.onnx"),
        tokens=str(root / "tokens.txt"), num_threads=threads, model_type="zipformer",
        provider="cpu", enable_endpoint_detection=True,
        rule2_min_trailing_silence=0.8, rule3_min_utterance_length=30)


def recognize(model, kind: str, samples, rate: int, realtime: bool):
    started = time.perf_counter()
    stream = model.create_stream()
    if kind == "qwen":
        # This ONNX interface is offline: do not label partial-file replay as streaming.
        stream.accept_waveform(rate, samples)
        model.decode_stream(stream)
        return stream.result.text.strip(), {
            "decode_seconds": time.perf_counter() - started,
            "first_partial_audio_seconds": None, "first_partial_wall_seconds": None,
            "partial_updates": 0, "streaming": False}
    parts, previous, updates = [], "", 0
    first_audio = first_wall = None
    step = rate // 10
    consumed = 0

    def drain(final=False):
        nonlocal previous, updates, first_audio, first_wall
        while model.is_ready(stream):
            model.decode_stream(stream)
        text = model.get_result(stream).strip()
        current = "\n".join(parts + ([text] if text else []))
        if current and current != previous:
            updates += 1
            if first_audio is None:
                first_audio, first_wall = consumed / rate, time.perf_counter() - started
            previous = current
        if not final and model.is_endpoint(stream):
            if text:
                parts.append(text)
            model.reset(stream)
        return current

    for offset in range(0, len(samples), step):
        block = samples[offset:offset + step]
        consumed += len(block)
        if realtime:
            time.sleep(max(0, consumed / rate - (time.perf_counter() - started)))
        stream.accept_waveform(rate, block)
        drain()
    stop_started = time.perf_counter()
    stream.accept_waveform(rate, np.zeros(int(rate * 0.6), dtype=np.float32))
    stream.input_finished()
    text = drain(final=True)
    elapsed = time.perf_counter() - started
    return text, {"decode_seconds": elapsed,
                  "first_partial_audio_seconds": first_audio,
                  "first_partial_wall_seconds": first_wall,
                  "tail_seconds": time.perf_counter() - stop_started,
                  "partial_updates": updates, "streaming": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", required=True, choices=("zipformer", "paraformer", "qwen"))
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--realtime", action="store_true")
    args = parser.parse_args()
    if args.kind == "qwen" and args.realtime:
        parser.error("The tested Qwen ONNX interface is offline, not streaming")

    def no_network(*_args, **_kwargs):
        raise RuntimeError("Network is disabled for this local inference experiment")

    socket.socket.connect = no_network
    socket.socket.connect_ex = no_network
    cases = json.loads(args.manifest.read_text(encoding="utf-8"))["cases"]
    if args.limit:
        cases = cases[:args.limit]
    started = time.perf_counter()
    model = load_model(args.kind, args.model_root, args.threads)
    report = {"model": args.model_root.name, "kind": args.kind,
              "sherpa_onnx": sherpa_onnx.__version__, "threads": args.threads,
              "load_seconds": time.perf_counter() - started,
              "realtime_replay": args.realtime, "results": []}
    print(json.dumps({k: v for k, v in report.items() if k != "results"}), flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for case in cases:
        audio = (args.manifest.parent / case["audio"]).resolve()
        samples, rate = sf.read(audio, dtype="float32", always_2d=True)
        samples = samples.mean(axis=1)
        text, timing = recognize(model, args.kind, samples, rate, args.realtime)
        row = {"id": case["id"], "kind": case.get("kind", "public_audio"),
               "audio_sha256": hashlib.sha256(audio.read_bytes()).hexdigest(),
               "audio_seconds": len(samples) / rate, "text": text, **timing}
        if not args.realtime:
            row["rtf"] = timing["decode_seconds"] / row["audio_seconds"]
        if case.get("reference"):
            expected, actual = normalized(case["reference"]), normalized(text)
            row.update(reference=case["reference"], reference_chars=len(expected),
                       edit_errors=edit_distance(expected, actual))
            row["cer"] = row["edit_errors"] / len(expected)
            row["terms"] = {term: normalized(term) in actual for term in case.get("terms", [])}
        report["results"].append(row)
        report["peak_working_set_mb"] = peak_memory_mb()
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(row, ensure_ascii=False), flush=True)
    print("COMPLETED", args.output, flush=True)


if __name__ == "__main__":
    main()
