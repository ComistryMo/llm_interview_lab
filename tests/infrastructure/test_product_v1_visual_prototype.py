"""Contract checks for the isolated Product V1 visual-direction prototype.

These checks intentionally do not import the production desktop controller or
run the full application.  The prototype is presentation-only and all evidence
must remain synthetic.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs" / "images" / "product-v1" / "manifest.json"
QML = ROOT / "src" / "llm_interview_lab" / "desktop" / "qml" / "prototypes" / "ProductV1WorkbenchPrototype.qml"
DESIGN = ROOT / "docs" / "design" / "product-v1-visual-directions.zh.md"


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert data[12:16] == b"IHDR"
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def test_visual_direction_manifest_is_complete_and_synthetic() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["synthetic"] is True
    assert manifest["language"] == "zh-CN"
    assert manifest["viewport"] == "1280x800"
    assert re.fullmatch(r"[0-9a-f]{40}", manifest["source_commit"])

    expected = {
        (direction, theme)
        for direction in ("graphite-blue", "obsidian-violet", "warm-frost")
        for theme in ("light", "dark")
    }
    actual = {(item["direction"], item["theme"]) for item in manifest["screenshots"]}
    assert actual == expected
    assert len(manifest["screenshots"]) == 6

    for item in manifest["screenshots"]:
        path = ROOT / item["path"]
        assert path.is_file(), item["path"]
        assert item["synthetic"] is True
        assert (item["width"], item["height"]) == (1280, 800)
        assert _png_size(path) == (1280, 800)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == item["sha256"], item["path"]


def test_prototype_has_realistic_scope_without_production_side_effects() -> None:
    source = QML.read_text(encoding="utf-8")
    assert "LOSS-014" in source
    assert "prototypeDirection" in source
    assert "prototypeDark" in source
    assert "synthetic: true" in source
    assert "AppController" not in source
    assert "Private Tests" not in source
    assert "通过率" not in source


def test_design_note_documents_all_directions_and_recommendation() -> None:
    source = DESIGN.read_text(encoding="utf-8")
    for name in ("Graphite Blue", "Obsidian Violet", "Warm Frost"):
        assert name in source
    assert "推荐主方向：Graphite Blue" in source
    assert "1280×800" in source
    assert "synthetic" in source
