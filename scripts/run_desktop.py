"""Prepare once, then run this checkout directly; no executable packaging."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import venv


ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--setup", action="store_true", help="Create .venv if missing and install editable desktop dependencies, then exit.")
    parser.add_argument("--data-root", type=Path, help="Use a different data directory; never resets existing data.")
    args, app_args = parser.parse_known_args(argv)
    environment = ROOT / ".venv"
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if args.setup:
        if not python.is_file():
            venv.EnvBuilder(with_pip=True).create(environment)
        return subprocess.call([str(python), "-m", "pip", "install", "-e", ".[desktop,ai,dev]"], cwd=ROOT)
    if not python.is_file():
        print("Missing .venv. Run this script once with --setup (Python 3.11 recommended).", file=sys.stderr)
        return 1

    env = os.environ.copy()
    # Do not accidentally run the editable installation of another worktree.
    env["PYTHONPATH"] = str(ROOT / "src")
    env["PYTHONUTF8"] = "1"
    data = args.data_root or Path(env.get("LLM_LAB_DESKTOP_DATA_ROOT") or ROOT / "workspace/maintainer/manual-uat")
    env["LLM_LAB_DESKTOP_DATA_ROOT"] = str(data.resolve())
    # A previous offscreen probe must not make an ordinary launch invisible.
    # Explicit smoke/screenshot requests retain Qt's existing headless path.
    if not any(arg == "--smoke-test" or arg.startswith("--screenshot") for arg in app_args):
        if sys.platform in {"win32", "darwin"}:
            env["QT_QPA_PLATFORM"] = "windows" if sys.platform == "win32" else "cocoa"
    env.pop("LLM_LAB_PACKAGED", None)
    return subprocess.call([str(python), "-m", "llm_interview_lab.desktop.main", *app_args], cwd=ROOT, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
