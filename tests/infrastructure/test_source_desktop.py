"""The source runner selects this checkout without building or clearing data."""
import os
from pathlib import Path
import sys

from scripts import run_desktop


def environment(tmp_path, monkeypatch):
    root = tmp_path / "checkout with spaces"
    python = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    python.parent.mkdir(parents=True)
    python.touch()
    monkeypatch.setattr(run_desktop, "ROOT", root)
    return root, python


def test_source_run_uses_checkout_and_preserves_data(tmp_path, monkeypatch):
    root, python = environment(tmp_path, monkeypatch)
    data = tmp_path / "existing data"
    data.mkdir()
    marker = data / "keep.txt"
    marker.write_text("synthetic saved data")
    monkeypatch.setenv("LLM_LAB_DESKTOP_DATA_ROOT", str(data))
    monkeypatch.setenv("LLM_LAB_PACKAGED", "1")
    monkeypatch.setenv("PYTHONPATH", "another-checkout")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    calls = []
    monkeypatch.setattr(run_desktop.subprocess, "call", lambda args, **kwargs: calls.append((args, kwargs)) or 0)
    assert run_desktop.main(["--window-size", "1080x680"]) == 0
    arguments, context = calls[0]
    assert arguments == [str(python), "-m", "llm_interview_lab.desktop.main", "--window-size", "1080x680"]
    assert context["cwd"] == root
    assert context["env"]["PYTHONPATH"] == str(root / "src")
    assert context["env"]["LLM_LAB_DESKTOP_DATA_ROOT"] == str(data.resolve())
    assert "LLM_LAB_PACKAGED" not in context["env"]
    if sys.platform in {"win32", "darwin"}:
        assert context["env"]["QT_QPA_PLATFORM"] == ("windows" if sys.platform == "win32" else "cocoa")
    assert marker.read_text() == "synthetic saved data"


def test_setup_is_explicit_editable_install_not_a_build(tmp_path, monkeypatch):
    root, python = environment(tmp_path, monkeypatch)
    calls = []
    monkeypatch.setattr(run_desktop.subprocess, "call", lambda args, **kwargs: calls.append(args) or 0)
    monkeypatch.setattr(run_desktop.venv, "EnvBuilder", lambda **kwargs: (_ for _ in ()).throw(AssertionError("existing venv must not be recreated")))
    assert run_desktop.main(["--setup"]) == 0
    assert calls == [[str(python), "-m", "pip", "install", "-e", ".[desktop,ai,dev]"]]


def test_custom_data_and_smoke_mode_are_forwarded(tmp_path, monkeypatch):
    root, _ = environment(tmp_path, monkeypatch)
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("LLM_LAB_DESKTOP_DATA_ROOT", "ignored-by-explicit-option")
    custom = tmp_path / "isolated"
    def run(args, **kwargs):
        assert args[-1] == "--smoke-test"
        assert kwargs["env"]["QT_QPA_PLATFORM"] == "offscreen"
        assert kwargs["env"]["LLM_LAB_DESKTOP_DATA_ROOT"] == str(custom.resolve())
        return 7
    monkeypatch.setattr(run_desktop.subprocess, "call", run)
    assert run_desktop.main(["--data-root", str(custom), "--smoke-test"]) == 7
    assert not custom.exists()


def test_missing_environment_does_not_install_implicitly(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(run_desktop, "ROOT", tmp_path)
    assert run_desktop.main([]) == 1
    assert "--setup" in capsys.readouterr().err
    assert not (tmp_path / ".venv").exists()
