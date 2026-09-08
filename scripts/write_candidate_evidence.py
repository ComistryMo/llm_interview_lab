"""Publish only the explicitly named synthetic production-page captures."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
from llm_interview_lab import __version__


PAGES = ("home", "setup", "answer", "coding", "report", "connections", "settings")
INPUTS = ("src/llm_interview_lab/desktop", "src/llm_interview_lab/application.py",
          "src/llm_interview_lab/roles.py", "curriculum/roles",
          "src/llm_interview_lab/__init__.py")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--before-commit", required=True)
    parser.add_argument("--after-commit", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    destination = root / "docs/images/candidate-20260909"
    result = {"version": __version__, "language": "zh-CN", "synthetic": True,
              "renderer": "production AppController + Main.qml; Windows/software",
              "logical_size": [1280, 800], "font_scale": 1.0,
              "business_evidence": "Local synthetic sessions and drafts; NO real AI/microphone claims",
              "sets": {}}
    for label, folder, revision in (("before", args.before, args.before_commit),
                                    ("after", args.after, args.after_commit)):
        commit = subprocess.check_output(["git", "rev-parse", revision], cwd=root, text=True).strip()
        inputs = {}
        names = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", commit, "--", *INPUTS], cwd=root, text=True).splitlines()
        for name in names:
            raw = subprocess.check_output(["git", "show", f"{commit}:{name}"], cwd=root)
            inputs[name] = hashlib.sha256(raw).hexdigest()
        entries = []
        for page in PAGES:
            for theme in ("light", "dark"):
                name = f"{page}-{theme}.png"
                raw = (folder / name).read_bytes()
                assert raw[:8] == b"\x89PNG\r\n\x1a\n"
                width, height = struct.unpack(">II", raw[16:24])
                target = destination / label / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(folder / name, target)
                entries.append({"page": page, "theme": theme,
                                "path": target.relative_to(root).as_posix(),
                                "pixel_size": [width, height],
                                "sha256": hashlib.sha256(raw).hexdigest()})
        result["sets"][label] = {"source_commit": commit, "source_inputs": inputs, "screenshots": entries}
    (destination / "manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Published {len(PAGES) * 4} synthetic captures: {destination}")


if __name__ == "__main__":
    main()
