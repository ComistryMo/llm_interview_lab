"""User-initiated updates from this project's public GitHub Releases.

Incremental reconstruction and explicit restart use a native install handoff.
This module never opens Profiles, credentials or model caches.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import tempfile
import threading
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from PySide6.QtCore import QObject, Property, QRunnable, QStandardPaths, QThreadPool, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from .. import __version__
from ..release_version import VERSION_PATTERN as _VERSION, version_key
from .update_payload import MANIFEST_NAMES, PayloadError, reconstruct, validate_manifest
from .update_install import installation_root, prepare_handoff, validate_staged_app, launch_handoff

REPOSITORY = "ComistryMo/llm_interview_lab"
RELEASES_URL = f"https://github.com/{REPOSITORY}/releases"
API_URL = f"https://api.github.com/repos/{REPOSITORY}/releases?per_page=10"
ASSET_NAMES = {
    "windows-x64": "LLMInterviewLab-Windows-x64-portable.zip",
    "macos-arm64": "LLMInterviewLab-macOS-arm64.dmg",
}


class UpdateError(RuntimeError):
    pass


class UpdateCancelled(UpdateError):
    pass


def platform_key() -> str:
    machine = platform.machine().lower()
    if os.name == "nt" and machine in {"amd64", "x86_64"}:
        return "windows-x64"
    if platform.system() == "Darwin" and machine in {"arm64", "aarch64"}:
        return "macos-arm64"
    return "unsupported"


def _asset_url(url: str, *, redirect: bool = False) -> bool:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError:
        return False
    if parsed.scheme != "https" or parsed.username or parsed.password or port not in {None, 443}:
        return False
    if parsed.hostname == "github.com":
        return parsed.path.startswith(f"/{REPOSITORY}/releases/download/")
    return redirect and parsed.hostname in {"release-assets.githubusercontent.com", "objects.githubusercontent.com"}


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def open_public(url: str):
    """Only the fixed API, repository release assets and their HTTPS CDN hops."""
    if url != API_URL and not _asset_url(url):
        raise UpdateError("更新来源不是本项目的官方发布地址。")
    opener = build_opener(_NoRedirect())
    for hop in range(6):
        try:
            return opener.open(Request(url, headers={"User-Agent": "LLMInterviewLab-Update",
                "Accept": "application/vnd.github+json" if url == API_URL else "application/octet-stream"}), timeout=20)
        except HTTPError as error:
            if error.code in {301, 302, 303, 307, 308}:
                target = error.headers.get("Location", "")
                error.close()
                if not _asset_url(target, redirect=True):
                    raise UpdateError("下载地址跳转到非官方或不安全的来源，已停止。") from None
                url = target
                continue
            code = error.code
            error.close()
            if code in {403, 429}:
                raise UpdateError("GitHub 暂时限制查询或下载，请稍后重试，也可以打开官方发布页面。") from None
            if code == 404:
                raise UpdateError("此发布或下载文件暂时不存在，请重新检查更新。") from None
            raise UpdateError(f"GitHub 请求失败（HTTP {code}），请稍后重试。") from None
        except (URLError, TimeoutError, OSError):
            raise UpdateError("无法连接 GitHub 或请求超时；请检查网络后重试，当前应用不受影响。") from None
    raise UpdateError("下载重定向次数异常，请从官方发布页面检查。")


def _read_small(url: str, limit: int, opener=open_public) -> bytes:
    with opener(url) as response:
        try:
            data = response.read(limit + 1)
        except (TimeoutError, OSError):
            raise UpdateError("读取发布信息时网络中断或超时，请稍后重试。") from None
    if len(data) > limit:
        raise UpdateError("发布信息超出预期大小，请从官方发布页面查看。")
    return data


def select_release(releases: list[dict], current: str, channel: str, target: str, *, incremental=False) -> dict:
    current_key = version_key(current)
    available = []
    current_published = False
    for release in releases:
        if release.get("draft"):
            continue
        try:
            key = version_key(str(release.get("tag_name", "")))
        except ValueError:
            continue
        current_published |= key == current_key
        if channel == "stable" and (key[3] != 3 or release.get("prerelease")):
            continue
        available.append((key, release))
    newer = [(key, release) for key, release in available if key > current_key]
    if not newer:
        return {"status": "up_to_date" if current_published else "local_unpublished",
                "message": "此渠道没有更新版本。" if current_published else "当前版本未出现在最近的公开发布列表中，可能是本地候选版；未发现更高版本。"}
    _, release = max(newer, key=lambda item: item[0])
    tag = release["tag_name"]
    asset_name = (MANIFEST_NAMES if incremental else ASSET_NAMES).get(target)
    asset = next((item for item in release.get("assets", []) if item.get("name") == asset_name), None)
    checksum = next((item for item in release.get("assets", []) if item.get("name") == "SHA256SUMS.txt"), None)
    state = {"release_version": tag, "notes": str(release.get("body") or "发布者未填写更新说明。")[:16000],
             "release_url": f"{RELEASES_URL}/tag/{quote(tag, safe='')}",
             "status": "available" if asset else "no_asset",
             "message": "发现新版，可下载并校验。" if asset else "已发现新版，但尚无匹配当前平台的安装包。"}
    if incremental and not asset:
        state.update(status="no_incremental", message="新版缺少匹配平台的增量更新资源，发布不完整。请反馈维护者；不会改为下载全量安装包。")
    if asset:
        expected_url = f"{RELEASES_URL}/download/{quote(tag, safe='')}/{asset_name}"
        if asset.get("browser_download_url") != expected_url or type(asset.get("size")) is not int or asset["size"] <= 0:
            raise UpdateError("发布包信息不完整或来源不匹配，已停止下载准备。")
        digest = str(asset.get("digest") or "")
        digest = digest[7:] if re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest) else ""
        checksum_url = f"{RELEASES_URL}/download/{quote(tag, safe='')}/SHA256SUMS.txt"
        if checksum and checksum.get("browser_download_url") != checksum_url:
            raise UpdateError("发布校验清单的来源不匹配。")
        state.update(asset_name=asset_name, asset_url=expected_url, size=asset["size"], sha256=digest.lower(),
                     checksum_url=checksum_url if checksum else "")
        if not digest and not checksum:
            state.update(status="unverified_asset", message="发布包缺少 SHA-256，暂不提供应用内下载；请查看发布说明。")
    if incremental:
        state["incremental"] = True
        if state["status"] == "available":
            state["message"] = "发现新版。将复用本机已有文件，仅拉取变化的数据块和小文件组，无需重新安装。"
    return state


def check_releases(current: str, channel: str, target: str, *, opener=open_public, incremental=False) -> dict:
    try:
        releases = json.loads(_read_small(API_URL, 16 * 1024 * 1024, opener))
    except (ValueError, UnicodeDecodeError):
        raise UpdateError("GitHub 返回的发布信息无法解析，请稍后重试。") from None
    if not isinstance(releases, list) or any(not isinstance(item, dict) for item in releases):
        raise UpdateError("GitHub 未返回有效的发布列表，请稍后重试。")
    return select_release(releases, current, channel, target, incremental=incremental)


def prepare_incremental(release: dict, installed: Path, target: str, cancel, progress, *, opener=open_public) -> dict:
    raw = _read_small(release["asset_url"], 8 * 1024 * 1024, opener)
    expected = release.get("sha256")
    if not expected and release.get("checksum_url"):
        lines = _read_small(release["checksum_url"], 256 * 1024, opener).decode("utf-8-sig").splitlines()
        hashes = [line.split()[0] for line in lines if len(line.split()) == 2 and line.split()[1] == release["asset_name"]]
        if len(hashes) == 1:
            expected = hashes[0]
    if len(raw) != release["size"] or hashlib.sha256(raw).hexdigest() != expected:
        raise UpdateError("更新清单校验失败，未修改当前应用。")
    try:
        manifest = json.loads(raw)
        validate_manifest(manifest, target, release["release_version"])
    except (ValueError, KeyError, TypeError) as error:
        raise UpdateError("更新清单无法解析，未修改当前应用。") from error
    handoff = prepare_handoff(installed, target, manifest["version"])
    base_url = release["asset_url"].rsplit("/", 1)[0] + "/"
    def fetch(name, spec):
        if cancel.is_set():
            raise UpdateCancelled("已取消更新，当前应用未改变。")
        return _read_small(base_url + name, spec["size"], opener)
    try:
        result = reconstruct(manifest, installed, Path(handoff["staging"]), fetch, cancel, progress)
        if cancel.is_set():
            raise UpdateCancelled("已取消更新，当前应用未改变。")
        validate_staged_app(handoff)
    except Exception:
        # Only remove the directory just allocated by prepare_handoff, never
        # the installed app or a previously completed update's rollback copy.
        temporary = Path(handoff["handoff"]).parent.resolve()
        if temporary.parent == installed.resolve().parent and temporary.name.startswith(".llm-update-"):
            shutil.rmtree(temporary)
        if cancel.is_set():
            raise UpdateCancelled("已取消更新，当前应用未改变。") from None
        raise
    return {**result, "handoff": handoff["handoff"], "file_path": handoff["staging"]}


def download_release(release: dict, directory: Path, cancel: threading.Event, progress, *, opener=open_public) -> dict:
    """Preserve existing files; remove only this operation's incomplete temp file."""
    name = release["asset_name"]
    tag = release["release_version"]
    if name not in ASSET_NAMES.values() or not _VERSION.fullmatch(tag):
        raise UpdateError("下载文件名或版本号无效。")
    digest = release.get("sha256", "")
    if not digest:
        checksum = _read_small(release["checksum_url"], 64 * 1024, opener).decode("utf-8-sig")
        matches = [match[1].lower() for line in checksum.splitlines()
                   if (match := re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?" + re.escape(name), line))]
        if len(matches) != 1:
            raise UpdateError("校验清单没有唯一匹配此文件的 SHA-256，已停止下载。")
        digest = matches[0]
    if cancel.is_set():
        raise UpdateCancelled("已取消下载。")
    destination = directory / tag
    destination.mkdir(parents=True, exist_ok=True)
    final_path = destination / name
    if final_path.exists():
        with final_path.open("rb") as existing:
            actual = hashlib.file_digest(existing, "sha256").hexdigest() if hasattr(hashlib, "file_digest") else _file_sha(existing)
        if actual != digest:
            raise UpdateError("下载目录已有同名但内容不同的文件；请先移走该文件再重试，不会自动覆盖。")
        return {"file_path": str(final_path), "sha256": actual}
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".download-", suffix=".part", dir=destination, delete=False) as output:
            temporary = Path(output.name)
            sha = hashlib.sha256()
            received = 0
            with opener(release["asset_url"]) as response:
                while True:
                    if cancel.is_set():
                        raise UpdateCancelled("已取消下载，未完成的临时文件已移除。")
                    try:
                        chunk = response.read(256 * 1024)
                    except (TimeoutError, OSError):
                        raise UpdateError("下载时网络中断或超时，请重试；当前应用不受影响。") from None
                    if not chunk:
                        break
                    output.write(chunk)
                    sha.update(chunk)
                    received += len(chunk)
                    if received > release["size"]:
                        raise UpdateError("下载大小与发布信息不一致，请重新检查更新。")
                    progress(min(99, received * 100 // release["size"]))
        if received != release["size"] or sha.hexdigest() != digest:
            raise UpdateError("下载不完整或 SHA-256 不匹配，未保留该文件；请重试。")
        if cancel.is_set():
            raise UpdateCancelled("已取消下载。")
        # Both files are on the same volume. A hard link publishes the verified
        # file atomically and refuses an existing name on Windows AND macOS.
        try:
            os.link(temporary, final_path)
        except FileExistsError:
            raise UpdateError("此文件已存在，请打开下载位置检查；不会覆盖已有文件。")
        progress(100)
        return {"file_path": str(final_path), "sha256": digest}
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _file_sha(file) -> str:
    digest = hashlib.sha256()
    for chunk in iter(lambda: file.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


class _WorkerSignals(QObject):
    completed = Signal(object)
    failed = Signal(str, bool)
    progress = Signal(int)


class _UpdateWorker(QRunnable):
    def __init__(self, operation):
        super().__init__()
        self.signals = _WorkerSignals()
        self.operation = operation

    def run(self):
        try:
            self.signals.completed.emit(self.operation(self.signals.progress.emit))
        except UpdateCancelled as error:
            self.signals.failed.emit(str(error), True)
        except (UpdateError, PayloadError) as error:
            self.signals.failed.emit(str(error), False)
        except OSError:
            self.signals.failed.emit("无法保存下载文件；请检查磁盘空间和下载目录权限后重试。", False)
        except Exception:
            self.signals.failed.emit("更新操作失败，请稍后重试或打开官方发布页面；当前应用和数据未改变。", False)


class UpdateManager(QObject):
    changed = Signal()
    restartRequested = Signal()

    def __init__(self, settings, *, directory: Path | None = None, current=__version__, target=None, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._directory = directory or Path(QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)) / "LLMInterviewLab"
        self._current = current
        self._target = target or platform_key()
        self._installed = installation_root(target=self._target)
        channel = str(settings.value("updates/channel", "preview" if version_key(current)[3] < 3 else "stable"))
        self._state = {"current_version": current, "channel": channel if channel in {"stable", "preview"} else "preview",
                       "status": "idle", "message": "仅在你点击时检查更新，不会自动下载或安装。", "progress": 0}
        self._worker = None
        self._cancel = threading.Event()
        self._closed = False
        receipt = str(settings.value("updates/lastHandoff", ""))
        if receipt:
            try:
                status = (Path(receipt).parent / "status").read_text("ascii")
                messages = {"installed": "上次应用内更新已完成。旧版保留在本次更新目录中。",
                            "rolled_back": "新版启动失败，已恢复旧版。可重试更新或反馈维护者，用户数据未移动。",
                            "install_failed": "上次安装未完成，旧版未被替换。请检查目录权限或占用后重试。",
                            "unconfirmed": "上次更新未收到启动确认，已保留旧版。请复制本页状态反馈维护者。"}
                if status in messages:
                    self._state["message"] = messages[status]
            except OSError:
                pass

    @Property("QVariantMap", notify=changed)
    def state(self):
        return dict(self._state)

    def _change(self, **fields):
        self._state.update(fields)
        self.changed.emit()

    @Slot(str)
    def setChannel(self, channel):
        if self._worker or channel not in {"stable", "preview"}:
            return
        self._settings.setValue("updates/channel", channel)
        self._settings.sync()
        self._state = {"current_version": self._current, "channel": channel, "status": "idle", "message": "渠道已更改，请重新检查更新。", "progress": 0}
        self.changed.emit()

    def _start(self, operation, completed):
        if self._closed or self._worker:
            return
        self._cancel = threading.Event()
        worker = _UpdateWorker(operation)
        self._worker = worker

        def done(value):
            self._worker = None
            if not self._closed:
                completed(value)

        def failed(message, cancelled):
            self._worker = None
            if not self._closed:
                self._change(status="cancelled" if cancelled else "error", message=message)

        worker.signals.completed.connect(done)
        worker.signals.failed.connect(failed)
        worker.signals.progress.connect(lambda amount: self._change(progress=amount) if not self._closed else None)
        QThreadPool.globalInstance().start(worker)

    @Slot()
    def check(self):
        if self._worker or self._closed:
            return
        # A new query must not leave the previous release's download action live.
        self._state = {"current_version": self._current, "channel": self._state["channel"],
                       "status": "checking", "message": "正在检查官方发布…", "progress": 0}
        self.changed.emit()
        channel = self._state["channel"]
        self._start(lambda progress: check_releases(self._current, channel, self._target, incremental=True), lambda result: self._change(**result))

    @Slot()
    def download(self):
        if self._worker or self._closed or not self._state.get("asset_url") or self._state["status"] == "unverified_asset":
            return
        if not self._installed:
            self._change(status="source_install", message="当前为源码启动或无法识别安装目录。应用内安装适用于正式桌面包；源码工作区不会被更新覆盖。")
            return
        release = dict(self._state)
        self._change(status="downloading", progress=0, message="正在校验本机文件、拉取变化内容并准备新版；不会覆盖正在运行的应用。")
        self._start(lambda progress: prepare_incremental(release, self._installed, self._target, self._cancel, progress),
                    lambda result: self._change(**result, status="prepared", progress=100,
                        message=f"更新已准备好：下载 {result['downloaded_bytes'] / 1048576:.1f} MB，复用 {result['reused_bytes'] / 1048576:.1f} MB。点击安装并重启后生效。"))

    @Slot()
    def install(self):
        if self._worker or self._closed or self._state["status"] != "prepared":
            return
        self._change(status="install_pending", message="正在保存当前内容并退出应用以安装更新…")
        self.restartRequested.emit()

    @Slot(result=bool)
    def launchInstaller(self):
        if self._state["status"] != "install_pending":
            return True
        try:
            path = Path(self._state["handoff"])
            launch_handoff(path)
            self._settings.setValue("updates/lastHandoff", str(path))
            self._settings.sync()
            return True
        except (OSError, ValueError, KeyError, PayloadError):
            self._change(status="prepared", message="无法启动更新安装程序，当前应用未退出。请检查目录权限后重试。")
            return False

    @Slot()
    def cancelInstallClose(self):
        if self._state["status"] == "install_pending":
            self._change(status="prepared", message="尚有内容未能保存或操作正在进行，未退出应用。请处理后再次安装。")

    @Slot()
    def cancel(self):
        if self._worker and self._state["status"] == "downloading":
            self._cancel.set()
            self._change(status="cancelling", message="正在取消下载…")

    @Slot()
    def openReleasePage(self):
        QDesktopServices.openUrl(QUrl(RELEASES_URL))

    @Slot()
    def openDownloadLocation(self):
        path = self._state.get("file_path")
        if path and self._state["status"] == "downloaded":
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path).parent)))

    def close(self):
        self._closed = True
        self._cancel.set()
