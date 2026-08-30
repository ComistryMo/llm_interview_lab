from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from llm_interview_lab.application import ApplicationService
from llm_interview_lab.catalog import load_catalog
from llm_interview_lab.cli import main
from llm_interview_lab.knowledge import KnowledgeError, load_knowledge, validate_knowledge
from llm_interview_lab.roles import load_role_catalog


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]


def _bundle():
    curriculum = load_catalog(REPO_ROOT)
    return curriculum, load_knowledge(REPO_ROOT, curriculum=curriculum)


def test_research_bundle_has_three_kinds_and_valid_ontology_links() -> None:
    curriculum, knowledge = _bundle()
    roles = load_role_catalog(REPO_ROOT, curriculum=curriculum)

    assert knowledge.schema_version == 1
    assert len(knowledge.sources) >= 45
    assert len(knowledge.cards) >= 40
    assert {card.kind for card in knowledge.cards.values()} == {
        "eight_stock",
        "experience_pattern",
        "coding_prompt",
    }
    assert all(set(card.tracks) <= set(curriculum.tracks) for card in knowledge.cards.values())
    assert all(set(card.skills) <= set(roles.skills) for card in knowledge.cards.values())
    assert all(
        claim.source_id in knowledge.sources
        for card in knowledge.cards.values()
        for claim in card.source_claims
    )
    assert all(
        card.related_problems and set(card.related_problems) <= set(curriculum.problems)
        for card in knowledge.cards.values()
    )

    for card in knowledge.cards.values():
        if card.priority in {"P0", "P1"}:
            assert card.one_liner and card.core_answer and card.derivation_or_example
            assert len(card.follow_ups) >= 2
            assert len(card.pitfalls) >= 2
        if card.kind == "experience_pattern":
            assert all(getattr(card, field) for field in (
                "observed_pattern",
                "candidate_playbook",
                "drill_prompt",
                "sample_size_or_scope",
                "caveat",
                "provenance",
            ))
        if card.kind == "coding_prompt":
            assert set(card.coding_contract or {}) >= {"input", "output", "constraints"}
            assert card.test_focus and card.edge_cases and card.solution_direction


def test_search_order_and_serialization_are_deterministic_and_detached() -> None:
    _, knowledge = _bundle()
    first = [card.id for card in knowledge.search("GRPO reward")]
    second = [card.id for card in knowledge.select(query="GRPO reward")]
    assert first == second
    assert first
    assert [card.id for card in knowledge.search("KV cache", track="systems")] == [
        card.id for card in knowledge.search("KV cache", track="systems")
    ]

    card = knowledge.get("COD-PT-001")
    payload = card.as_dict()
    payload["title"] = "mutated outside catalog"
    assert knowledge.get("COD-PT-001").title != payload["title"]
    catalog_payload = knowledge.as_dict()
    catalog_payload["cards"][0]["title"] = "mutated outside catalog"
    assert knowledge.raw["cards"][0]["title"] != catalog_payload["cards"][0]["title"]


@pytest.mark.parametrize("mutation", ["unknown_source", "duplicate_card", "missing_layer", "unknown_problem"])
def test_validator_rejects_broken_provenance_or_cross_references(mutation: str) -> None:
    curriculum, knowledge = _bundle()
    value = copy.deepcopy(dict(knowledge.raw))
    if mutation == "unknown_source":
        value["cards"][0]["source_claims"][0]["source_id"] = "missing-source"
    elif mutation == "duplicate_card":
        value["cards"].append(copy.deepcopy(value["cards"][0]))
    elif mutation == "missing_layer":
        value["cards"][0].pop("one_liner", None)
    else:
        value["cards"][0]["related_problems"].append("ATT-999")
    with pytest.raises(KnowledgeError):
        validate_knowledge(value, REPO_ROOT, curriculum=curriculum)


def test_application_facade_and_cli_expose_read_only_knowledge(capsys: pytest.CaptureFixture[str]) -> None:
    service = ApplicationService(REPO_ROOT)
    assert len(service.knowledge.cards) >= 40
    assert service.knowledge_card("COD-PT-001").kind == "coding_prompt"
    assert service.get_knowledge_card("COD-PT-001").id == "COD-PT-001"
    assert service.knowledge_search("GRPO", limit=3)
    assert service.knowledge_items(kind="experience_pattern")
    role_cards = service.knowledge_cards(role_id="post_training_engineer", limit=3)
    assert role_cards and all(
        set(item["tracks"]).intersection({"post_training", "llm_algorithm"})
        for item in role_cards
    )
    assert main([
        "knowledge", "search", "动态分辨率", "--role", "VLM Algorithm Engineer",
        "--limit", "5", "--json",
    ]) == 0
    vlm_search = json.loads(capsys.readouterr().out)
    assert any(item["id"] == "EGT-VLM-005" for item in vlm_search)
    detailed = service.knowledge_cards(
        query="DPO", role="post_training_engineer", include_answers=True, limit=1
    )
    assert detailed and detailed[0]["source_records"]

    assert main(["knowledge", "list", "--kind", "coding_prompt", "--json", "--limit", "2"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert len(listed) == 2
    assert all(item["kind"] == "coding_prompt" for item in listed)

    assert main(["knowledge", "show", "COD-PT-001", "--format", "json"]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["id"] == "COD-PT-001"
    assert shown["coding_contract"]["symbol"] == "dpo_loss"
    assert shown["source_records"]

    assert main(["knowledge", "validate", "--with-catalog", "--format", "json"]) == 0
    validation = json.loads(capsys.readouterr().out)
    assert validation["valid"] is True
    assert validation["curriculum_checked"] is True

    assert main([
        "knowledge", "list", "--role", "post_training_engineer", "--limit", "5", "--json"
    ]) == 0
    role_cards = json.loads(capsys.readouterr().out)
    assert role_cards
    assert all("post_training" in item["tracks"] or "llm_algorithm" in item["tracks"] for item in role_cards)


def test_source_registry_is_machine_readable_and_clean_room_scoped() -> None:
    value = json.loads((REPO_ROOT / "references/interview-sources.json").read_text(encoding="utf-8"))
    sources = value["sources"]
    assert len(sources) >= 100
    assert len({item["id"] for item in sources}) == len(sources)
    assert len({item["url"] for item in sources}) == len(sources)
    assert value["clean_room_policy"]["prohibited_usage"]
    assert all(item["retrieved_on"] == "2026-08-30" for item in sources)
    schema = json.loads(
        (REPO_ROOT / "curriculum/schema/knowledge.schema.json").read_text(
            encoding="utf-8"
        )
    )
    allowed_kinds = set(schema["$defs"]["source_kind"]["enum"])
    interop = value["knowledge_schema_interop"]
    for kind in {item["kind"] for item in sources}:
        mapped = interop[f"{kind}_kind_maps_to"]
        assert mapped in allowed_kinds
