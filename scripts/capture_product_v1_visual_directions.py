#!/usr/bin/env python3
"""Capture the isolated Product V1 visual-direction prototypes.

The harness intentionally loads only the presentation prototype.  It does not
construct AppController, open a Profile, or invoke any curriculum/grader code.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

# Make source checkouts work without requiring an editable install.
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QFont, QFontDatabase, QImage
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
import shiboken6


DIRECTIONS = ("graphite-blue", "obsidian-violet", "warm-frost")
THEMES = ("light", "dark")
NAMES = {
    ("graphite-blue", "light"): "graphite-blue-light.png",
    ("graphite-blue", "dark"): "graphite-blue-dark.png",
    ("obsidian-violet", "light"): "obsidian-violet-light.png",
    ("obsidian-violet", "dark"): "obsidian-violet-dark.png",
    ("warm-frost", "light"): "warm-frost-light.png",
    ("warm-frost", "dark"): "warm-frost-dark.png",
}


def _commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture six synthetic Product V1 workbench direction images."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "docs/images/product-v1",
    )
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=800)
    parser.add_argument("--settle-ms", type=int, default=160)
    return parser


def _capture(root, quick_window: QQuickWindow, path: Path, width: int, height: int) -> dict[str, object]:
    root.resize(width, height)
    root.show()
    app = QApplication.instance()
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        app.processEvents()
        if root.width() == width and root.height() == height:
            # Let layouts, fonts and the software scene settle without a long
            # process-wide delay.
            time.sleep(0.01)
            if time.monotonic() + 0.01 >= deadline:
                break
            if path.parent.exists():
                break
    image = quick_window.grabWindow()
    if image.isNull():
        raise RuntimeError(f"Qt Quick scene is empty: {path}")
    if image.width() != width or image.height() != height:
        expected_ratio = width / height
        actual_ratio = image.width() / image.height()
        if abs(expected_ratio - actual_ratio) > 0.01:
            raise RuntimeError(
                f"unexpected screenshot size for {path.name}: "
                f"{image.width()}x{image.height()} (expected {width}x{height})"
            )
        image = image.scaled(width, height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    if not image.save(str(path), "PNG"):
        raise RuntimeError(f"could not save screenshot: {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "path": path.relative_to(REPO_ROOT).as_posix(),
        "width": width,
        "height": height,
        "sha256": digest,
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.width < 960 or args.height < 620:
        raise SystemExit("prototype viewport must be at least 960x620")
    if args.settle_ms < 0:
        raise SystemExit("--settle-ms must be non-negative")
    # Windows' native platform plugin is needed for the installed CJK font
    # fallback.  Linux/macOS CI can use offscreen for a deterministic smoke.
    os.environ["QT_QPA_PLATFORM"] = "windows" if sys.platform == "win32" else "offscreen"
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    qml_path = (
        REPO_ROOT
        / "src/llm_interview_lab/desktop/qml/prototypes/ProductV1WorkbenchPrototype.qml"
    )

    app = QApplication([sys.argv[0]])
    # Match the production launcher’s best-effort CJK font selection.  This
    # keeps the evidence readable on Windows offscreen runners while falling
    # back to the platform default on macOS/Linux.
    families = set(QFontDatabase.families())
    for family in ("Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "WenQuanYi Zen Hei"):
        if family in families:
            app.setFont(QFont(family, 10))
            break
    engine = QQmlApplicationEngine()
    warnings: list[str] = []
    engine.warnings.connect(lambda values: warnings.extend(item.toString() for item in values))
    engine.rootContext().setContextProperty("prototypeDirection", "graphite-blue")
    engine.rootContext().setContextProperty("prototypeDark", False)
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    roots = engine.rootObjects()
    if not roots:
        details = "; ".join(warnings[-5:])
        raise RuntimeError(f"prototype QML did not create a root object: {details}")
    root = roots[0]
    quick_window = shiboken6.wrapInstance(
        shiboken6.getCppPointer(root)[0], QQuickWindow
    )
    captured: list[dict[str, object]] = []
    for direction in DIRECTIONS:
        for theme in THEMES:
            root.setProperty("prototypeDirection", direction)
            root.setProperty("prototypeDark", theme == "dark")
            app.processEvents()
            if args.settle_ms:
                end = time.monotonic() + args.settle_ms / 1000
                while time.monotonic() < end:
                    app.processEvents()
                    time.sleep(0.01)
            path = output_dir / NAMES[(direction, theme)]
            item = _capture(root, quick_window, path, args.width, args.height)
            item.update({"direction": direction, "theme": theme, "synthetic": True})
            captured.append(item)
    root.hide()
    root.deleteLater()
    app.processEvents()
    manifest = {
        "schema_version": 1,
        "synthetic": True,
        "language": "zh-CN",
        "prototype": "Product V1 Coding Workbench",
        "source_commit": _commit(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "viewport": f"{args.width}x{args.height}",
        "screenshots": captured,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
