"""Windows-first Qt Quick entry point."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from llm_interview_lab import __version__


def _grader_worker(arguments: list[str]) -> int:
    import pytest

    return int(pytest.main(arguments))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="llm-lab-gui")
    parser.add_argument("--profile", default="default")
    parser.add_argument("--version", action="store_true")
    parser.add_argument(
        "--screenshot",
        metavar="PATH",
        help="render the selected synthetic demo page to a PNG and exit",
    )
    parser.add_argument(
        "--screenshot-page",
        choices=("onboarding", "home", "exercise", "interview", "connections"),
        default="home",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "--grader-worker":
        return _grader_worker(arguments[1:])
    args = _parser().parse_args(arguments)
    if args.version:
        print(f"llm-lab-gui {__version__}")
        return 0
    if args.screenshot:
        os.environ.setdefault("QT_QUICK_BACKEND", "software")
    from PySide6.QtCore import QTimer, QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine

    from llm_interview_lab.desktop.controller import AppController
    from llm_interview_lab.desktop.runtime import prepare_desktop_repository

    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Material")
    if getattr(sys, "frozen", False) or "__compiled__" in globals():
        # Nuitka places one-file data beside the entry module in its temporary
        # extraction directory.  Keep runtime asset discovery independent of
        # the imported package module's synthetic ``__file__`` value.
        os.environ.setdefault(
            "LLM_LAB_BUNDLE_ROOT",
            str(Path(__file__).resolve().parent / "runtime_assets"),
        )
    app = QGuiApplication([sys.argv[0]])
    app.setApplicationName("LLM Interview Lab")
    app.setOrganizationName("ComistryMo")
    try:
        repo_root = prepare_desktop_repository()
        controller = AppController(
            repo_root,
            profile_id=args.profile,
            demo_page=args.screenshot_page if args.screenshot else None,
        )
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    engine = QQmlApplicationEngine()
    engine.warnings.connect(
        lambda warnings: [print(f"QML: {warning.toString()}", file=sys.stderr) for warning in warnings]
    )
    engine.rootContext().setContextProperty("backend", controller)
    qml_path = Path(__file__).parent / "qml/Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        print("ERROR: desktop UI could not be loaded", file=sys.stderr)
        return 2
    app.aboutToQuit.connect(controller.shutdown)

    if args.screenshot:
        destination = Path(args.screenshot).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)

        def capture() -> None:
            try:
                window = engine.rootObjects()[0]
                screen = window.screen() or QGuiApplication.primaryScreen()
                image = screen.grabWindow(window.winId())
                if image.isNull() or not image.save(str(destination), "PNG"):
                    raise RuntimeError("the rendered window could not be captured")
            except Exception as error:
                print(f"ERROR: screenshot could not be saved: {error}", file=sys.stderr)
                app.exit(2)
                return
            window.hide()
            window.deleteLater()
            QTimer.singleShot(0, app.quit)

        QTimer.singleShot(900, capture)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
