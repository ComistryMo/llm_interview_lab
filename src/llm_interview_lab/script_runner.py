"""Run trusted learner Python locally; this is not a security sandbox."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def run_local_python(path: Path, stdin: str = "", *, repo_root: Path, timeout: float = 30) -> dict:
    started = time.monotonic()
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    desktop_executable = os.environ.get("LLM_LAB_GRADER_EXECUTABLE")
    command = ([desktop_executable, "--script-worker", str(path)]
               if desktop_executable else [sys.executable, str(path)])
    with (tempfile.TemporaryFile(dir=path.parent) as source,
          tempfile.TemporaryFile(dir=path.parent) as out, tempfile.TemporaryFile(dir=path.parent) as err):
        source.write(stdin.encode("utf-8"))
        source.seek(0)
        with subprocess.Popen(
            command,
            stdin=source, stdout=out, stderr=err, cwd=path.parent, env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        ) as process:
            status = "finished"
            while True:
                try:
                    process.wait(timeout=0.05)
                    break
                except subprocess.TimeoutExpired:
                    if os.fstat(out.fileno()).st_size + os.fstat(err.fileno()).st_size > 64 * 1024:
                        status = "output_limited"
                    elif time.monotonic() - started >= timeout:
                        status = "timed_out"
                    else:
                        continue
                    process.kill()
                    process.wait()
                    break
            exit_code = process.returncode if status == "finished" else None
        out.seek(0)
        err.seek(0)
        stdout, stderr = out.read(32 * 1024), err.read(32 * 1024)
    def display(value):
        value = value.decode("utf-8", errors="replace").replace("\r\n", "\n")
        value = value.replace(str(path.parent), "<coding>").replace(str(repo_root), "<app>")
        return value[:8000] + ("\n[输出已截断]" if len(value) > 8000 else "")
    result = {"status": status, "exit_code": exit_code, "stdin": stdin,
              "stdout": display(stdout), "stderr": display(stderr),
              "duration_ms": round((time.monotonic() - started) * 1000)}
    if status == "output_limited":
        result["stderr"] = "输出超过 64 KB，已停止脚本；请检查循环或减少打印后重试。\n" + result["stderr"]
    return result
