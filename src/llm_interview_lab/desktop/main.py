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


def _window_size(value: str) -> tuple[int, int]:
    """Parse a screenshot/smoke window size without accepting odd geometry."""

    try:
        width_text, height_text = value.lower().split("x", 1)
        width, height = int(width_text), int(height_text)
    except (ValueError, AttributeError) as error:
        raise argparse.ArgumentTypeError("window size must be WIDTHxHEIGHT") from error
    if width < 320 or height < 240 or width > 10000 or height > 10000:
        raise argparse.ArgumentTypeError("window size is outside the supported range")
    return width, height


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
        choices=(
            "onboarding",
            "home",
            "career",
            "learn",
            "exercise",
            "interview",
            "coach",
            "progress",
            "connections",
            "settings",
        ),
        default="home",
    )
    parser.add_argument(
        "--onboarding-step",
        type=int,
        choices=(0, 1, 2, 3),
        default=0,
        help="step to show when --screenshot-page onboarding is selected",
    )
    parser.add_argument(
        "--onboarding-role",
        help="synthetic role id to select in an onboarding screenshot",
    )
    parser.add_argument(
        "--window-size",
        type=_window_size,
        metavar="WIDTHxHEIGHT",
        help="resize the synthetic window before a screenshot or smoke test",
    )
    return parser


def _startup_error_code(stage: str, error: BaseException) -> str:
    detail = str(error).lower()
    if "desktop bundle is missing" in detail or stage == "runtime_assets":
        return "RUNTIME_ASSETS_MISSING"
    if stage in {"repository", "logging"}:
        return "DATA_DIRECTORY_UNAVAILABLE"
    if stage == "qml":
        return "QML_LOAD_FAILED"
    if stage == "qt":
        return "QT_INITIALIZATION_FAILED"
    return "CONTROLLER_INITIALIZATION_FAILED"


