"""Release/asset protocol and real Qt background interaction, no network/keys."""
import hashlib
import io
import json
import threading
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QSettings
from llm_interview_lab.desktop import updates
from tests.infrastructure.test_interview_input_runtime import qapp, _wait_for_asr


def release(tag="v0.4.0-alpha.4", *, payload=b"synthetic portable archive", platform="windows-x64", digest=True):
    name = updates.ASSET_NAMES[platform]
    asset = {"name": name, "size": len(payload), "browser_download_url": f"{updates.RELEASES_URL}/download/{tag}/{name}"}
    if digest:
        asset["digest"] = "sha256:" + hashlib.sha256(payload).hexdigest()
    return {"tag_name": tag, "body": "合成更新说明：仅用于测试。", "prerelease": "-" in tag, "assets": [asset]}


def selected(**kwargs):
    return updates.select_release([release(**kwargs)], "0.4.0a3", "preview", "windows-x64")


def test_release_order_channels_and_distinct_empty_states():
    order = ["0.4.0a3", "v0.4.0-alpha.4", "0.4.0b1", "v0.4.0-rc.1", "0.4.0", "0.4.1a1"]
    assert list(map(updates.version_key, order)) == sorted(map(updates.version_key, order))
    rows = [release("v0.4.0-alpha.4"), release("v0.3.0"), release("v0.4.0-rc.1")]
    assert updates.select_release(rows, "0.4.0a3", "preview", "windows-x64")["release_version"] == "v0.4.0-rc.1"
    assert updates.select_release(rows, "0.4.0a3", "stable", "windows-x64")["status"] == "local_unpublished"
    assert updates.select_release(rows, "0.4.0rc1", "preview", "windows-x64")["status"] == "up_to_date"
    assert updates.select_release(rows, "0.4.0a3", "preview", "macos-arm64")["status"] == "no_asset"
    assert selected(digest=False)["status"] == "unverified_asset"
    rows += [{**release("v9.0.0"), "draft": True}, {"tag_name": "not-a-version"}]
    assert updates.select_release(rows, "0.4.0rc1", "preview", "windows-x64")["status"] == "up_to_date"


def test_public_sources_and_json_contract():
    visited = []
    def opener(url):
        visited.append(url)
        return io.BytesIO(json.dumps([release()]).encode())
    assert updates.check_releases("0.4.0a3", "preview", "windows-x64", opener=opener)["status"] == "available"
    assert visited == [updates.API_URL]
    for body in (b"broken", b"{}", b"[1]"):
        with pytest.raises(updates.UpdateError):
            updates.check_releases("0.4.0a3", "preview", "windows-x64", opener=lambda url: io.BytesIO(body))
    item = release()
    item["assets"][0]["browser_download_url"] = "https://example.com/file.zip"
    with pytest.raises(updates.UpdateError, match="来源"):
        updates.select_release([item], "0.4.0a3", "preview", "windows-x64")
    for url in ("http://github.com/file", "https://github.com/other/repo/releases/download/file",
                "https://user:pass@github.com/ComistryMo/llm_interview_lab/releases/download/file",
                "https://example.com/", "https://github.com:444/ComistryMo/llm_interview_lab/releases/download/file"):
        assert not updates._asset_url(url, redirect=True)
    assert updates._asset_url("https://release-assets.githubusercontent.com/github-production-release-asset/x?signature=public", redirect=True)


def test_redirect_and_rate_limit(monkeypatch):
    calls = []
    class Opener:
        def open(self, request, timeout):
            calls.append(request.full_url)
            if len(calls) == 1:
                raise updates.HTTPError(request.full_url, 302, "redirect", {"Location": "http://example.com/file"}, io.BytesIO())
            pytest.fail("An unsafe redirect was followed")
    monkeypatch.setattr(updates, "build_opener", lambda *args: Opener())
    with pytest.raises(updates.UpdateError, match="不安全"):
        updates.open_public(selected()["asset_url"])
    assert len(calls) == 1
    class Limited:
        def open(self, request, timeout):
            assert not request.has_header("Authorization")
            raise updates.HTTPError(request.full_url, 403, "limit", {}, io.BytesIO())
    monkeypatch.setattr(updates, "build_opener", lambda *args: Limited())
    with pytest.raises(updates.UpdateError, match="限制"):
        updates.open_public(updates.API_URL)


