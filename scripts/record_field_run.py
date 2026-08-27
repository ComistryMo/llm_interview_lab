"""Record one anonymous real-user run locally and update public aggregates."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import re
import subprocess
import sys

from llm_interview_lab.catalog import CatalogError, load_catalog
from llm_interview_lab.workspace import find_repository_root


RUN_ID = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
STATUSES = ("completed", "blocked", "abandoned")


class FieldRunError(RuntimeError):
    """Raised when anonymous field evidence is invalid or duplicated."""


def _require_ignored(repo_root: Path, path: Path) -> None:
    relative = path.relative_to(repo_root).as_posix()
    result = subprocess.run(
        ["git", "-C", str(repo_root), "check-ignore", "-q", "--", relative],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        raise FieldRunError("field-run evidence path is not ignored by Git")


def _update_aggregate(repo_root: Path, problem_id: str, completed: bool) -> None:
    pattern = re.compile(
        r"(?m)^    validation: \{level: (contract|oracle|field|stable), "
        r"field_runs: ([0-9]+)(, fingerprint: [0-9a-f]{64})?\}$"
    )
    for shard in sorted((repo_root / "curriculum/catalog").glob("*.yaml")):
        text = shard.read_text(encoding="utf-8")
        start = re.search(rf"(?m)^  - id: {re.escape(problem_id)}\s*$", text)
        if start is None:
            continue
        next_node = re.search(r"(?m)^  - id: (?:[A-Z]+|CAP-[A-Z]+)-[0-9]{3}\s*$", text[start.end():])
        end = start.end() + next_node.start() if next_node else len(text)
        block = text[start.start():end]
        marker = pattern.search(block)
        if marker is None:
            raise FieldRunError("Catalog validation marker is missing")
        level = "field" if completed and marker.group(1) == "oracle" else marker.group(1)
        replacement = (
            f"    validation: {{level: {level}, field_runs: {int(marker.group(2)) + 1}"
            f"{marker.group(3) or ''}}}"
        )
        updated = block[:marker.start()] + replacement + block[marker.end():]
        shard.write_text(text[:start.start()] + updated + text[end:], encoding="utf-8", newline="\n")
        return
    raise FieldRunError(f"Catalog node not found: {problem_id}")


def record_field_run(
    repo_root: Path,
    *,
    anonymous_run_id: str,
    problem_id: str,
    quest_id: str,
    completion_status: str,
    issue_count: int,
    validation_date: str,
) -> dict[str, object]:
    if RUN_ID.fullmatch(anonymous_run_id) is None:
        raise FieldRunError("anonymous run ID must be a non-identifying lowercase slug")
    if completion_status not in STATUSES:
        raise FieldRunError("invalid completion status")
    if type(issue_count) is not int or issue_count < 0:
        raise FieldRunError("issue count must be a non-negative integer")
    try:
        date.fromisoformat(validation_date)
    except ValueError as error:
        raise FieldRunError("validation date must use YYYY-MM-DD") from error
    catalog = load_catalog(repo_root)
    problem = catalog.get(problem_id)
    quest = catalog.quests.get(quest_id)
    if quest is None or problem_id not in quest.problem_ids:
        raise FieldRunError("problem is not part of the selected quest")
    if not problem.recommendable:
        raise FieldRunError("contract-only problems cannot receive field validation")
    evidence = repo_root / "workspace/profiles/maintainer-oracle/field_runs.jsonl"
    _require_ignored(repo_root, evidence)
    key = (anonymous_run_id, problem_id, quest_id)
    existing = []
    if evidence.exists():
        for line in evidence.read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            existing.append(item)
            if (item["anonymous_run_id"], item["problem_id"], item["quest_id"]) == key:
                raise FieldRunError("this anonymous run is already recorded for the problem")
    record = {
        "schema_version": 1,
        "anonymous_run_id": anonymous_run_id,
        "problem_id": problem_id,
        "quest_id": quest_id,
        "completion_status": completion_status,
        "issue_count": issue_count,
        "validation_date": validation_date,
    }
    evidence.parent.mkdir(parents=True, exist_ok=True)
    with evidence.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    _update_aggregate(repo_root, problem_id, completion_status == "completed")
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--anonymous-run-id", required=True)
    parser.add_argument("--problem-id", required=True)
    parser.add_argument("--quest-id", required=True)
    parser.add_argument("--status", choices=STATUSES, required=True)
    parser.add_argument("--issue-count", type=int, required=True)
    parser.add_argument("--date", required=True)
    args = parser.parse_args(argv)
    try:
        record = record_field_run(
            find_repository_root(),
            anonymous_run_id=args.anonymous_run_id,
            problem_id=args.problem_id,
            quest_id=args.quest_id,
            completion_status=args.status,
            issue_count=args.issue_count,
            validation_date=args.date,
        )
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return 0
    except (CatalogError, FieldRunError, OSError, json.JSONDecodeError) as error:
        print(json.dumps({"result": "failed", "error": str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
