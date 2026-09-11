"""Protocol-3 request budgeting in Unicode characters and UTF-8 bytes, not tokens.

The complete interview remains on disk. Only exact supplied answer ranges can
be cited in this turn. Summaries/indexes never grant evidence access.
"""
from copy import deepcopy
import hashlib
import json
from .base import ContextPart, ContextPreview

MAX_CHARS = 64000
MAX_BYTES = 160000
HISTORY_CHARS = 14000
WIRE_RESERVE_CHARS = 14000  # instruction + schema also occur in transport envelopes


def part(key, label, content, sensitive=False):
    if not isinstance(content, str):
        content = json.dumps(content, ensure_ascii=False, separators=(",", ":"))
    return ContextPart(key, label, content, hashlib.sha256(content.encode()).hexdigest(), sensitive=sensitive)


def measure(text):
    return {"characters": len(text), "utf8_bytes": len(text.encode("utf-8")), "tokens": None}


def enforce_wire_budget(text):
    value = measure(text)
    if value["characters"] > MAX_CHARS or value["utf8_bytes"] > MAX_BYTES:
        raise ValueError("本轮必要上下文超过请求预算；请缩短当前回答或减少本轮材料后重试。原回答未截断，未发送请求。")
    return value


def bounded_parts(parts, contract, session):
    """Current Q/A, target evidence and contradictions are never truncated."""
    by_id = {p.id: p for p in parts}
    history = json.loads(by_id["dialogue_history"].content)
    qid = contract["request_basis"]["question_id"]
    state = session["interviewer_state"]
    selected = {key for ref in contract["expert_references"] for key in ref["claim_ids"]}
    selected.update(key for key, conflict in state["contradictions"].items() if not conflict["resolved"])
    selected.update(p["claim_id"] for p in state["probes"][-2:] if p["claim_id"])
    compact = deepcopy(state)
    compact["claims"] = {key: c for key, c in state["claims"].items() if key in selected}
    compact["gaps"] = {key: g for key, g in state["gaps"].items() if key in selected}
    compact["contradictions"] = {key: c for key, c in state["contradictions"].items() if key in selected}
    experience_ids = {c["experience_id"] for c in compact["claims"].values()}
    compact["experiences"] = {key: e for key, e in state["experiences"].items() if key in experience_ids}
    compact["closures"] = [c for c in state["closures"] if c["claim_id"] in selected][-8:]
    compact["probes"] = [p for p in state["probes"] if p["claim_id"] in selected][-8:]
    compact.pop("applied_answers")
    contract["interviewer_state"] = compact
    contract["state_index"] = [{"claim_id": key, "topic_id": c["topic_id"], "criterion": c["criterion"],
        "status": c["criterion_status"], "is_evidence": False} for key, c in list(state["claims"].items())[-40:]]
    contract["state_index_omitted"] = max(0, len(state["claims"]) - 40)
    contract["allowed_probe_claim_ids"] = sorted(selected)
    contract["probe_target_rule"] = "仅已加载目标或本轮新建主张；core允许当前回答中新出现的真实岗位主张。索引不是引文。"
    # Full current answer, even for a preview before locking. Digest is the
    # locked record's digest when available, never an invented surrogate hash.
    texts = {h["question_id"]: h.get("answer", "") for h in history}
    texts[qid] = by_id.get("candidate_answer", part("", "", "")).content
    registry = json.loads(by_id["coding_sources"].content) if "coding_sources" in by_id else []
    texts.update({s["source_id"]: s["text"] for s in registry})
    required_ranges = {qid: [(0, len(texts[qid]))]} if texts[qid] else {}
    required_ranges.update({s["source_id"]: [(0, len(s["text"]))] for s in registry if s["text"]})
    quotes = [q for c in compact["claims"].values() for q in c["evidence"]]
    quotes += [e["evidence"] for e in compact["experiences"].values()]
    quotes += [q for c in compact["contradictions"].values() for q in (c["first"], c["second"])]
    quotes += [c["evidence"] for c in compact["closures"]]
    for quote in quotes:
        required_ranges.setdefault(quote["question_id"], []).append((quote["start"], quote["end"]))
    recent = []
    for item in reversed(history[-2:]):
        if sum(len(json.dumps(h, ensure_ascii=False)) for h in recent + [item]) <= HISTORY_CHARS:
            recent.insert(0, item)
    contract["context_budget"] = {"max_characters": MAX_CHARS, "max_utf8_bytes": MAX_BYTES,
        "history_soft_characters": HISTORY_CHARS, "wire_reserve_characters": WIRE_RESERVE_CHARS,
        "unit_note": "字符/UTF-8字节，不是token。Codex复用线程的累计上下文不在此上限内。",
        "trim_order": ["old_history", "recent_history_oldest_first", "optional_knowledge_candidates"],
        "required_overflow": "reject_before_transport"}
    # A reviewed criterion does not replace a whole ordinary card. Keep the
    # original pool/order, deduplicating cards only; it remains budget-optional.
    optional = []
    for resource in parts:
        if resource.id == "knowledge_candidates":
            content = json.loads(resource.content)
            seen = set()
            cards = []
            for card in content["cards"]:
                if card["id"] not in seen:
                    seen.add(card["id"])
                    cards.append(card)
            content["cards"] = cards
            optional.append(part(resource.id, resource.label, content, resource.sensitive))
    required = [p for p in parts if p.id not in ("dialogue_history", "interview_contract", "knowledge_candidates")]
    def assemble():
        # Recompute before serializing/hashing on EVERY budget iteration.
        contract["loaded_knowledge_ids"] = list(dict.fromkeys(
            [c["id"] for p in optional for c in json.loads(p.content)["cards"]]
            + [r["topic_id"] for r in contract["expert_references"]]))
        scopes = deepcopy(required_ranges)
        for item in recent:
            if item.get("answer"):
                scopes[item["question_id"]] = [(0, len(item["answer"]))]
        sources = []
        for source_id, spans in scopes.items():
            spans = sorted(set(spans))
            sources.append({"question_id": source_id,
                "answer_sha256": next((s["sha256"] for s in registry if s["source_id"] == source_id), session["answers"].get(source_id, {}).get("sha256", "")),
                "ranges": [{"start": start, "end": end} for start, end in spans]})
        contract["sent_answer_sources"] = sources
        evidence = [{**source, "question": next((q["prompt"] for q in session["questions"] if q["question_id"] == source["question_id"]), ""),
            "ranges": [{**span, "text": texts[source["question_id"]][span["start"]:span["end"]]} for span in source["ranges"]]}
            for source in sources if source["question_id"] != qid and source["question_id"] not in {h["question_id"] for h in recent}
            and source["question_id"] not in {s["source_id"] for s in registry}]
        contract["history_omitted_count"] = len(history) - len(recent)
        assembled = required + optional + [part("dialogue_history", "本轮最近必要问答", recent, True),
            part("evidence_sources", "目标与矛盾原文（其余历史索引不可引用）", evidence, True)]
        assembled.insert(1, part("interview_contract", "本轮证据、缺口、岗位范围与决策协议", contract, True))
        return assembled
    while True:
        assembled = assemble()
        text = ContextPreview("interviewer", session["profile_id"], tuple(assembled)).selected_text
        if len(text) <= MAX_CHARS - WIRE_RESERVE_CHARS and len(text.encode()) <= MAX_BYTES - WIRE_RESERVE_CHARS * 3:
            return assembled
        if recent:
            recent.pop(0)
        elif optional:
            optional.clear()
        else:
            raise ValueError("当前完整回答、材料或必要证据超过上下文预算；请缩短回答或减少本轮材料，未截断原文或发起请求。")
