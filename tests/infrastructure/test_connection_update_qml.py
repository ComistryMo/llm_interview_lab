"""Production QML interaction with isolated Profile and no real network/keys."""
import json
import os
import hashlib
from pathlib import Path
import struct
import subprocess
import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QMetaObject, QPointF, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest

from llm_interview_lab.ai.connection_diagnostics import connection_diagnostic
from tests.infrastructure.test_interview_input_runtime import (
    qapp, public_repo, controller, scene, _find, _capture, _click, REPO,
)


def test_connection_diagnostic_and_update_controls_in_production_qml(scene, monkeypatch):
    window, app = scene
    app.navigate("connections")
    app._set_connection_failure(connection_diagnostic(FileNotFoundError("secret local path"), "init_client"))
    window.setWidth(1080)
    window.setHeight(680)
    QTest.qWait(100)
    error = _find(window, "connectionFormError")
    button = _find(window, "copyConnectionFormDiagnostic")
    assert error.property("visible") and button.property("visible")
    assert "AI_CONN_CLIENT_INIT" in error.property("text")
    assert error.height() >= error.property("implicitHeight") - 1
    copied = []
    class Clipboard:
        def setText(self, value): copied.append(value)
    monkeypatch.setattr(QGuiApplication, "clipboard", lambda: Clipboard())
    page = _find(window, "connectionsPage")
    page.setProperty("contentY", max(0, button.mapToItem(page, QPointF()).y() - page.height() + 80))
    QTest.qWait(100)
    _click(window, button)
    assert json.loads(copied[0])["code"] == "AI_CONN_CLIENT_INIT"
    assert "secret local path" not in copied[0]
    _capture(window, "connection-diagnostic-1080")
    app.clearConnectionError()
    app._connection_error = "找不到此连接"
    assert app.connectionDiagnostic == {}  # Do not attach a previous error's diagnostic.
    app.navigate("settings")
    QMetaObject.invokeMethod(_find(window, "globalToast"), "close", Qt.DirectConnection)
    manager = app.updateManager
    manager._change(status="prepared", release_version="v1.0.2", handoff="", downloaded_bytes=100,
                    reused_bytes=10000, message="合成更新已准备，仅用于界面验证。")
    QTest.qWait(80)
    install = _find(window, "installDesktopUpdate")
    assert install.property("visible") and install.property("enabled")
    settings = _find(window, "settingsPage")
    settings.setProperty("contentY", max(0, install.mapToItem(settings, QPointF()).y() - settings.height() + 80))
    QTest.qWait(100)
    _click(window, install)
    QTest.qWait(80)
    _capture(window, "update-install-confirmation-1080")
    manager._change(status="idle")
    directory = os.environ.get("LLM_LAB_UI_EVIDENCE_DIR")
    if directory:
        from llm_interview_lab import __version__
        destination = Path(directory)
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
        files = ["src/llm_interview_lab/desktop/" + name for name in (
            "controller.py", "updates.py", "qml/Main.qml", "qml/components/UpdateSettings.qml",
            "qml/components/LabDialog.qml", "qml/pages/ConnectionsPage.qml", "qml/pages/SettingsPage.qml")]
        images = []
        for name in ("connection-diagnostic-1080", "update-install-confirmation-1080"):
            raw = (destination / (name + ".png")).read_bytes()
            images.append({"path": "docs/images/source-alpha1/" + name + ".png", "synthetic": True,
                           "source_commit": commit, "sha256": hashlib.sha256(raw).hexdigest(),
                           "pixel_size": list(struct.unpack(">II", raw[16:24]))})
        manifest = {"version": __version__, "source_commit": commit, "synthetic": True,
                    "renderer": "Windows Qt / production AppController and QML; synthetic error and prepared update state, not a bundle install",
                    "logical_size": [1080, 680], "screenshots": images,
                    "source_inputs": {name: hashlib.sha256((REPO / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() for name in files}}
        (destination / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
