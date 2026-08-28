"""Render the original SVG into Windows and macOS build-time icon assets."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


SIZES = (16, 32, 64, 128, 256, 512, 1024)


def render_png(source: Path, destination: Path, size: int) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    renderer = QSvgRenderer(str(source))
    if not renderer.isValid():
        raise RuntimeError("app icon SVG is invalid")
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(destination), "PNG"):
        raise RuntimeError(f"could not write {destination.name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("dist/icons"))
    parser.add_argument("--macos", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = root / "src/llm_interview_lab/desktop/resources/app-icon.svg"
    output = args.output.resolve()
    render_png(source, output / "app-icon-1024.png", 1024)
    render_png(source, output / "app-icon-256.png", 256)
    from PySide6.QtGui import QImage

    # The macOS build consumes only the iconset/ICNS.  Some Qt image plugin
    # bundles do not ship an ICO writer on Unix, so do not make an unrelated
    # Windows artefact a prerequisite for an Apple build.
    if not args.macos and not QImage(str(output / "app-icon-256.png")).save(
        str(output / "LLMInterviewLab.ico"), "ICO"
    ):
        raise RuntimeError("could not write Windows icon")
    if args.macos:
        iconset = output / "LLMInterviewLab.iconset"
        for size in (16, 32, 128, 256, 512):
            render_png(source, iconset / f"icon_{size}x{size}.png", size)
            render_png(source, iconset / f"icon_{size}x{size}@2x.png", size * 2)
        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset), "-o", str(output / "LLMInterviewLab.icns")],
            check=True,
        )
    print(output / ("LLMInterviewLab.icns" if args.macos else "app-icon-1024.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
