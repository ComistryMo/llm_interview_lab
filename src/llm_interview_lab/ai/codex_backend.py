"""Official Codex App Server stdio integration for the desktop client."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any, AsyncIterator, Awaitable, Callable

from llm_interview_lab import __version__


class CodexBackendError(RuntimeError):
    """Raised for App Server transport or protocol failures."""


def discover_codex_executable(configured: str | Path | None = None) -> str | None:
    """Find Codex without assuming a Finder-launched macOS app inherited shell PATH."""

    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured).expanduser())
    discovered = shutil.which("codex")
    if discovered:
        candidates.append(Path(discovered))
    home = Path.home()
    if sys.platform == "darwin":
        candidates.extend(
            [
                Path("/opt/homebrew/bin/codex"),
                Path("/usr/local/bin/codex"),
                home / ".local/bin/codex",
                home / ".npm-global/bin/codex",
                home / ".volta/bin/codex",
                home / ".bun/bin/codex",
            ]
        )
    elif sys.platform == "win32":
        app_data = os.environ.get("APPDATA")
        local_data = os.environ.get("LOCALAPPDATA")
        if app_data:
            candidates.append(Path(app_data) / "npm/codex.cmd")
        if local_data:
            candidates.append(Path(local_data) / "Programs/codex/codex.exe")
    else:
        candidates.extend(
            [
                Path("/usr/local/bin/codex"),
                home / ".local/bin/codex",
                home / ".npm-global/bin/codex",
                home / ".volta/bin/codex",
            ]
        )
    for candidate in candidates:
        try:
            resolved = candidate.resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        if resolved.is_file() and (sys.platform == "win32" or os.access(resolved, os.X_OK)):
            return str(resolved)
    return None


@dataclass(frozen=True)
class CodexEvent:
    method: str
    params: dict[str, Any]
    request_id: int | str | None = None

    @property
    def requires_approval(self) -> bool:
        return self.request_id is not None and self.method in {
            "item/commandExecution/requestApproval",
            "item/fileChange/requestApproval",
        }


class CodexAppServerBackend:
    """A small JSONL client; it never parses the interactive Codex terminal UI."""

    def __init__(
        self,
        workspace_root: Path,
        *,
        executable: str | Path | None = None,
        process_factory: Callable[..., Awaitable[Any]] | None = None,
    ) -> None:
        self.workspace_root = workspace_root.resolve()
        self.executable = str(executable) if executable else "codex"
        self._configured_executable = executable
        self._process_factory = process_factory or asyncio.create_subprocess_exec
        self._process: Any | None = None
        self._reader_task: asyncio.Task | None = None
        self._pending: dict[int, asyncio.Future] = {}
        self._events: asyncio.Queue[CodexEvent] = asyncio.Queue()
        self._next_request_id = 1
        # ``events()`` is consumed by the Controller's transport pump.  A
        # process EOF must wake that consumer; otherwise it would remain
        # blocked on ``Queue.get`` while the UI still advertises a live Codex
        # connection.  Keep the marker private to this transport and let the
        # async generator turn it into a normal StopAsyncIteration.
        self._closed_marker_enqueued = False

    def _mark_closed(self, message: str) -> None:
        """Wake event consumers exactly once when the App Server disappears."""

        if self._closed_marker_enqueued:
            return
        self._closed_marker_enqueued = True
        try:
            self._events.put_nowait(CodexEvent("transport/closed", {"message": message}))
        except asyncio.QueueFull:
            # The queue is unbounded today, but a defensive fallback keeps a
            # close path from masking the original transport failure if that
            # implementation detail changes later.
            pass

    def available(self) -> bool:
        return discover_codex_executable(self._configured_executable) is not None

    async def connect(self) -> dict[str, Any]:
        if self._process is not None:
            raise CodexBackendError("Codex App Server is already connected")
        resolved = discover_codex_executable(self._configured_executable)
        if resolved is None and self._process_factory is asyncio.create_subprocess_exec:
            raise CodexBackendError("Codex executable was not found")
        executable = resolved or self.executable
        try:
            command: tuple[str, ...] = (
                executable,
                "app-server",
                "--listen",
                "stdio://",
            )
            # ``codex`` installed through npm on Windows is commonly a
            # ``.cmd`` shim.  ``CreateProcess`` cannot execute that file
            # directly (WinError 193); route only the real subprocess path
            # through the system command interpreter.  Fake process factories
            # used by tests still receive the simple executable command.
            if (
                self._process_factory is asyncio.create_subprocess_exec
                and sys.platform == "win32"
                and Path(executable).suffix.lower() in {".cmd", ".bat"}
            ):
                command = (
                    os.environ.get("COMSPEC", "cmd.exe"),
                    "/d",
                    "/s",
                    "/c",
                    f'"{executable}" app-server --listen stdio://',
                )
            self._process = await self._process_factory(
                *command,
                cwd=str(self.workspace_root),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                # App Server can write diagnostics for the lifetime of the process.
                # Do not leave an unread PIPE that could eventually deadlock it.
                stderr=asyncio.subprocess.DEVNULL,
            )
        except OSError as error:
            raise CodexBackendError("Codex App Server could not be started") from error
        # A backend instance is normally one-shot, but resetting the marker
        # makes an explicit reconnect safe for test/fallback adapters too.
        while True:
            try:
                self._events.get_nowait()
            except asyncio.QueueEmpty:
                break
        self._closed_marker_enqueued = False
        self._reader_task = asyncio.create_task(self._read_loop())
        result = await self.request(
            "initialize",
            {
                "clientInfo": {
                    "name": "llm_interview_lab",
                    "title": "LLM Interview Lab",
                    "version": __version__,
                },
                "capabilities": {"experimentalApi": False},
            },
        )
        await self.notify("initialized", {})
        return result

    async def _send(self, value: dict[str, Any]) -> None:
        if self._process is None or self._process.stdin is None:
            raise CodexBackendError("Codex App Server is not connected")
        self._process.stdin.write(
            (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        )
        await self._process.stdin.drain()

    async def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request_id = self._next_request_id
        self._next_request_id += 1
        future = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future
        try:
            await self._send(
                {"id": request_id, "method": method, "params": params or {}}
            )
        except Exception:
            self._pending.pop(request_id, None)
            raise
        try:
            return await asyncio.wait_for(future, timeout=30)
        except asyncio.TimeoutError as error:
            self._pending.pop(request_id, None)
            raise CodexBackendError(f"Codex request timed out: {method}") from error
        except asyncio.CancelledError:
            self._pending.pop(request_id, None)
            raise

    async def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        await self._send({"method": method, "params": params or {}})

    async def _read_loop(self) -> None:
        assert self._process is not None and self._process.stdout is not None
        try:
            while True:
                line = await self._process.stdout.readline()
                if not line:
                    error = CodexBackendError("Codex App Server closed its event stream")
                    for future in self._pending.values():
                        if not future.done():
                            future.set_exception(error)
                    self._pending.clear()
                    self._mark_closed(str(error))
                    # Make the public connection state agree with the EOF.
                    # ``events`` consumes the marker before returning, while
                    # callers can still inspect ``_process`` to see that the
                    # transport is gone.
                    self._process = None
                    return
                try:
                    message = json.loads(line.decode("utf-8"))
                except (UnicodeError, json.JSONDecodeError):
                    await self._events.put(CodexEvent("transport/error", {"message": "invalid App Server JSON"}))
                    continue
                request_id = message.get("id")
                if request_id in self._pending and ("result" in message or "error" in message):
                    future = self._pending.pop(request_id)
                    if "error" in message:
                        value = message["error"]
                        detail = value.get("message") if isinstance(value, dict) else value
                        future.set_exception(
                            CodexBackendError(str(detail or "Codex request failed"))
                        )
                    else:
                        future.set_result(message.get("result", {}))
                    continue
                method = message.get("method")
                if isinstance(method, str):
                    await self._events.put(
                        CodexEvent(method, message.get("params") or {}, request_id)
                    )
        except asyncio.CancelledError:
            # ``close`` deliberately cancels the reader.  It still enqueues a
            # marker there so a concurrent ``events()`` consumer is released.
            raise
        except Exception as error:
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(CodexBackendError("Codex App Server transport failed"))
            self._pending.clear()
            self._mark_closed(str(error))
            self._process = None

    async def account(self) -> dict[str, Any]:
        return await self.request("account/read", {"refreshToken": False})

    async def start_thread(
        self,
        *,
        model: str | None = None,
        mode: str = "coach",
    ) -> dict[str, Any]:
        if mode not in {"coach", "reviewer", "interviewer", "repository_agent"}:
            raise CodexBackendError("unsupported Codex mode")
        params: dict[str, Any] = {
            "cwd": str(self.workspace_root),
            "approvalPolicy": "untrusted" if mode == "repository_agent" else "never",
            "sandbox": "workspaceWrite" if mode == "repository_agent" else "readOnly",
        }
        if model:
            params["model"] = model
        return await self.request("thread/start", params)

    async def resume_thread(self, thread_id: str) -> dict[str, Any]:
        return await self.request("thread/resume", {"threadId": thread_id})

    async def start_turn(self, thread_id: str, text: str) -> dict[str, Any]:
        return await self.request(
            "turn/start",
            {"threadId": thread_id, "input": [{"type": "text", "text": text}]},
        )

    async def interrupt(self, thread_id: str, turn_id: str) -> dict[str, Any]:
        return await self.request(
            "turn/interrupt", {"threadId": thread_id, "turnId": turn_id}
        )

    async def resolve_approval(self, request_id: int | str, decision: str) -> None:
        if decision not in {"accept", "acceptForSession", "decline", "cancel"}:
            raise CodexBackendError("unsupported approval decision")
        await self._send({"id": request_id, "result": {"decision": decision}})

    async def events(self) -> AsyncIterator[CodexEvent]:
        while True:
            if self._process is None and self._events.empty():
                return
            event = await self._events.get()
            if event.method == "transport/closed":
                return
            yield event

    async def close(self) -> None:
        process, self._process = self._process, None
        self._mark_closed("Codex App Server connection closed")
        if self._reader_task is not None:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
            self._reader_task = None
        if process is not None:
            if process.stdin is not None:
                process.stdin.close()
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=3)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
