"""Validate one ignored maintainer oracle against public and private tests."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

from llm_interview_lab.catalog import CatalogError, Problem, load_catalog
from llm_interview_lab.grader import GraderResult, run_public_tests
from llm_interview_lab.workspace import find_repository_root


ORACLE_PROFILE = "maintainer-oracle"
LEVELS = ("contract", "oracle", "field", "stable")


class OracleValidationError(RuntimeError):
    """Raised when local validation evidence is missing or fails."""


def _paths(repo_root: Path, problem_id: str, stage: str | None) -> tuple[Path, Path, Path]:
    root = repo_root / "workspace" / "profiles" / ORACLE_PROFILE / "oracles" / problem_id
    evidence = root if stage is None else root / "retention" / stage
    return evidence / "submission.py", evidence / "test_private.py", root / "reports"


def _require_ignored(repo_root: Path, path: Path) -> None:
    relative = path.relative_to(repo_root).as_posix()
    result = subprocess.run(
        ["git", "-C", str(repo_root), "check-ignore", "-q", "--", relative],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        raise OracleValidationError("maintainer oracle path is not ignored by Git")


def _variant(problem: Problem, stage: str) -> dict[str, Any]:
    value = problem.raw["retention"].get(stage)
    if not isinstance(value, dict):
        raise OracleValidationError(f"{problem.id} has no runnable {stage} retention asset")
    if value.get("oracle_validated") not in {True, False}:
        raise OracleValidationError(f"{problem.id} {stage} retention metadata is invalid")
    return value


def _run(
    repo_root: Path,
    problem: Problem,
    submission: Path,
    test_path: Path,
    symbol: str,
) -> GraderResult:
    return run_public_tests(
        repo_root=repo_root,
        test_path=test_path,
        submission_path=submission,
        submissions_root=submission.parent,
        expected_symbol=symbol,
        time_limit_ms=problem.time_limit_ms,
        output_limit_kb=problem.output_limit_kb,
    )


def _problem_block(text: str, problem_id: str) -> tuple[int, int, str]:
    start_match = re.search(rf"(?m)^  - id: {re.escape(problem_id)}\s*$", text)
    if start_match is None:
        raise OracleValidationError(f"Catalog node not found while updating: {problem_id}")
    next_match = re.search(r"(?m)^  - id: [A-Z]+-[0-9]{3}\s*$", text[start_match.end():])
    end = start_match.end() + next_match.start() if next_match else len(text)
    return start_match.start(), end, text[start_match.start():end]


def _update_catalog(repo_root: Path, problem_id: str, stage: str | None) -> None:
    for shard in sorted((repo_root / "curriculum" / "catalog").glob("*.yaml")):
        text = shard.read_text(encoding="utf-8")
        if not re.search(rf"(?m)^  - id: {re.escape(problem_id)}\s*$", text):
            continue
        start, end, block = _problem_block(text, problem_id)
        if stage is None:
            marker = re.search(
                r"(?m)^    validation: \{level: (contract|oracle|field|stable), field_runs: ([0-9]+)\}$",
                block,
            )
            if marker is None:
                raise OracleValidationError("Catalog validation marker is missing")
            if marker.group(1) != "contract":
                return
            updated, count = re.subn(
                r"(?m)^    validation: \{level: contract, field_runs: ([0-9]+)\}$",
                r"    validation: {level: oracle, field_runs: \1}",
                block,
                count=1,
            )
        else:
            stage_start = re.search(rf"(?m)^      {stage}:\s*$", block)
            if stage_start is None:
                raise OracleValidationError(f"Catalog has no {stage} retention block")
            tail = block[stage_start.start():]
            next_stage = re.search(r"(?m)^      d[27]:\s*$", tail[stage_start.end() - stage_start.start():])
            stage_end = (
                stage_start.end() + next_stage.start()
                if next_stage is not None
                else len(block)
            )
            stage_block = block[stage_start.start():stage_end]
            if re.search(r"(?m)^        oracle_validated: true$", stage_block):
                return
            stage_updated, count = re.subn(
                r"(?m)^        oracle_validated: false$",
                "        oracle_validated: true",
                stage_block,
                count=1,
            )
            updated = block[:stage_start.start()] + stage_updated + block[stage_end:]
        if count != 1:
            raise OracleValidationError("Catalog validation marker could not be updated exactly once")
        shard.write_text(text[:start] + updated + text[end:], encoding="utf-8", newline="\n")
        return
    raise OracleValidationError(f"Catalog shard not found for {problem_id}")


def _write_report(
    reports: Path,
    problem_id: str,
    stage: str | None,
    public: GraderResult,
    private: GraderResult,
) -> dict[str, Any]:
    label = stage or "base"
    report = {
        "schema_version": 1,
        "problem_id": problem_id,
        "stage": stage,
        "validated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "submission_sha256": public.submission_sha256,
        "public": {"status": public.status, "passed": public.passed, "failed": public.failed},
        "private": {"status": private.status, "passed": private.passed, "failed": private.failed},
        "result": "passed" if public.status == private.status == "passed" else "failed",
    }
    reports.mkdir(parents=True, exist_ok=True)
    (reports / f"{label}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    markdown = (
        f"# {problem_id} {label} Oracle Validation\n\n"
        f"- Result: **{report['result'].upper()}**\n"
        f"- Public: {public.status} ({public.passed} passed, {public.failed} failed)\n"
        f"- Private/property: {private.status} ({private.passed} passed, {private.failed} failed)\n"
        f"- Submission SHA-256: `{public.submission_sha256}`\n"
    )
    (reports / f"{label}.md").write_text(markdown, encoding="utf-8", newline="\n")
    return report


def validate(problem_id: str, stage: str | None = None) -> dict[str, Any]:
    repo_root = find_repository_root()
    problem = load_catalog(repo_root).get(problem_id)
    if not problem.ready or problem.public_tests is None or problem.symbol is None:
        raise OracleValidationError("only ready problems can be oracle validated")
    submission, private_test, reports = _paths(repo_root, problem_id, stage)
    _require_ignored(repo_root, submission)
    if not submission.is_file() or not private_test.is_file():
        raise OracleValidationError("ignored oracle submission and private test are both required")
    if stage is None:
        public_test, symbol = problem.public_tests, problem.symbol
    else:
        variant = _variant(problem, stage)
        asset_root = repo_root.joinpath(*Path(variant["assets"]["root"]).parts)
        public_test = asset_root / variant["assets"]["public_tests"]
        symbol = variant["interface"]["symbol"]
    public = _run(repo_root, problem, submission, public_test, symbol)
    private = _run(repo_root, problem, submission, private_test, symbol)
    report = _write_report(reports, problem_id, stage, public, private)
    if report["result"] != "passed":
        raise OracleValidationError(
            f"validation failed: public={public.status}, private={private.status}"
        )
    _update_catalog(repo_root, problem_id, stage)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("problem_id")
    parser.add_argument("--stage", choices=("d2", "d7"))
    args = parser.parse_args(argv)
    try:
        print(json.dumps(validate(args.problem_id, args.stage), ensure_ascii=False, indent=2))
        return 0
    except (CatalogError, OracleValidationError, OSError) as error:
        print(json.dumps({"result": "failed", "error": str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