def _show_loading_screen(app, *, enabled: bool):
    """Show immediate feedback while repository/QML resources are prepared.

    The screen is intentionally tiny and disposable; the real UI remains the
    single source of interaction.  Offscreen smoke and screenshot modes skip it.
    """

    if not enabled:
        return None
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout

        dialog = QDialog()
        dialog.setWindowTitle("LLM Interview Lab")
        dialog.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint)
        dialog.setModal(False)
        label = QLabel("正在准备本地工作区……\n课程和学习档案即将加载")
        label.setMinimumWidth(330)
        label.setMargin(24)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout = QVBoxLayout(dialog)
        layout.addWidget(label)
        dialog.setLayout(layout)
        dialog.show()
        app.processEvents()
        return dialog
    except Exception:
        # A loading hint must never prevent the actual application from
        # starting; bootstrap errors are still handled by the visible error box.
        return None


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

    from llm_interview_lab.desktop.runtime import (
        configure_desktop_logging,
        desktop_log_root,
        detect_legacy_desktop_data,
        prepare_desktop_repository,
        record_bootstrap_event,
        runtime_assets_available,
        show_startup_error,
    )

    if getattr(sys, "frozen", False) or "__compiled__" in globals():
        os.environ.setdefault("LLM_LAB_PACKAGED", "1")
    record_bootstrap_event(
        "process_started",
    )
    packaged = os.environ.get("LLM_LAB_PACKAGED", "").lower() in {"1", "true", "yes"}
    try:
        assets_found = runtime_assets_available() if packaged else True
    except Exception as error:
        path = record_bootstrap_event(
            "runtime_assets", error=error, runtime_assets_found=False
        )
        show_startup_error(
            "RUNTIME_ASSETS_MISSING",
            "应用运行资源检查失败，请重新解压完整 Portable ZIP 或重新下载。",
            path,
        )
        return 2
    if packaged and not assets_found:
        error = RuntimeError("desktop bundle is missing required runtime assets")
        path = record_bootstrap_event(
            "runtime_assets",
            error=error,
            runtime_assets_found=False,
        )
        show_startup_error(
            "RUNTIME_ASSETS_MISSING",
            "应用运行资源不完整，请重新解压完整 Portable ZIP 或重新下载。",
            path,
        )
        return 2
    record_bootstrap_event("runtime_assets", runtime_assets_found=assets_found)
    try:
        from PySide6.QtCore import QTimer, QUrl, QObject
        from PySide6.QtWidgets import QApplication
        from PySide6.QtQml import QQmlApplicationEngine
        from PySide6.QtQuick import QQuickWindow
        import shiboken6
    except ImportError as error:
        path = record_bootstrap_event("qt", error=error)
        show_startup_error(
            "QT_INITIALIZATION_FAILED",
            '未安装或无法加载桌面依赖。源码用户请运行 `python -m pip install -e ".[desktop]"`。',
            path,
        )
        return 2

    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Material")
    try:
        app = QApplication([sys.argv[0]])
    except Exception as error:
        path = record_bootstrap_event("qt", error=error)
        show_startup_error(
            _startup_error_code("qt", error),
            "桌面窗口环境初始化失败。请查看日志后重新启动。",
            path,
        )
        return 2
    app.setApplicationName("LLM Interview Lab")
    app.setOrganizationName("ComistryMo")
    app.setOrganizationDomain("comistrymo.github.io")
    app.setApplicationVersion(__version__)
    loading = _show_loading_screen(
        app,
        enabled=not (args.screenshot or args.smoke_test)
        and os.environ.get("QT_QPA_PLATFORM", "").lower() not in {"offscreen", "minimal"},
    )
    repository_started = time.perf_counter()
    try:
        repo_root = prepare_desktop_repository()
    except Exception as error:
        if loading is not None:
            loading.close()
        path = record_bootstrap_event("repository", error=error)
        code = _startup_error_code("repository", error)
        reason = (
            "应用运行资源不完整，请重新解压完整 Portable ZIP 或重新下载。"
            if code == "RUNTIME_ASSETS_MISSING"
            else "无法准备本地数据目录，请检查当前用户的 AppData 写入权限。"
        )
        show_startup_error(code, reason, path)
        return 2
    try:
        configure_desktop_logging(repo_root)
    except Exception as error:
        if loading is not None:
            loading.close()
        path = record_bootstrap_event("logging", error=error)
        show_startup_error(
            _startup_error_code("logging", error),
            "无法创建本地日志或数据目录，请检查 AppData 写入权限。",
            path,
        )
        return 2
    try:
        from llm_interview_lab.desktop.controller import AppController

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
        if loading is not None:
            loading.close()
        logging.getLogger("llm_interview_lab.desktop").error(
            "startup_failed error_type=%s", type(error).__name__
        )
        path = record_bootstrap_event("controller", error=error)
        show_startup_error(
            _startup_error_code("controller", error),
            "桌面应用初始化失败。请查看日志中的错误编号并重试。",
            path,
        )
        return 2
    repository_ready = time.perf_counter()
    engine = QQmlApplicationEngine()
    engine.warnings.connect(
        lambda warnings: [print(f"QML: {warning.toString()}", file=sys.stderr) for warning in warnings]
    )
    engine.rootContext().setContextProperty("backend", controller)
    qml_path = Path(__file__).parent / "qml/Main.qml"
    try:
        engine.load(QUrl.fromLocalFile(str(qml_path)))
    except Exception as error:
        if loading is not None:
            loading.close()
        path = record_bootstrap_event("qml", error=error)
        show_startup_error(
            _startup_error_code("qml", error),
            "桌面界面加载失败，请重新下载完整应用包。",
            path,
        )
        controller.shutdown()
        return 2
    if not engine.rootObjects():
        if loading is not None:
            loading.close()
        error = RuntimeError("QML root object was not created")
        path = record_bootstrap_event("qml", error=error)
        show_startup_error(
            _startup_error_code("qml", error),
            "桌面界面加载失败，请重新下载完整应用包。",
            path,
        )
        controller.shutdown()
        return 2
    window = engine.rootObjects()[0]
    if args.window_size is not None:
        window.resize(*args.window_size)
    if args.screenshot and args.screenshot_page == "onboarding":
        # QML's onboarding object is a child item; select its step only for
        # synthetic screenshots, without changing normal startup behavior.
        onboarding = window.findChild(QObject, "onboardingPage")
        if onboarding is not None:
            onboarding.setProperty("step", args.onboarding_step)
            if args.onboarding_role:
                onboarding.setProperty("selectedRole", args.onboarding_role)
    qml_ready = time.perf_counter()
    if loading is not None:
        loading.close()
        loading.deleteLater()
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

    metrics = startup_metrics()
    logging.getLogger("llm_interview_lab.desktop").info(
        "startup %s", json.dumps(metrics, ensure_ascii=True, sort_keys=True)
    )
    record_bootstrap_event(
        "first_window",
        runtime_assets_found=assets_found,
        first_window_ms=int(metrics["first_window_ms"]),
    )

    if args.screenshot:
        destination = Path(args.screenshot).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)

        def capture() -> None:
            try:
                window = engine.rootObjects()[0]
                # Capture the Qt Quick scene itself. Screen.grabWindow() is
                # unreliable for offscreen standalone builds because there is
                # no native desktop surface for the window handle.
                quick_window = shiboken6.wrapInstance(
                    shiboken6.getCppPointer(window)[0], QQuickWindow
                )
                image = quick_window.grabWindow()
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
