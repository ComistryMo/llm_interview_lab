"""Cross-platform Qt Quick entry point for the local desktop workbench."""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import sys
import time

from llm_interview_lab import __version__


_PROCESS_STARTED = time.perf_counter()


def _grader_worker(arguments: list[str]) -> int:
    import pytest

    return int(pytest.main(arguments))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="llm-lab-gui")
    parser.add_argument("--profile", default="default")
    parser.add_argument("--version", action="store_true")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="load the synthetic home window for one event-loop cycle and exit",
    )
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
    if args.screenshot or args.smoke_test:
        os.environ.setdefault("QT_QUICK_BACKEND", "software")
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6.QtCore import QTimer, QUrl
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlApplicationEngine
    except ImportError:
        print(
            '错误：未安装桌面依赖。请运行 `python -m pip install -e ".[desktop]"` 后重试。',
            file=sys.stderr,
        )
        return 2

    from llm_interview_lab.desktop.controller import AppController
    from llm_interview_lab.desktop.runtime import (
        configure_desktop_logging,
        desktop_log_root,
        detect_legacy_desktop_data,
        prepare_desktop_repository,
    )

    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Material")
    if getattr(sys, "frozen", False) or "__compiled__" in globals():
        os.environ.setdefault("LLM_LAB_PACKAGED", "1")
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
    app.setOrganizationDomain("comistrymo.github.io")
    app.setApplicationVersion(__version__)
    repository_started = time.perf_counter()
    try:
        repo_root = prepare_desktop_repository()
        configure_desktop_logging(repo_root)
        legacy_root = detect_legacy_desktop_data(repo_root)
        controller = AppController(
            repo_root,
            profile_id=args.profile,
            demo_page=(args.screenshot_page if args.screenshot else "home")
            if (args.screenshot or args.smoke_test)
            else None,
            legacy_data_root=legacy_root,
            log_root=desktop_log_root(repo_root),
        )
    except Exception as error:
        logging.getLogger("llm_interview_lab.desktop").error(
            "startup_failed error_type=%s", type(error).__name__
        )
        print(f"错误：桌面应用启动失败（{type(error).__name__}）。请查看本地日志。", file=sys.stderr)
        return 2
    repository_ready = time.perf_counter()
    engine = QQmlApplicationEngine()
    engine.warnings.connect(
        lambda warnings: [print(f"QML: {warning.toString()}", file=sys.stderr) for warning in warnings]
    )
    engine.rootContext().setContextProperty("backend", controller)
    qml_path = Path(__file__).parent / "qml/Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        print("错误：桌面界面无法加载。请查看本地日志。", file=sys.stderr)
        return 2
    qml_ready = time.perf_counter()
    app.aboutToQuit.connect(controller.shutdown)

    def startup_metrics() -> dict[str, int | str]:
        return {
            "process_to_application_ms": round((repository_started - _PROCESS_STARTED) * 1000),
            "catalog_workspace_ms": round((repository_ready - repository_started) * 1000),
            "qml_window_ms": round((qml_ready - repository_ready) * 1000),
            "first_window_ms": round((qml_ready - _PROCESS_STARTED) * 1000),
            "provider_probe": "lazy",
            "codex_probe": "lazy",
        }

    logging.getLogger("llm_interview_lab.desktop").info(
        "startup %s", json.dumps(startup_metrics(), ensure_ascii=True, sort_keys=True)
    )

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
                print(f"错误：截图保存失败（{type(error).__name__}）。", file=sys.stderr)
                app.exit(2)
                return
            window.hide()
            window.deleteLater()
            QTimer.singleShot(0, app.quit)

        QTimer.singleShot(900, capture)
    elif args.smoke_test:
        def finish_smoke() -> None:
            print(json.dumps({"status": "ok", **startup_metrics()}, sort_keys=True))
            window = engine.rootObjects()[0]
            window.hide()
            window.deleteLater()
            QTimer.singleShot(0, app.quit)

        QTimer.singleShot(150, finish_smoke)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
