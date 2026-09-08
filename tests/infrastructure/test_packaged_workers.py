"""Direct worker contracts behind the native no-Python acceptance regression."""
import os
from pathlib import Path
import subprocess
import sys

from llm_interview_lab.desktop import runtime

ROOT = Path(__file__).resolve().parents[2]


def test_compiled_worker_uses_running_app_not_nonexistent_python(tmp_path, monkeypatch):
    executable = tmp_path / "中文 应用" / "LLMInterviewLab.exe"
    executable.parent.mkdir()
    executable.touch()
    monkeypatch.setattr(runtime, "__compiled__", object(), raising=False)
    monkeypatch.setattr(runtime.sys, "argv", [str(executable)])
    monkeypatch.setattr(runtime.sys, "executable", str(executable.with_name("python.exe")))
    monkeypatch.setenv("LLM_LAB_BUNDLE_ROOT", str(ROOT))
    monkeypatch.setenv("LLM_LAB_DESKTOP_DATA_ROOT", str(tmp_path / "合成 数据"))
    monkeypatch.delenv("LLM_LAB_PACKAGED", raising=False)
    monkeypatch.setenv("LLM_LAB_GRADER_EXECUTABLE", "")
    runtime.prepare_desktop_repository()
    assert os.environ["LLM_LAB_GRADER_EXECUTABLE"] == str(executable.resolve())


def test_script_worker_accepts_stdin_imports_and_exit_codes(tmp_path):
    (tmp_path / "helper.py").write_text("factor = 2\n", encoding="utf-8")
    script = tmp_path / "自测 代码.py"
    script.write_text("from helper import factor\nprint(int(input()) * factor)\n", encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONUTF8": "1"}
    command = [sys.executable, "-m", "llm_interview_lab.desktop.main", "--script-worker", str(script)]
    result = subprocess.run(command, input="7\n", capture_output=True, text=True,
                            cwd=tmp_path, env=env, timeout=20)
    assert result.returncode == 0 and result.stdout.strip() == "14", result.stderr
    script.write_text("raise SystemExit(3)\n", encoding="utf-8")
    result = subprocess.run(command, capture_output=True, text=True, cwd=tmp_path, env=env, timeout=20)
    assert result.returncode == 3


def test_packaged_script_runner_uses_worker_protocol(tmp_path, monkeypatch):
    from llm_interview_lab import script_runner
    import pytest
    script = tmp_path / "script.py"
    script.write_text("print(9)\n", encoding="utf-8")
    monkeypatch.setenv("LLM_LAB_GRADER_EXECUTABLE", "synthetic-app.exe")
    def inspect(command, **kwargs):
        assert command == ["synthetic-app.exe", "--script-worker", str(script)]
        raise RuntimeError("command inspected")
    monkeypatch.setattr(script_runner.subprocess, "Popen", inspect)
    with pytest.raises(RuntimeError, match="command inspected"):
        script_runner.run_local_python(script, repo_root=tmp_path)


def test_both_platform_specs_include_all_pytest_runtime_plugins():
    for name in ("pysidedeploy.spec", "pysidedeploy-macos.spec"):
        spec = (ROOT / "scripts" / name).read_text(encoding="utf-8")
        for option in ("--include-package=_pytest", "--include-package=unittest",
                       "--noinclude-pytest-mode=allow", "--noinclude-unittest-mode=allow"):
            assert option in spec
