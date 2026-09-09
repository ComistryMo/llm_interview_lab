"""Native handoff after normal UI close; all targets are prepared sibling paths."""
from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import plistlib
import subprocess
import sys
import tempfile

from .update_payload import ENTRYPOINTS, PayloadError
from ..release_version import version_key


def installation_root(executable: Path | None = None, target: str | None = None) -> Path | None:
    exe = (executable or Path(sys.executable)).resolve()
    target = target or ("windows-x64" if os.name == "nt" else "macos-arm64")
    if target == "windows-x64":
        root = exe.parent
        return root if exe.name == ENTRYPOINTS[target] and (root / "runtime_assets/BUILD-METADATA.json").is_file() else None
    if target == "macos-arm64" and exe.parent.name == "MacOS" and exe.parent.parent.name == "Contents":
        root = exe.parent.parent.parent
        if root.suffix == ".app" and (root / "Contents/Info.plist").is_file():
            return root
    return None


def prepare_handoff(installed: Path, target: str, version: str) -> dict:
    installed = installed.resolve()
    if installed == Path(installed.anchor) or not installed.is_dir():
        raise PayloadError("没有找到可更新的应用目录。")
    if target == "macos-arm64" and str(installed).startswith("/Volumes/"):
        raise PayloadError("当前应用仍在只读安装磁盘中。请先将应用拖入应用程序目录，再使用应用内更新。")
    try:
        directory = Path(tempfile.mkdtemp(prefix=".llm-update-", dir=installed.parent))
    except OSError as error:
        raise PayloadError("应用所在目录不可写或磁盘空间不足，无法准备更新；当前版本未改变。") from error
    handoff = {"protocol": 1, "installed": str(installed), "staging": str(directory / installed.name),
               "previous": str(directory / "previous"), "target": target, "version": version,
               "entrypoint": ENTRYPOINTS[target], "pid": os.getpid()}
    path = directory / "handoff.json"
    path.write_text(json.dumps(handoff, ensure_ascii=False), encoding="utf-8")
    return {**handoff, "handoff": str(path)}


def validate_staged_app(handoff: dict) -> None:
    staged = Path(handoff["staging"])
    if handoff["target"] == "macos-arm64":
        info = plistlib.loads((staged / "Contents/Info.plist").read_bytes())
        if (info.get("CFBundleIdentifier") != "io.github.comistrymo.llminterviewlab"
                or info.get("CFBundleShortVersionString") != handoff["version"].lstrip("v").split("-")[0]):
            raise PayloadError("新版应用标识或版本不匹配。")
        minimum = tuple(map(int, info.get("LSMinimumSystemVersion", "14.0").split(".")))
        host = tuple(map(int, platform.mac_ver()[0].split(".")))
        if host < minimum:
            raise PayloadError("当前 macOS 版本不支持此更新。请先升级系统；不会覆盖旧应用。")
        result = subprocess.run(["/usr/bin/codesign", "--verify", "--deep", "--strict", str(staged)], capture_output=True, timeout=60)
        if result.returncode:
            raise PayloadError("新版 macOS 应用签名完整性检查失败，未替换当前应用。")
    result = subprocess.run([str(staged / handoff["entrypoint"]), "--version"],
                            capture_output=True, text=True, timeout=30,
                            **({"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}))
    reported = result.stdout.strip().removeprefix("llm-lab-gui ")
    if result.returncode or not result.stdout.startswith("llm-lab-gui ") or version_key(reported) != version_key(handoff["version"]):
        raise PayloadError("新版主程序无法启动或版本不符，当前应用保持不变。")


def launch_handoff(path: Path) -> None:
    path = path.resolve()
    value = json.loads(path.read_text("utf-8"))
    installed = Path(value["installed"])
    if (path.name != "handoff.json" or not path.parent.name.startswith(".llm-update-")
            or path.parent.parent != installed.parent or not installed.is_absolute()
            or Path(value["staging"]) != path.parent / installed.name
            or Path(value["previous"]) != path.parent / "previous"
            or value["entrypoint"] != ENTRYPOINTS[value["target"]]):
        raise PayloadError("更新安装路径不匹配，已停止。")
    source = Path(__file__).parent / "resources" / ("apply_update.ps1" if os.name == "nt" else "apply_update.sh")
    helper = path.parent / source.name
    helper.write_bytes(source.read_bytes())
    arguments = [str(installed), value["staging"], value["previous"], str(os.getpid()), str(path), value["entrypoint"]]
    if os.name == "nt":
        # -WindowStyle Hidden applies only to the handoff helper, not the GUI.
        subprocess.Popen(["powershell.exe", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden",
                          "-ExecutionPolicy", "Bypass", "-File", str(helper), *arguments],
                         creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                         cwd=str(path.parent), close_fds=True)
    else:
        subprocess.Popen(["/bin/sh", str(helper), *arguments], cwd=str(path.parent),
                         start_new_session=True, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)


def acknowledge_startup() -> None:
    raw = os.environ.pop("LLM_LAB_UPDATE_HANDOFF", "")
    if not raw:
        return
    path = Path(raw).resolve()
    try:
        value = json.loads(path.read_text("utf-8"))
        if (path.name != "handoff.json" or not path.parent.name.startswith(".llm-update-")
                or installation_root() != Path(value["installed"])
                or path.parent.parent != Path(value["installed"]).parent):
            return
        (path.parent / "ready").write_text("ready", encoding="ascii")
    except (OSError, ValueError, KeyError):
        return  # The external helper retains the previous app if no ACK arrives.
