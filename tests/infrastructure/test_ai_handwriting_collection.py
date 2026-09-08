"""Acceptance of the authored collection, not a substitute for oracle execution."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import re
import shutil
import subprocess

import pytest
import yaml

from llm_interview_lab.ai.context_builder import (
    build_dynamic_role_interview_context_preview,
)
from llm_interview_lab.application import ApplicationService
from llm_interview_lab.catalog import PROBLEM_ASSETS, load_catalog
from llm_interview_lab.knowledge import load_knowledge
from llm_interview_lab.role_interviews import dynamic_coding_candidates
from llm_interview_lab.roles import load_role_catalog
from llm_interview_lab.workspace import init_profile

pytestmark = pytest.mark.infrastructure
ROOT = Path(__file__).resolve().parents[2]
MAPPING = (
    "PT-003",
    "ATT-019",
    "ATT-020",
    "ATT-021",
    "NNL-006",
    "INF-013",
    "ATT-011",
    "PT-022",
    "PT-023",
    "LOSS-004",
    "LOSS-006",
    "PT-024",
    "TML-004",
    "LOSS-010",
    "TNS-014",
    "ATT-015",
    "NNL-014",
    "NNL-005",
    "TOK-001",
    "OPT-005",
    "LOSS-016",
    "TML-006",
    "TML-001",
    "NNL-016",
    "NNL-009",
    "CV-002",
    "TML-007",
    "TML-008",
    "ATT-022",
    "PT-009",
    "PT-010",
    "NNL-017",
    "INF-008",
    "REC-007",
    "REC-008",
    "ATT-008",
    "TML-009",
    "REC-009",
    "VLM-001",
    "TNS-017",
)


@pytest.fixture(scope="module")
def bundle():
    catalog = load_catalog(ROOT)
    return (
        catalog,
        load_knowledge(ROOT, curriculum=catalog),
        load_role_catalog(ROOT, curriculum=catalog),
    )


def test_all_forty_source_specs_have_validated_exercises_and_deep_cards(bundle):
    catalog, knowledge, roles = bundle
    assert len(set(MAPPING)) == 40
    for number, pid in enumerate(MAPPING, 1):
        problem = catalog.get(pid)
        card = knowledge.get(f"COD-AI-{number:03d}")
        assert problem.recommendable and problem.validation_level == "oracle"
        assert card.related_problems[0] == pid
        assert len(set(card.follow_ups)) == 4
        assert set(card.skills) <= set(roles.skills)
        assert card.coding_contract["symbol"] == problem.symbol
        assert (
            card.coding_contract["framework"] == problem.raw["interface"]["framework"]
        )
        assert card.source_claims and card.acceptance


def test_new_assets_are_chinese_executable_stubs_without_published_solutions(bundle):
    catalog, _, _ = bundle
    for pid in set(MAPPING) - {"OPT-005"}:
        problem = catalog.get(pid)
        folder = problem.problem_dir
        assert {p.name for p in folder.iterdir()} == PROBLEM_ASSETS
        text = (folder / "task.md").read_text(encoding="utf-8")
        assert "## 题目要求" in text and "## 口述与追问" in text
        assert "## 来源" in text and "## 共同约定" in text
        for name in ("starter.py", "test_public.py"):
            ast.parse(
                (folder / name).read_text(encoding="utf-8"), feature_version=(3, 10)
            )
        starter = ast.parse((folder / "starter.py").read_text(encoding="utf-8"))
        assert any(isinstance(node, ast.Raise) for node in ast.walk(starter))
        tests = ast.parse(problem.public_tests.read_text(encoding="utf-8"))
        assert (
            sum(
                isinstance(n, ast.FunctionDef) and n.name.startswith("test_")
                for n in tests.body
            )
            >= 5
        )


def test_new_hard_dependencies_can_actually_reach_mastery_and_unlock(bundle):
    catalog, _, _ = bundle
    reachable_mastery = set()
    for pid in catalog.order:
        p = catalog.get(pid)
        if (
            p.recommendable
            and set(p.prerequisites) <= reachable_mastery
            and all(p.retention_variant(ROOT, stage) for stage in ("d2", "d7"))
        ):
            reachable_mastery.add(pid)
    # This is a reachability calculation, not a mutation or grant of learner mastery.
    unlocked = {p.id for p in catalog.unlocked(reachable_mastery)}
    assert set(MAPPING) <= unlocked | reachable_mastery
    for pid in set(MAPPING) - {"OPT-005"}:
        assert set(catalog.get(pid).prerequisites) <= reachable_mastery
        assert catalog.get(pid).retention_variant(ROOT, "d2") is None


def test_quests_cover_collection_without_forcing_it_on_product_roles(bundle):
    catalog, _, roles = bundle
    routes = {
        q.id: q for q in catalog.quests.values() if q.id.startswith("ai_handwriting_")
    }
    assert len(routes) == 5
    assert set(MAPPING) <= {pid for q in routes.values() for pid in q.problem_ids}
    assert (
        "ai_handwriting_post_training"
        in roles.resolve_role("post_training_engineer").recommended_quests
    )
    assert (
        "ai_handwriting_inference"
        in roles.resolve_role("ai_inference_systems_engineer").recommended_quests
    )
    assert not set(routes).intersection(
        roles.resolve_role("ai_product_manager").recommended_quests
    )


def test_experience_cards_keep_anecdotes_grouping_and_date_uncertainty(bundle):
    _, knowledge, _ = bundle
    for number in range(1, 18):
        card = knowledge.get(f"EXP-AI-{number:03d}")
        assert card.kind == "experience_pattern"
        assert all(c.confidence == "anecdotal_unverified" for c in card.source_claims)
        assert "不是公司官方标准" in card.sample_size_or_scope
        assert "缺失年份" in card.caveat
        assert card.observed_pattern and card.drill_prompt and card.provenance
    assert "同作者" in knowledge.get("EXP-AI-014").sample_size_or_scope
    assert "续轮" in knowledge.get("EXP-AI-017").sample_size_or_scope
    assert "未可靠取得完整正文" in knowledge.get("EXP-AI-015").provenance


@pytest.mark.parametrize("numpy_present", [False, True])
def test_numpy_environment_is_explicit_before_practice(
    bundle, monkeypatch, numpy_present
):
    catalog, _, _ = bundle
    actual = importlib.util.find_spec
    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: (
            (object() if numpy_present else None) if name == "numpy" else actual(name)
        ),
    )
    service = ApplicationService(ROOT)
    view = service.problem_view("TML-004")
    assert view["environment_available"] is numpy_present
    assert view["environment"] == (
        "当前可运行" if numpy_present else "需要 NumPy 练习环境"
    )
    assert ApplicationService._problem_environment_available(catalog.get("TOK-001"))


def test_interview_candidates_use_new_real_assets_and_exclude_missing_numpy(
    bundle, monkeypatch
):
    catalog, _, roles = bundle
    # Availability is controlled here; this is candidate selection, not a model or execution smoke.
    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name in {"torch", "numpy"} else None,
    )
    available = set()
    for role in roles.roles:
        for seniority in ("intern", "new_grad", "mid"):
            session = {"role_id": role, "seniority": seniority}
            available.update(
                p.id for p, _ in dynamic_coding_candidates(catalog, roles, session)
            )
    assert set(MAPPING) <= available
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    session = {"role_id": "ai_algorithm_research_engineer", "seniority": "new_grad"}
    remaining = dynamic_coding_candidates(catalog, roles, session)
    assert remaining and all(
        p.raw["interface"]["framework"] == "stdlib" for p, _ in remaining
    )


def test_grpo_and_masked_dpo_do_not_silently_replace_legacy_interfaces(bundle):
    catalog, _, _ = bundle
    assert catalog.get("PT-015").symbol != catalog.get("PT-023").symbol
    assert catalog.get("PT-002").symbol != catalog.get("PT-022").symbol
    assert catalog.get("ATT-004").symbol != catalog.get("ATT-019").symbol
    text = (catalog.get("PT-023").problem_dir / "task.md").read_text(encoding="utf-8")
    assert "PT-015 全 token 平均是不同目标" in text


def test_role_skills_and_interview_strategy_reach_real_context_without_future_list(
    bundle, tmp_path
):
    _, _, roles = bundle
    root = tmp_path / "synthetic-context"
    for relative in ("workspace/schema", "workspace/templates", "coach"):
        shutil.copytree(ROOT / relative, root / relative)
    (root / "workspace/profiles").mkdir()
    (root / ".gitignore").write_text("/workspace/profiles/*\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    init_profile(root, "collection-check")
    preview = build_dynamic_role_interview_context_preview(
        root,
        "collection-check",
        roles,
        role_id="post_training_engineer",
        seniority="intern",
        difficulty="hard",
    )
    assert "逐回答 token mean" in preview.selected_text
    assert (
        "GAE" in preview.selected_text and "old 与 reference" in preview.selected_text
    )
    assert "Ask exactly one main question per turn" in preview.selected_text
    assert '"questions": [' not in preview.selected_text
    assert "candidate_introduction" in preview.selected_text


def test_collection_document_links_and_numbers_match_runtime(bundle):
    catalog, knowledge, _ = bundle
    path = ROOT / "docs/content/ai-handwriting-40.zh.md"
    text = path.read_text(encoding="utf-8")
    for number, pid in enumerate(MAPPING, 1):
        assert f"| AI{number:02d} |" in text and f"[{pid}]" in text
        assert any(
            card.id == f"COD-AI-{number:03d}"
            for card in knowledge.search(f"AI{number:02d}")
        )
    for target in re.findall(r"\]\(([^)]+)\)", text):
        if not target.startswith(("http:", "https:", "#")):
            assert (path.parent / target).is_file(), target
    nodes = yaml.safe_load(
        (ROOT / "curriculum/catalog/ai_handwriting.yaml").read_text(encoding="utf-8")
    )["problems"]
    assert len(nodes) == 39
    assert all(catalog.get(n["id"]).ready for n in nodes)