def test_download_hash_manifest_reuse_and_collision(tmp_path):
    data = b"synthetic portable archive"
    item = release(digest=False)
    checksum_url = f"{updates.RELEASES_URL}/download/{item['tag_name']}/SHA256SUMS.txt"
    item["assets"].append({"name": "SHA256SUMS.txt", "browser_download_url": checksum_url})
    state = updates.select_release([item], "0.4.0a3", "preview", "windows-x64")
    checksum = f"{hashlib.sha256(data).hexdigest()}  {state['asset_name']}\n".encode()
    urls, progress = [], []
    def opener(url):
        urls.append(url)
        return io.BytesIO(checksum if url == checksum_url else data)
    result = updates.download_release(state, tmp_path, threading.Event(), progress.append, opener=opener)
    destination = Path(result["file_path"])
    assert destination.read_bytes() == data
    assert progress[-1] == 100 and result["sha256"] == hashlib.sha256(data).hexdigest()
    assert updates.download_release(state, tmp_path, threading.Event(), progress.append, opener=opener) == result
    assert urls.count(state["asset_url"]) == 1
    destination.write_bytes(b"existing user file")
    with pytest.raises(updates.UpdateError, match="不会自动覆盖"):
        updates.download_release(state, tmp_path, threading.Event(), progress.append, opener=opener)
    assert destination.read_bytes() == b"existing user file"


def test_download_failures_cancel_and_preserve_other_files(tmp_path, monkeypatch):
    unrelated = tmp_path / "do-not-change.txt"
    unrelated.write_text("synthetic existing data", encoding="utf-8")
    state = selected()
    for data in (b"incomplete", b"wrong archive same length".ljust(state["size"], b" ")):
        with pytest.raises(updates.UpdateError):
            updates.download_release(state, tmp_path, threading.Event(), lambda value: None, opener=lambda url: io.BytesIO(data))
        assert not list(tmp_path.rglob("*.part")) and not list(tmp_path.rglob("*.zip"))
    cancelled = threading.Event()
    def progress(value):
        cancelled.set()
    with pytest.raises(updates.UpdateCancelled):
        updates.download_release(state, tmp_path, cancelled, progress, opener=lambda url: io.BytesIO(b"synthetic portable archive"))
    assert not list(tmp_path.rglob("*.part")) and not list(tmp_path.rglob("*.zip"))
    def disk_full(*args, **kwargs):
        raise OSError("synthetic disk full")
    monkeypatch.setattr(updates.tempfile, "NamedTemporaryFile", disk_full)
    with pytest.raises(OSError):
        updates.download_release(state, tmp_path, threading.Event(), lambda value: None, opener=lambda url: io.BytesIO())
    assert unrelated.read_text(encoding="utf-8") == "synthetic existing data"


def test_real_qt_manager_busy_retry_cancel_channel_and_open_folder(qapp, tmp_path, monkeypatch):
    settings = QSettings(str(tmp_path / "update.ini"), QSettings.IniFormat)
    manager = updates.UpdateManager(settings, directory=tmp_path / "downloads", current="0.4.0a3", target="windows-x64")
    assert manager.state["status"] == "idle"  # No automatic network.
    ready, proceed = threading.Event(), threading.Event()
    calls = []
    def check(*args):
        calls.append(args)
        ready.set()
        assert proceed.wait(5)
        return selected()
    monkeypatch.setattr(updates, "check_releases", check)
    manager.check()
    assert _wait_for_asr(ready.is_set)
    manager.check()
    manager.setChannel("stable")
    assert manager.state["channel"] == "preview" and len(calls) == 1
    proceed.set()
    assert _wait_for_asr(lambda: manager.state["status"] == "available")
    actual_download = updates.download_release
    monkeypatch.setattr(updates, "download_release", lambda state, directory, cancel, progress:
        actual_download(state, directory, cancel, progress, opener=lambda url: io.BytesIO(b"synthetic portable archive")))
    manager.download()
    assert _wait_for_asr(lambda: manager.state["status"] == "downloaded")
    assert Path(manager.state["file_path"]).read_bytes() == b"synthetic portable archive"
    opened = []
    monkeypatch.setattr(updates.QDesktopServices, "openUrl", lambda url: opened.append(url))
    manager.openDownloadLocation()
    assert opened[0].toLocalFile() == str(Path(manager.state["file_path"]).parent).replace("\\", "/")
    manager.setChannel("stable")
    other = updates.UpdateManager(settings, directory=tmp_path, current="0.4.0a3")
    assert other.state["channel"] == "stable" and not other.state.get("asset_url")
    monkeypatch.setattr(updates, "check_releases", lambda *args: (_ for _ in ()).throw(updates.UpdateError("合成限流，请重试")))
    manager.check()
    assert _wait_for_asr(lambda: manager.state["status"] == "error")
    assert "重试" in manager.state["message"] and not manager.state.get("file_path")
    monkeypatch.setattr(updates, "check_releases", lambda *args: selected())
    manager.check()
    assert _wait_for_asr(lambda: manager.state["status"] == "available")
    def wait_cancel(state, directory, cancel, progress):
        assert cancel.wait(5)
        raise updates.UpdateCancelled("合成取消")
    monkeypatch.setattr(updates, "download_release", wait_cancel)
    manager.download()
    manager.cancel()
    assert _wait_for_asr(lambda: manager.state["status"] == "cancelled")
    manager.close()
    other.close()
