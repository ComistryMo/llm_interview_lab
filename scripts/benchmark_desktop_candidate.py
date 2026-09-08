"""Same-host desktop measurements using only a newly created synthetic workspace.

Process-cold is not OS-cache-cold. Fixture provisioning and dialogue generation
are excluded from UI timings. No microphone, credential or remote model is used.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import faulthandler

ROOT = Path(__file__).resolve().parents[1]


def working_set_mb():
    if os.name != "nt":
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 if sys.platform != "darwin" else 1024 ** 2)
    # Outside all timed regions; ask Windows for this synthetic process only.
    result = subprocess.check_output(["powershell", "-NoProfile", "-Command",
        f"(Get-Process -Id {os.getpid()}).WorkingSet64"], text=True, timeout=10,
        creationflags=subprocess.CREATE_NO_WINDOW)
    return int(result.strip()) / 1024 ** 2


def child(root: Path, profile: str):
    faulthandler.enable()
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "Material"  # Same as desktop.main.
    started = time.perf_counter()
    from PySide6.QtCore import QCoreApplication, QObject, QPoint, QPointF, QSettings, Qt, QUrl
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuick import QQuickWindow
    from PySide6.QtTest import QTest
    import llm_interview_lab.desktop.controller as module
    app = QApplication(["synthetic-desktop-benchmark"])
    app.setFont(QFont("Microsoft YaHei UI" if os.name == "nt" else "sans-serif", 10))
    settings = QSettings(str(root / f"{profile}.ini"), QSettings.IniFormat)
    module.QSettings = lambda *args: settings
    module.AppController.refreshCodexAvailability = lambda self: None
    module.AppController._restore_ai_connection = lambda self: None
    controller = module.AppController(root, profile_id=profile)
    assert not controller.onboardingRequired, controller.lastActionResult
    controller.saveInterviewPreferences({"role_id": "post_training_engineer", "difficulty": "hard", "ai_mode": "codex"})
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(e.toString() for e in errors))
    engine.rootContext().setContextProperty("backend", controller)
    engine.load(QUrl.fromLocalFile(str(ROOT / "src/llm_interview_lab/desktop/qml/Main.qml")))
    window = engine.rootObjects()[0]
    assert isinstance(window, QQuickWindow)
    window.resize(1440, 900)
    window.show()
    QTest.qWait(30)

    def items(item):
        for item in item.childItems():
            yield item
            yield from items(item)

    def find(name):
        return next((i for i in items(window.contentItem()) if i.objectName() == name), window.findChild(QObject, name))

    def click(name):
        item = find(name)
        point = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
        QTest.mouseClick(window, Qt.LeftButton, pos=QPoint(round(point.x()), round(point.y())))
        QCoreApplication.processEvents()

    old_mode = controller.sidebarMode
    click("toggleSidebar")
    assert controller.sidebarMode != old_mode
    result = {"startup_interactive_ms": (time.perf_counter() - started) * 1000,
              "startup_working_set_mb": working_set_mb()}
    controller.navigate("learn")
    tick = time.perf_counter()
    click("knowledgeBrowserButton")
    assert controller.knowledgeLoaded
    QCoreApplication.processEvents()
    result["knowledge_first_open_ms"] = (time.perf_counter() - tick) * 1000
    queries = ("GRPO", "KL loss", "EGT-QB-028", "mask token", "ZeRO", "LoRA rank", "注意力", "AdamW")
    search_ms, hits = [], []
    for query in queries * 3:
        tick = time.perf_counter()
        assert controller.searchKnowledge(query)
        QCoreApplication.processEvents()
        QTest.qWait(10)  # Complete Qt's scheduled layout/deferred-deletion tick.
        search_ms.append((time.perf_counter() - tick) * 1000)
        hits.append([card["id"] for card in controller.knowledgeCards])
    result["search_ms"] = search_ms
    result["search_hits"] = hits
    controller.navigate("interview")
    QTest.qWait(100)
    preview = controller.dynamicInterviewContextPreview("post_training_engineer", "", "hard", "", False)
    controller.startDynamicPersonalizedInterview("post_training_engineer", "", "hard", "codex", "", False, preview["context_sha256"])
    assert controller.interview.get("question"), controller.lastActionResult
    controller.navigate("interview")
    answer = "合成性能验证：我实现了公开 GRPO 训练的奖励归一化，用独立样本检查 KL 和长度偏差。" * 10
    tick = time.perf_counter()
    controller.lockInterviewAnswer(answer)
    QCoreApplication.processEvents()
    result["submit_local_ms"] = (time.perf_counter() - tick) * 1000
    interview_id = controller.interview["interview_id"]
    for index in range(40):
        question = controller.service.current_interview(profile, interview_id)["question"]
        if index:
            controller.service.answer_interview(profile, interview_id, question["question_id"], answer)
        controller.service.advance_dynamic_interview(profile, interview_id, question["question_id"], {
            "next_stage": "experience", "follow_up": f"合成追问 {index + 1}：请说明实验对照、边界与验证。",
            "coding_problem_id": "", "next_skill_ids": [next(iter(controller.service.roles.roles["post_training_engineer"].skill_weights))],
            "coverage": {"experience": "合成公开实验", "angle": "验证", "topic": "GRPO", "evidence": "", "sufficient": False},
        }, context_sha256=preview["context_sha256"])
    tick = time.perf_counter()
    controller._load_interview(interview_id)
    QCoreApplication.processEvents()
    QTest.qWait(20)
    result["history_40_open_ms"] = (time.perf_counter() - tick) * 1000
    viewport = find("interviewQuestionScroll").property("contentItem")
    scroll_ms = []
    for fraction in (0, .25, .5, .75, 1) * 3:
        tick = time.perf_counter()
        viewport.setProperty("contentY", fraction * max(0, viewport.property("contentHeight") - viewport.height()))
        QCoreApplication.processEvents()
        scroll_ms.append((time.perf_counter() - tick) * 1000)
    result["history_scroll_ms"] = scroll_ms
    result["final_working_set_mb"] = working_set_mb()
    assert not warnings, "\n".join(warnings)
    window.close()
    controller.shutdown()
    print(json.dumps(result, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--child", type=Path)
    parser.add_argument("--profile")
    args = parser.parse_args()
    if args.child:
        child(args.child, args.profile)
        return
    if not args.output:
        parser.error("--output is required")
    work = ROOT / "workspace/maintainer/release-candidate-20260909"
    work.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="llm-lab-synthetic-benchmark-") as directory:
        root = Path(directory)
        for name in ("curriculum", "coach", "workspace/schema", "workspace/templates"):
            shutil.copytree(ROOT / name, root / name)
        for name in (".gitignore", "pyproject.toml"):
            shutil.copy2(ROOT / name, root / name)
        (root / "workspace/profiles").mkdir()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        from llm_interview_lab.workspace import init_profile
        for index in range(args.samples):
            init_profile(root, f"synthetic-benchmark-{index}", display_name="合成性能验收")
        results = []
        for index in range(args.samples):
            run = subprocess.run([sys.executable, __file__, "--child", str(root), "--profile", f"synthetic-benchmark-{index}"],
                text=True, encoding="utf-8", capture_output=True, timeout=240,
                env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONIOENCODING": "utf-8", "QT_QPA_PLATFORM": "windows" if os.name == "nt" else "offscreen", "QT_QUICK_BACKEND": "software"})
            if run.returncode:
                raise RuntimeError(f"benchmark child exit {run.returncode}\n{run.stderr[-5000:]}\n{run.stdout[-1000:]}")
            results.append(json.loads(run.stdout.strip().splitlines()[-1]))
            print(f"synthetic sample {index + 1}/{args.samples}: {results[-1]['startup_interactive_ms']:.0f} ms to interaction", flush=True)
    scalar = [key for key, value in results[0].items() if isinstance(value, (int, float))]
    report = {"synthetic": True, "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "tracked_diff_sha256": __import__("hashlib").sha256(subprocess.check_output(["git", "diff"], cwd=ROOT)).hexdigest(),
              "python": sys.version, "platform": sys.platform, "size": [1440, 900], "samples": results,
              "notes": "Fresh process, provisioned synthetic public assets; OS caches not flushed. UI event processing, not a GPU frame-time claim. No network/AI/credentials.",
              "median": {key: statistics.median(row[key] for row in results) for key in scalar}}
    for key in ("search_ms", "history_scroll_ms"):
        report["median"][key] = statistics.median(value for row in results for value in row[key])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["median"], ensure_ascii=False))


if __name__ == "__main__":
    main()
