"""Exercise both packaged workers without Python on PATH or learner data."""
import os
from pathlib import Path
import subprocess


def check_workers(executable: Path, scratch: Path, environment: dict) -> None:
    script = scratch / "synthetic_worker.py"
    script.write_text("print(sum(map(int, input().split())))\n", encoding="utf-8")
    env = {**environment, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    # Neither worker may depend on a separate Python installation.
    env["PATH"] = (os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
                   if os.name == "nt" else "/usr/bin:/bin")
    result = subprocess.run([str(executable), "--script-worker", str(script)],
                            input="2 3 4\n", capture_output=True, text=True,
                            cwd=scratch, env=env, timeout=30)
    if result.returncode or result.stdout.strip() != "9":
        raise RuntimeError(f"packaged script worker failed: {result.stdout}{result.stderr}")
    tests = scratch / "test_synthetic_worker.py"
    tests.write_text("import unittest\n\nclass WorkerTest(unittest.TestCase):\n"
                     "    def test_arithmetic(self):\n        self.assertEqual(2 + 3, 5)\n",
                     encoding="utf-8")
    result = subprocess.run([str(executable), "--grader-worker", str(tests), "-q"],
                            capture_output=True, text=True, cwd=scratch, env=env, timeout=30)
    if result.returncode or "1 passed" not in result.stdout:
        raise RuntimeError(f"packaged pytest worker failed: {result.stdout}{result.stderr}")

