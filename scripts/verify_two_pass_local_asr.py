"""Isolated real-model two-pass experiment; not a production STT replacement.

Replays explicit public/synthetic WAVs on a Qt timer. A streaming worker owns
preview/endpointing; one independent worker corrects endpoint PCM with Qwen.
No microphone, Profile, API, download, or application-settings access.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import queue
import socket
import threading
import time

import numpy as np
from PySide6.QtCore import QCoreApplication, QTimer, Qt
import sherpa_onnx
import soundfile as sf

from compare_local_asr import edit_distance, load_model, normalized, peak_memory_mb


class Replay:
    """Test-only state, deliberately independent of application/Profile state."""

    def __init__(self, app, online, offline, cases, output, metadata, vad_config=None):
        self.app, self.online, self.offline = app, online, offline
        self.cases, self.output, self.report = iter(cases), output, metadata
        self.vad_config = vad_config
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.events, self.blocks = queue.Queue(), queue.Queue()
        self.timer = QTimer()
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.setInterval(20)
        self.timer.timeout.connect(self.tick)
        self.begin()

    def emit(self, kind, **values):
        self.events.put({"kind": kind, "wall_s": time.perf_counter() - self.started,
                         **values})

    def begin(self):
        case = next(self.cases, None)
        if case is None:
            self.timer.stop()
            self.app.quit()
            return
        self.case = case
        self.samples = case["samples"]
        self.position = 0
        self.eof = self.preview_done = False
        self.cancel = threading.Event()
        self.rows, self.event_log, self.gaps = {}, [], []
        self.skipped_spans = []
        self.preview_updates = self.preview_while_correcting = 0
        self.first_partial = self.cancel_at = None
        self.inflight = set()
        self.max_pending = self.ignored_late = 0
        self.base_draft = "保留原先手打的内容。"
        self.draft = self.base_draft
        self.typed_during_correction = False
        self.finalized = set()
        self.duplicate_final = 0
        self.started = self.previous_tick = time.perf_counter()
        self.worker = threading.Thread(target=self.preview, daemon=True)
        self.worker.start()
        self.timer.start()
        print(f"REPLAY {case['id']} {len(self.samples) / 16000:.3f}s", flush=True)

    def correct(self, segment_id, pcm):
        if self.cancel.is_set():
            self.emit("discarded", segment_id=segment_id)
            return
        self.emit("correcting", segment_id=segment_id)
        started = time.perf_counter()
        try:
            stream = self.offline.create_stream()
            stream.accept_waveform(16000, pcm)
            self.offline.decode_stream(stream)
            self.emit("corrected", segment_id=segment_id,
                      text=stream.result.text.strip(), decode_s=time.perf_counter() - started)
        except Exception as error:
            self.emit("failed", segment_id=segment_id, error=f"{type(error).__name__}: {error}")

    def preview(self):
        stream = self.online.create_stream()
        vad = (sherpa_onnx.VoiceActivityDetector(self.vad_config, buffer_size_in_seconds=60)
               if self.vad_config else None)
        start = end = segment_id = 0
        previous = ""
        pcm_blocks = []

        def decode():
            nonlocal previous
            while self.online.is_ready(stream) and not self.cancel.is_set():
                self.online.decode_stream(stream)
            text = self.online.get_result(stream).strip()
            if text and text != previous and not self.cancel.is_set():
                self.emit("partial", segment_id=segment_id, text=text, audio_s=end / 16000)
                previous = text
            return text

        def close_segment(text, reason, speech=False):
            nonlocal start, segment_id, previous
            if end == start:
                return
            if text or speech:
                pcm = np.concatenate(pcm_blocks)
                self.emit("segment", segment_id=segment_id, start=start, end=end,
                          preview=text, reason=reason,
                          pcm_sha256=hashlib.sha256(pcm.tobytes()).hexdigest())
                self.pool.submit(self.correct, segment_id, pcm)
                segment_id += 1
            else:
                self.emit("silence_span", start=start, end=end)
            start = end
            pcm_blocks.clear()
            previous = ""

        try:
            while not self.cancel.is_set():
                block = self.blocks.get()
                if block is None:
                    if not self.cancel.is_set():
                        stream.accept_waveform(16000, np.zeros(9600, dtype=np.float32))
                        stream.input_finished()
                        if vad:
                            vad.flush()
                        close_segment(decode(), "stop", speech=bool(vad and not vad.empty()))
                    break
                pcm_blocks.append(block)
                end += len(block)
                stream.accept_waveform(16000, block)
                text = decode()
                if vad:
                    vad.accept_waveform(block)
                    boundary = not vad.empty()
                    while not vad.empty():
                        vad.pop()
                else:
                    boundary = self.online.is_endpoint(stream)
                if boundary and not self.cancel.is_set():
                    close_segment(text, "vad" if vad else "endpoint", speech=bool(vad))
                    self.online.reset(stream)
            self.emit("preview_done")
        except Exception as error:
            self.emit("preview_failed", error=f"{type(error).__name__}: {error}")
            self.emit("preview_done")

    def tick(self):
        now = time.perf_counter()
        self.gaps.append(now - self.previous_tick)
        self.previous_tick = now
        elapsed = now - self.started
        # Replay only already elapsed audio; each block represents 100 ms.
        while not self.eof and self.position < len(self.samples):
            end = min(self.position + 1600, len(self.samples))
            if elapsed < end / 16000:
                break
            self.blocks.put(self.samples[self.position:end])
            self.position = end
        if not self.eof and self.position == len(self.samples):
            self.eof = True
            self.stop_at = elapsed
            self.blocks.put(None)
        while not self.events.empty():
            event = self.events.get_nowait()
            self.event_log.append(event)
            kind, key = event["kind"], event.get("segment_id")
            if kind == "partial":
                self.preview_updates += 1
                if self.first_partial is None:
                    self.first_partial = event["wall_s"]
                if self.inflight:
                    self.preview_while_correcting += 1
            elif kind == "segment":
                self.rows[key] = {**event, "text": event["preview"]}
                self.max_pending = max(self.max_pending, len(self.rows) - len(self.finalized))
            elif kind == "silence_span":
                self.skipped_spans.append(event)
            elif kind == "correcting":
                self.inflight.add(key)
                if not self.typed_during_correction:
                    self.draft += "录音期间手打的补充。"
                    self.typed_during_correction = True
                if self.case.get("cancel_on_correction") and self.cancel_at is None:
                    self.cancel_at = time.perf_counter() - self.started
                    self.cancel.set()
                    self.eof = True
                    self.stop_at = self.cancel_at
                    self.blocks.put(None)
            elif kind in ("corrected", "failed", "discarded"):
                self.inflight.discard(key)
                if key in self.finalized:
                    self.duplicate_final += 1
                self.finalized.add(key)
                self.rows[key]["completion"] = event
                self.rows[key]["endpoint_to_completion_s"] = event["wall_s"] - self.rows[key]["wall_s"]
                if self.cancel.is_set():
                    self.ignored_late += 1
                elif kind == "corrected" and event["text"]:
                    # Replace by immutable segment ID, never append both hypotheses.
                    self.rows[key]["text"] = event["text"]
            elif kind == "preview_done":
                self.preview_done = True
        if self.preview_done and len(self.finalized) == len(self.rows):
            self.finish()

    def finish(self):
        self.timer.stop()
        self.worker.join(timeout=0)
        ordered = [self.rows[key] for key in sorted(self.rows)]
        baseline = "\n".join(row["preview"] for row in ordered)
        corrected = "" if self.cancel.is_set() else "\n".join(row["text"] for row in ordered)
        expected_draft = self.base_draft + ("录音期间手打的补充。" if self.typed_during_correction else "")
        spans = sorted(ordered + self.skipped_spans, key=lambda row: row["start"])
        coverage = (not spans and self.position == 0) or bool(
            spans and spans[0]["start"] == 0
            and spans[-1]["end"] == self.position
            and all(left["end"] == right["start"] for left, right in zip(spans, spans[1:])))
        pcm_matches = all(row["pcm_sha256"] == hashlib.sha256(
            self.samples[row["start"]:row["end"]].tobytes()).hexdigest() for row in ordered)
        failures = [e for e in self.event_log if e["kind"] in ("failed", "preview_failed")]
        row = {
            "id": self.case["id"], "audio_seconds": len(self.samples) / 16000,
            "source_audio_sha256": self.case["source_audio_sha256"],
            "pcm_sha256": hashlib.sha256(self.samples.tobytes()).hexdigest(),
            "cancelled": self.cancel.is_set(), "cancel_at_s": self.cancel_at,
            "first_preview_s": self.first_partial,
            "preview_updates": self.preview_updates,
            "preview_updates_while_correcting": self.preview_while_correcting,
            "pending_segments_max": self.max_pending,
            "qt_heartbeat_max_gap_s": max(self.gaps),
            "qt_heartbeat_p95_gap_s": float(np.percentile(self.gaps, 95)),
            "stop_to_drain_s": time.perf_counter() - self.started - self.stop_at,
            "late_corrections_ignored": self.ignored_late,
            "no_duplicate_segment_final": self.duplicate_final == 0,
            "draft_preserved": self.draft == expected_draft,
            "all_audio_ranges_accounted": coverage, "correction_pcm_matches": pcm_matches,
            "preview_text": baseline, "final_text": corrected,
            "segments": ordered, "silence_spans": self.skipped_spans,
            "failures": failures, "events": self.event_log,
        }
        if self.case.get("reference") and not self.cancel.is_set():
            reference = normalized(self.case["reference"])
            row["reference"] = self.case["reference"]
            row["reference_chars"] = len(reference)
            row["preview_errors"] = edit_distance(reference, normalized(baseline))
            row["corrected_errors"] = edit_distance(reference, normalized(corrected))
        self.report["results"].append(row)
        self.report["peak_working_set_mb"] = peak_memory_mb()
        self.output.write_text(json.dumps(self.report, ensure_ascii=False, indent=2), encoding="utf-8")
        summary = {key: value for key, value in row.items() if key not in
                   ("events", "segments", "silence_spans", "reference", "source_audio_sha256")}
        print(json.dumps(summary, ensure_ascii=False), flush=True)
        QTimer.singleShot(0, self.begin)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview-model", type=Path, required=True)
    parser.add_argument("--qwen-model", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--vad-model", type=Path,
                        help="Use acoustic pauses, not preview decoding, to split correction audio")
    parser.add_argument("--case", action="append")
    args = parser.parse_args()

    def no_network(*_args, **_kwargs):
        raise RuntimeError("Network disabled for local inference verification")

    socket.socket.connect = socket.socket.connect_ex = no_network
    source = json.loads(args.manifest.read_text(encoding="utf-8"))
    clips, shas = {}, {}
    for item in source["cases"]:
        path = args.manifest.parent / item["audio"]
        samples, rate = sf.read(path, dtype="float32", always_2d=True)
        if rate != 16000:
            raise ValueError(f"This replay fixture must be 16 kHz: {item['id']}")
        clips[item["id"]] = samples.mean(axis=1)
        shas[item["id"]] = hashlib.sha256(path.read_bytes()).hexdigest()
    synthetic = [item for item in source["cases"] if item.get("reference")]
    public = [item for item in source["cases"] if not item.get("reference")]

    def joined(name, items, gap):
        silence = np.zeros(round(16000 * gap), dtype=np.float32)
        return {"id": name, "samples": np.concatenate([
            part for item in items for part in (clips[item["id"]], silence)]),
            "reference": "".join(item.get("reference", "") for item in items),
            "source_audio_sha256": {item["id"]: shas[item["id"]] for item in items}}

    cases = [joined("normal-pauses", synthetic, 1.2),
             joined("short-pauses", synthetic, 0.25),
             joined("public-speech", public, 1.2),
             joined("stop-without-pause", synthetic[:1], 0),
             {"id": "silence", "samples": np.zeros(48000, dtype=np.float32),
              "source_audio_sha256": {}},
             {**joined("cancel-inflight", synthetic[:1], 1.2), "cancel_on_correction": True},
             joined("restart-after-cancel", synthetic[1:2], 1.2)]
    if args.case:
        cases = [case for case in cases if case["id"] in args.case]
        if len(cases) != len(set(args.case)):
            parser.error("Unknown or duplicate case selection")
    load_started = time.perf_counter()
    online = load_model("zipformer", args.preview_model, 2)
    preview_load_s = time.perf_counter() - load_started
    load_started = time.perf_counter()
    offline = load_model("qwen", args.qwen_model, 2)
    metadata = {"kind": "isolated_two_pass_probe", "threads_per_model": 2,
                "preview_model": args.preview_model.name, "correction_model": args.qwen_model.name,
                "preview_load_s": preview_load_s,
                "correction_load_s": time.perf_counter() - load_started,
                "results": []}
    vad_config = None
    if args.vad_model:
        vad_config = sherpa_onnx.VadModelConfig()
        vad_config.silero_vad.model = str(args.vad_model)
        vad_config.silero_vad.min_silence_duration = 0.8
        vad_config.silero_vad.min_speech_duration = 0.25
        vad_config.silero_vad.max_speech_duration = 30
        vad_config.sample_rate = 16000
        vad_config.num_threads = 1
        metadata["vad"] = {"model": args.vad_model.name,
                           "sha256": hashlib.sha256(args.vad_model.read_bytes()).hexdigest(),
                           "threshold": 0.5, "min_speech_s": 0.25,
                           "min_silence_s": 0.8, "max_speech_s": 30}
    print(json.dumps(metadata), flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    app = QCoreApplication([])
    replay = Replay(app, online, offline, cases, args.output, metadata, vad_config)
    app.exec()
    replay.pool.shutdown(wait=True)
    print("COMPLETED", args.output, flush=True)


if __name__ == "__main__":
    main()
