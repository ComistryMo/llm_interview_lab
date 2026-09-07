"""Focused contracts for the four original AI handwriting additions."""
from pathlib import Path
import ast

import pytest

from llm_interview_lab.catalog import load_catalog, compute_problem_fingerprint, PROBLEM_ASSETS
from llm_interview_lab.roles import load_role_catalog
from llm_interview_lab.desktop.i18n import problem_brief, problem_title

ROOT = Path(__file__).resolve().parents[2]
ADDED = ("OPT-003", "LOSS-002", "ATT-003", "PT-019")


@pytest.fixture(scope="module")
def catalog():
    return load_catalog(ROOT)


@pytest.mark.parametrize("problem_id", ADDED)
def test_original_assets_are_chinese_and_oracle_validated(catalog, problem_id):
    problem = catalog.get(problem_id)
    assert problem.ready and problem.validation_level == "oracle"
    assert problem.field_runs == 0
    assert problem.raw["validation"]["fingerprint"] == compute_problem_fingerprint(ROOT, problem)
    assert {p.name for p in problem.problem_dir.iterdir()} == PROBLEM_ASSETS
    task = (problem.problem_dir / "task.md").read_text(encoding="utf-8")
    assert "## 任务" in task and "## 接口" in task and "## 口述追问" in task
    assert problem_brief(problem_id, task) == task, "Show full Chinese tasks, not a generic brief"
    assert any("\u4e00" <= c <= "\u9fff" for c in problem_title(problem_id, problem.title))
    starter = ast.parse((problem.problem_dir / "starter.py").read_text(encoding="utf-8"))
    fn = next(n for n in starter.body if isinstance(n, ast.FunctionDef))
    assert fn.name == problem.symbol and isinstance(fn.body[-1], ast.Raise)
    public = ast.parse(problem.public_tests.read_text(encoding="utf-8"))
    assert sum(isinstance(n, ast.FunctionDef) and n.name.startswith("test_") for n in public.body) >= 5
    assert not problem.retention_variant(ROOT, "d2"), "Do not promise missing retention assets"


@pytest.mark.parametrize("problem_id", ADDED)
def test_prerequisites_ready_and_canonical_mapping_matches_reverse_index(catalog, problem_id):
    roles = load_role_catalog(ROOT, curriculum=catalog)
    problem = catalog.get(problem_id)
    reverse = {s.id for s in roles.skills.values() if problem_id in s.related_problems}
    assert set(problem.canonical_skills).issubset(reverse)
    pending, seen = list(problem.prerequisites), set()
    while pending:
        item = pending.pop()
        if item in seen:
            continue
        seen.add(item)
        prerequisite = catalog.get(item)
        assert prerequisite.ready, (problem_id, item)
        assert all(prerequisite.retention_variant(ROOT, stage) for stage in ("d2", "d7")), (problem_id, item)
        pending.extend(prerequisite.prerequisites)
