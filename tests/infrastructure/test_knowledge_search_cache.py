"""A public-content cache preserves search semantics and revalidates edits."""
import shutil
from pathlib import Path

import pytest

from llm_interview_lab.application import ApplicationService
from llm_interview_lab.knowledge import KnowledgeError

ROOT = Path(__file__).resolve().parents[2]


def test_cached_search_matches_original_filters_order_and_invalidates(tmp_path, monkeypatch):
    # Public content only. No Profile, keyring, connection, or private answers.
    shutil.copytree(ROOT / "curriculum", tmp_path / "curriculum")
    service = ApplicationService(tmp_path)
    catalog = service.knowledge_catalog()
    original = service._knowledge_search_text
    built = []
    def measured(card):
        built.append(card.id)
        return original(card)
    monkeypatch.setattr(service, "_knowledge_search_text", measured)
    for query in ("GRPO", "KL loss", "EGT-QB-028", "mask token", "ZeRO", "LoRA rank", "注意力", "AdamW") * 2:
        expected = [card.id for card in catalog.cards.values() if all(term.casefold() in original(card) for term in query.split())]
        assert [card.id for card in service.search_knowledge(query)] == expected
    assert len(built) == len(set(built)) == len(catalog.cards)
    expected = [card.id for card in catalog.cards.values()
                if card.kind == "eight_stock" and "GRPO".casefold() in original(card)]
    assert [card.id for card in service.search_knowledge("GRPO", kind="eight_stock")] == expected
    path = tmp_path / "curriculum/interviews/knowledge.yaml"
    source = path.read_text(encoding="utf-8")
    first = next(iter(catalog.cards.values()))
    path.write_text(source.replace(first.title, first.title + " CACHE_REFRESH_PROBE", 1), encoding="utf-8")
    assert [card.id for card in service.search_knowledge("CACHE_REFRESH_PROBE")] == [first.id]
    assert service.knowledge_catalog() is not catalog
    # Invalid content must not silently fall back to the previously cached result.
    path.write_text("cards: [invalid", encoding="utf-8")
    with pytest.raises(KnowledgeError):
        service.search_knowledge("CACHE_REFRESH_PROBE")
    path.write_text(source, encoding="utf-8")
    assert not service.search_knowledge("CACHE_REFRESH_PROBE")
    refreshed = service.knowledge_catalog(reload=True)
    assert not service._knowledge_search_documents
    assert len(refreshed.cards) == len(catalog.cards)
