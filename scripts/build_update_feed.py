"""Generate and round-trip the mandatory protocol-v1 release resources."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import stat
import zipfile

from llm_interview_lab.desktop.update_payload import build_payload, reconstruct, file_hash, MANIFEST_NAMES


ARCHIVES = {"windows-x64": "LLMInterviewLab-Windows-x64-portable.zip",
            "macos-arm64": "LLMInterviewLab-macOS-arm64.app.zip"}


def build_and_verify(release: Path, version: str) -> None:
    for target, archive_name in ARCHIVES.items():
        manifest = build_payload(release / archive_name, target, version, release)
        with tempfile.TemporaryDirectory(prefix="llm-update-verify-") as directory:
            root = Path(directory)
            (root / "empty").mkdir()
            result = reconstruct(manifest, root / "empty", root / "rebuilt",
                                 lambda name, spec: (release / name).read_bytes(), threading.Event(), lambda _: None)
            with zipfile.ZipFile(release / archive_name) as archive:
                originals = {info.filename.partition("/")[2]: info for info in archive.infolist()
                             if not info.is_dir() and not info.filename.startswith("__MACOSX/")}
                assert set(originals) == set(manifest["files"])
                for name, item in manifest["files"].items():
                    path = root / "rebuilt" / name
                    original = archive.read(originals[name])
                    if item["kind"] == "link":
                        assert stat.S_ISLNK(originals[name].external_attr >> 16)
                        assert path.is_symlink() and str(path.readlink()) == original.decode("utf-8")
                    else:
                        assert file_hash(path) == hashlib.sha256(original).hexdigest()
            print(json.dumps({"target": target, "files": len(manifest["files"]),
                              "objects": len(manifest["blobs"]), "reconstructed": True,
                              "downloaded_bytes": result["downloaded_bytes"]}))
    objects = sorted({*release.glob("update-*.json"), *release.glob("update-*.zip"), *release.glob("update-*.z")})
    if len(objects) + 6 > 1000:
        raise RuntimeError("Update object count exceeds the supported release asset budget")
    with (release / "SHA256SUMS.txt").open("a", encoding="utf-8") as stream:
        for path in objects:
            stream.write(f"{file_hash(path)}  {path.name}\n")
    for name in MANIFEST_NAMES.values():
        if not (release / name).is_file():
            raise RuntimeError("Both platform update manifests are mandatory")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--version", required=True)
    arguments = parser.parse_args()
    build_and_verify(arguments.release, arguments.version)
