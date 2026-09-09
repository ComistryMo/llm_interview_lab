"""Version-1 incremental payloads. Pure file operations; no Qt or user data.

Large files use independently compressed 4 MiB blocks. Small files are grouped
into 64 stable path buckets. The same format can update directly across versions;
it never requires a full installer or an intermediate version's patch.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import zipfile
import zlib

PROTOCOL = 1
BLOCK_SIZE = 4 * 1024 * 1024
SMALL_FILE = 1024 * 1024
MANIFEST_NAMES = {target: f"update-v1-{target}.json" for target in ("windows-x64", "macos-arm64")}
ENTRYPOINTS = {"windows-x64": "LLMInterviewLab.exe", "macos-arm64": "Contents/MacOS/main"}
HASH = re.compile(r"[0-9a-f]{64}\Z")


class PayloadError(RuntimeError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_hash(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(BLOCK_SIZE), b""):
            sha.update(block)
    return sha.hexdigest()


def relative_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if (not isinstance(value, str) or not value or path.is_absolute()
            or any(p in {".", "..", ""} for p in value.split("/"))
            or "\\" in value or ":" in value or "\x00" in value):
        raise PayloadError("更新包包含无效路径，未修改当前应用。")
    return path


def validate_manifest(manifest: dict, target: str, version: str) -> None:
    if (manifest.get("protocol") != PROTOCOL or manifest.get("target") != target
            or manifest.get("version") != version or manifest.get("entrypoint") != ENTRYPOINTS.get(target)):
        raise PayloadError("更新协议、版本或平台不匹配，当前版本保持不变。")
    files, blobs = manifest.get("files"), manifest.get("blobs")
    if not isinstance(files, dict) or not files or not isinstance(blobs, dict):
        raise PayloadError("更新清单缺少文件信息。")
    if manifest["entrypoint"] not in files:
        raise PayloadError("更新清单缺少应用主程序。")
    folded = set()
    for name, item in files.items():
        path = relative_path(name)
        key = name.casefold()
        if key in folded:
            raise PayloadError("更新清单包含重复的大小写路径。")
        folded.add(key)
        if any(str(parent) in files for parent in path.parents if str(parent) != "."):
            raise PayloadError("更新路径与文件或符号链接冲突。")
        if item.get("kind") == "link":
            link = item.get("link", "")
            if not link or PurePosixPath(link).is_absolute() or "\\" in link or ":" in link:
                raise PayloadError("更新包包含无效符号链接。")
            parts = list(path.parent.parts)
            for part in PurePosixPath(link).parts:
                if part == "..":
                    if not parts:
                        raise PayloadError("更新符号链接越出应用目录。")
                    parts.pop()
                elif part != ".":
                    parts.append(part)
            continue
        if (item.get("kind") != "file" or not HASH.fullmatch(str(item.get("sha256", "")))
                or type(item.get("size")) is not int or item["size"] < 0
                or type(item.get("mode")) is not int or item["mode"] & ~0o777):
            raise PayloadError("更新文件属性不完整。")
        if "pack" in item:
            if item["pack"] not in blobs or blobs[item["pack"]].get("kind") != "zip":
                raise PayloadError("更新小文件包缺失。")
        elif (not isinstance(item.get("blocks"), list)
              or sum(block.get("size", 0) for block in item["blocks"]) != item["size"]):
            raise PayloadError("更新数据块清单不完整。")
        else:
            for block in item["blocks"]:
                if (block.get("blob") not in blobs or not HASH.fullmatch(str(block.get("sha256", "")))
                        or not 0 < block.get("size", 0) <= BLOCK_SIZE):
                    raise PayloadError("更新数据块属性无效。")
    for name, blob in blobs.items():
        if (not re.fullmatch(r"update-[0-9a-f]{64}\.(zip|z)", name)
                or name.split("-")[1].split(".")[0] != blob.get("sha256")
                or type(blob.get("size")) is not int or blob["size"] <= 0):
            raise PayloadError("更新下载对象无效。")


def build_payload(archive: Path, target: str, version: str, output: Path) -> dict:
    """Generate release objects directly from a verified official ZIP, not a Profile."""
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"protocol": PROTOCOL, "target": target, "version": version,
                "entrypoint": ENTRYPOINTS[target], "files": {}, "blobs": {}}
    buckets: dict[int, list[tuple[str, bytes]]] = {}

    def blob(data: bytes, suffix: str) -> str:
        sha = digest(data)
        name = f"update-{sha}.{suffix}"
        dest = output / name
        if not dest.exists():
            with dest.open("xb") as stream:
                stream.write(data)
        elif file_hash(dest) != sha:
            raise PayloadError("已有更新对象校验失败。")
        manifest["blobs"][name] = {"sha256": sha, "size": len(data), "kind": suffix}
        return name

    with zipfile.ZipFile(archive) as source:
        for info in sorted(source.infolist(), key=lambda i: i.filename):
            if info.is_dir() or info.filename.startswith("__MACOSX/"):
                continue
            prefix, _, name = info.filename.partition("/")
            expected = "LLMInterviewLab.app" if target == "macos-arm64" else "LLMInterviewLab"
            if prefix != expected or not name:
                raise PayloadError("安装包根目录与目标平台不符。")
            relative_path(name)
            mode = info.external_attr >> 16
            data = source.read(info)
            if stat.S_ISLNK(mode):
                manifest["files"][name] = {"kind": "link", "link": data.decode("utf-8")}
                continue
            item = {"kind": "file", "size": len(data), "sha256": digest(data),
                    "mode": (mode & 0o777) or 0o644}
            manifest["files"][name] = item
            if len(data) < SMALL_FILE:
                bucket = hashlib.sha256(name.encode()).digest()[0] % 64
                buckets.setdefault(bucket, []).append((name, data))
            else:
                item["blocks"] = []
                for start in range(0, len(data), BLOCK_SIZE):
                    block = data[start:start + BLOCK_SIZE]
                    item["blocks"].append({"blob": blob(zlib.compress(block, 9), "z"),
                                           "size": len(block), "sha256": digest(block)})
    for entries in buckets.values():
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as packed:
            for name, data in entries:
                packed.writestr(zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0)), data,
                                compress_type=zipfile.ZIP_DEFLATED)
        name = blob(buffer.getvalue(), "zip")
        for path, _ in entries:
            manifest["files"][path]["pack"] = name
    validate_manifest(manifest, target, version)
    (output / MANIFEST_NAMES[target]).write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _local_file(root: Path, name: str) -> Path | None:
    path = root.joinpath(*relative_path(name).parts)
    # Do not follow a modified installation's link outside its program directory.
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        return None
    return path


def reconstruct(manifest: dict, installed: Path, staging: Path, fetch_blob, cancel, progress) -> dict:
    """Write a new app directory; never mutate or remove the installed application."""
    validate_manifest(manifest, manifest["target"], manifest["version"])
    if staging.exists() or staging.resolve() == installed.resolve():
        raise PayloadError("更新暂存目录必须是一个全新的独立目录。")
    staging.mkdir(parents=True)
    fetched: dict[str, bytes] = {}
    reused_bytes = downloaded_bytes = 0
    entries = manifest["files"]

    def cancelled():
        if cancel.is_set():
            raise PayloadError("已取消更新，当前应用未改变。")

    def fetch(name):
        nonlocal downloaded_bytes
        cancelled()
        if name not in fetched:
            spec = manifest["blobs"][name]
            data = fetch_blob(name, spec)
            if len(data) != spec["size"] or digest(data) != spec["sha256"]:
                raise PayloadError("更新数据下载不完整或校验失败，当前应用未改变。")
            if spec["kind"] == "zip":
                fetched[name] = data
            downloaded_bytes += len(data)
            return data
        return fetched[name]

    for number, (name, item) in enumerate(entries.items()):
        cancelled()
        dest = staging.joinpath(*relative_path(name).parts)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if item["kind"] == "link":
            continue  # Links are created last; never traverse one during extraction.
        old = _local_file(installed, name)
        if old and old.stat().st_size == item["size"] and file_hash(old) == item["sha256"]:
            shutil.copyfile(old, dest)
            reused_bytes += item["size"]
        elif "pack" in item:
            with zipfile.ZipFile(io.BytesIO(fetch(item["pack"]))) as packed:
                info = packed.getinfo(name)
                if info.file_size != item["size"]:
                    raise PayloadError("更新文件大小不匹配。")
                data = packed.read(info)
            with dest.open("xb") as stream:
                stream.write(data)
        else:
            offsets = {}
            if old:
                with old.open("rb") as previous:
                    for offset in range(0, old.stat().st_size, BLOCK_SIZE):
                        block = previous.read(BLOCK_SIZE)
                        offsets[digest(block)] = (offset, len(block))
            with dest.open("xb") as stream:
                for block in item["blocks"]:
                    cancelled()
                    if block["sha256"] in offsets:
                        offset, size = offsets[block["sha256"]]
                        with old.open("rb") as previous:
                            previous.seek(offset)
                            data = previous.read(size)
                        reused_bytes += len(data)
                    else:
                        decoder = zlib.decompressobj()
                        data = decoder.decompress(fetch(block["blob"]), block["size"] + 1)
                        if not decoder.eof or decoder.unused_data:
                            raise PayloadError("更新数据块压缩格式无效。")
                    if len(data) != block["size"] or digest(data) != block["sha256"]:
                        raise PayloadError("更新数据块校验失败。")
                    stream.write(data)
        if file_hash(dest) != item["sha256"]:
            raise PayloadError("重建后的更新文件校验失败，尚未替换应用。")
        os.chmod(dest, item["mode"])
        progress((number + 1) * 100 // len(entries))
    for name, item in entries.items():
        if item["kind"] == "link":
            staging.joinpath(*relative_path(name).parts).symlink_to(item["link"])
    return {"downloaded_bytes": downloaded_bytes, "reused_bytes": reused_bytes,
            "staging": str(staging), "version": manifest["version"]}
