"""Every supplied topic must reach a real practice surface and interview pool."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from llm_interview_lab.catalog import load_catalog
from llm_interview_lab.knowledge import load_knowledge
from llm_interview_lab.role_interviews import dynamic_coding_candidates
from llm_interview_lab.roles import load_role_catalog


pytestmark = pytest.mark.infrastructure
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def collection():
    manifest = json.loads((ROOT / "curriculum/interviews/question_collection_20260908.json").read_text(encoding="utf-8"))
    catalog = load_catalog(ROOT)
    roles = load_role_catalog(ROOT, curriculum=catalog)
    knowledge = load_knowledge(ROOT, curriculum=catalog)
    return manifest, catalog, roles, knowledge


def test_every_source_item_has_explicit_nonempty_coverage(collection):
    manifest, catalog, _, knowledge = collection
    assert manifest["source"]["sha256"] == "4b9be92238921f4b8f06613a8164aa814ed8b1bb55b3081b83011da6e33f80bb"
    assert manifest["source"]["embedded_images_available"] is False
    assert [row["id"] for row in manifest["coding"]] == [f"C{i:03}" for i in range(1, 41)]
    assert [row["id"] for row in manifest["theory"]] == [f"T{i:03}" for i in range(1, 161)]
    for row in manifest["coding"]:
        assert row["topic"] and row["note"] and row["problem_ids"]
        assert all(catalog.get(pid).recommendable for pid in row["problem_ids"]), row
    for row in manifest["theory"]:
        assert row["topic"] and row["coverage"] and row["card_ids"]
        for cid in row["card_ids"]:
            card = knowledge.get(cid)
            assert card.kind == "eight_stock"
            assert card.one_liner and card.core_answer and card.derivation_or_example
            assert len(card.follow_ups) >= 4 and len(card.pitfalls) >= 2
            assert set(card.acceptance) == {"L1", "L2", "L3", "L4"}
            assert card.source_claims and card.signals


def test_every_theory_number_is_searchable_and_matches_a_real_role(collection):
    manifest, _, roles, knowledge = collection
    for row in manifest["theory"]:
        assert set(row["card_ids"]) <= {card.id for card in knowledge.search(row["id"])}, row
        for cid in row["card_ids"]:
            card = knowledge.get(cid)
            matching_roles = [role for role in roles.roles.values()
                              if set(card.skills) & set(role.skill_weights)
                              and set(card.tracks) & set(role.required_tracks)]
            assert matching_roles, cid
            # Real selector used by both Codex and API interview Context. An
            # explicit topic in the candidate answer must be locally reachable;
            # this is not evidence that a remote model already asked all cards.
            assert any(cid in {c.id for c in knowledge.interview_candidates(
                skills=set(role.skill_weights), tracks=set(role.required_tracks),
                seniority="mid", context=card.title, current_answer=card.title,
            )} for role in matching_roles), cid


def test_all_coding_topics_reach_actual_environment_candidates(collection):
    pytest.importorskip("torch")
    pytest.importorskip("numpy")
    manifest, catalog, roles, _ = collection
    candidates = set()
    for role in roles.roles:
        for seniority in ("intern", "new_grad", "mid"):
            candidates.update(problem.id for problem, _ in dynamic_coding_candidates(
                catalog, roles, {"role_id": role, "seniority": seniority},
            ))
    for row in manifest["coding"]:
        assert row["problem_ids"][0] in candidates, row


def test_all_coding_topics_have_reachable_practice_prerequisites(collection):
    manifest, catalog, _, _ = collection
    masterable = set()
    for pid in catalog.order:
        problem = catalog.get(pid)
        if problem.recommendable and set(problem.prerequisites) <= masterable and all(
            problem.retention_variant(ROOT, stage) for stage in ("d2", "d7")
        ):
            masterable.add(pid)
    for row in manifest["coding"]:
        assert set(catalog.get(row["problem_ids"][0]).prerequisites) <= masterable, row


def test_collection_document_lists_every_source_id(collection):
    manifest, _, _, _ = collection
    document = (ROOT / "docs/content/question-bank-coverage.zh.md").read_text(encoding="utf-8")
    for row in manifest["coding"] + manifest["theory"]:
        assert f"| {row['id']} |" in document
