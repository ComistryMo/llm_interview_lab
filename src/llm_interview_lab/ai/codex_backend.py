"""Official Codex App Server stdio integration for the desktop client."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
from pathlib import Path
import shutil
from typing import Any, AsyncIterator, Awaitable, Callable


class CodexBackendError(RuntimeError):
    """Raised for App Server transport or protocol failures."""


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
        executable: str = "codex",
        process_factory: Callable[..., Awaitable[Any]] | None = None,
    ) -> None:
        self.workspace_root = workspace_root.resolve()
        self.executable = executable
        self._process_factory = process_factory or asyncio.create_subprocess_exec
        self._process: Any | None = None
        self._reader_task: asyncio.Task | None = None
        self._pending: dict[int, asyncio.Future] = {}
        self._events: asyncio.Queue[CodexEvent] = asyncio.Queue()
        self._next_request_id = 1

    def available(self) -> bool:
        return shutil.which(self.executable) is not None

    async def connect(self) -> dict[str, Any]:
        if self._process is not None:
            raise CodexBackendError("Codex App Server is already connected")
        if not self.available() and self._process_factory is asyncio.create_subprocess_exec:
            raise CodexBackendError("Codex executable was not found")
        try:
            self._process = await self._process_factory(
                self.executable,
                "app-server",
                "--listen",
                "stdio://",
                cwd=str(self.workspace_root),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                # App Server can write diagnostics for the lifetime of the process.
                # Do not leave an unread PIPE that could eventually deadlock it.
                stderr=asyncio.subprocess.DEVNULL,
            )
        except OSError as error:
            raise CodexBackendError("Codex App Server could not be started") from error
        self._reader_task = asyncio.create_task(self._read_loop())
        result = await self.request(
            "initialize",
            {
                "clientInfo": {
                    "name": "llm_interview_lab",
                    "title": "LLM Interview Lab",
                    "version": "0.4.0-alpha.1",
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
        while True:
            line = await self._process.stdout.readline()
            if not line:
                error = CodexBackendError("Codex App Server closed its event stream")
                for future in self._pending.values():
                    if not future.done():
                        future.set_exception(error)
                self._pending.clear()
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
        while self._process is not None:
            yield await self._events.get()

    async def close(self) -> None:
        process, self._process = self._process, None
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
