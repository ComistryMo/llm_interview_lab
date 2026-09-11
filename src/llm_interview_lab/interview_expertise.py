"""Bounded public-method routing and criterion retrieval for evidence protocol 3.

Lexical cues select a diagnostic tool, never determine whether an answer is
correct. No models, profiles, private files or plugin discovery are used here.
"""
import hashlib
import json
import re
from pathlib import Path

METHODS = (
    "mechanism-implementation-probe", "experiment-causality-audit",
    "counterexample-constraint-transfer", "ownership-consistency-check",
    "code-defense-failure-analysis",
)
TOPICS = {
    "EGT-QB-028": ("grpo", "组内", "组优势"),
    "EGT-QB-026": ("dpo", "偏好对"),
    "EGT-QB-030": ("kl", "散度", "reference"),
    "EGT-QB-014": ("sft", "loss mask", "packing", "监督"),
    "EGT-QB-048": ("attention", "注意力", "缩放", "sqrt"),
    "EGT-QB-058": ("gqa", "mqa", "kv头"),
    "EGT-QB-011": ("kv cache", "缓存", "cache"),
    "EGT-QB-001": ("adam", "adamw", "衰减"),
}
CRITERION_CUES = {
    "advantage": ("优势", "方差", "奖励组"), "reference": ("reference", "old", "参考"),
    "ratio": ("ratio", "概率比", "更新", "detach"), "reduction": ("长度", "归约", "分母"),
    "validation": ("评测", "奖励", "收益", "对照", "实验"), "mask": ("mask", "屏蔽"),
    "shift": ("shift", "错位", "label"), "packing": ("packing", "拼接"),
    "scaling": ("缩放", "方差", "sqrt"), "cache": ("缓存", "cache", "位置"),
    "decay": ("衰减", "正则", "l2"), "implementation": ("shape", "实现", "代码", "张量"),
    "mechanism": ("原理", "机制", "公式"), "boundary": ("边界", "全零", "无效"),
}


def _mentions(text, cues):
    folded = text.casefold()
    return any(re.search(r"(?<![a-z])" + re.escape(cue) + r"(?![a-z])", folded)
               if cue.isascii() else cue in folded for cue in cues)


def retrieve(knowledge, role, state, answer, question, *, limit=3):
    """Gap → new mechanism → untested criterion → role recall, stable ties."""
    lexical = knowledge.interview_candidates(skills=set(role.skill_weights), tracks=set(role.required_tracks),
        seniority=None, context=question + "\n" + answer, current_answer=answer, limit=8)
    eligible = {c.id: c for c in lexical}
    for card in knowledge.cards.values():
        if card.raw.get("expert_reference") and set(card.skills) & set(role.skill_weights):
            eligible[card.id] = card
    ranked = []
    for card in eligible.values():
        expert = card.raw.get("expert_reference")
        if not expert:
            continue
        named = _mentions(answer, TOPICS.get(card.id, (card.title,)))
        question_named = _mentions(question, TOPICS.get(card.id, (card.title,)))
        for criterion, reference in expert["criteria"].items():
            claims = [(key, c) for key, c in state["claims"].items()
                      if c["topic_id"] == card.id and c["criterion"] == criterion]
            gaps = [key for key, _ in claims if state["gaps"][key]["status"] == "open"]
            specific = _mentions(answer, CRITERION_CUES.get(criterion, (criterion,)))
            resolved = bool(claims) and not gaps
            priority = (0 if gaps and (named or (question_named and specific)) else
                        1 if (specific and (named or question_named)) or (named and not claims) else
                        2 if question_named and not claims else 3)
            # Resolved criteria rank below new criteria even in the same topic.
            rank = (5 if resolved else priority, not specific, not question_named, not named, card.id, criterion)
            ranked.append((rank, {"topic_id": card.id, "criterion": criterion, "claim_ids": gaps,
                "priority": priority, "reason": ("relevant_open_gap", "current_mechanism", "untested_criterion", "role_recall")[priority],
                "version": expert["version"], "sha256": hashlib.sha256(json.dumps(expert, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
                "assumptions": expert["assumptions"], "source_pins": expert["source_pins"],
                "source_ids": [s.source_id for s in card.source_claims], "reference": reference}))
    return [item for _, item in sorted(ranked, key=lambda row: row[0])[:limit]]


def route_methods(stage, state, answer, role_id, difficulty, references):
    if stage not in ("introduction", "experience", "theory", "coding"):
        return []
    scores = {method: 0 for method in METHODS}
    reasons = {method: [] for method in METHODS}
    def add(index, score, reason):
        scores[METHODS[index]] += score
        reasons[METHODS[index]].append(reason)
    if references or _mentions(answer, ("实现", "公式", "梯度", "shape")):
        add(0, 3, "current_mechanism_or_loaded_criterion")
    if _mentions(answer, ("效果", "收益", "提高", "评测", "消融", "对照", "成功率", "奖励上涨", "reward上涨")):
        add(1, 5, "current_result_claim")
    if _mentions(answer, ("不知道", "不清楚", "没做过", "记不清", "边界", "如果", "恒定", "一定")):
        add(2, 5, "current_boundary_or_adjacent_entry")
    if _mentions(answer, ("我们", "不是我", "团队", "负责")):
        add(3, 3 if stage == "introduction" else 1, "current_ownership_scope")
    if any(not c["resolved"] for c in state["contradictions"].values()):
        add(3, 6, "unresolved_contradiction")
    if _mentions(answer, ("前面两处", "前后", "之前说", "同一实验")):
        add(3, 5, "current_consistency_question_not_a_verdict")
    if _mentions(answer, ("nan", "报错", "越界", "def ", "反向传播")):
        add(4, 6, "described_implementation_failure")
    if difficulty == "hard" and references and stage != "introduction":
        add(2, 2, "hard_requires_constraint_transfer")
    if any(g["status"] == "open" for g in state["gaps"].values()):
        add(0, 1, "existing_evidence_gap")
    return [{"id": method, "routing_reasons": reasons[method], "role_id": role_id,
             "stage": stage, "difficulty": difficulty}
            for method in sorted(METHODS, key=lambda m: (-scores[m], METHODS.index(m))) if scores[method]][:2]


def load_methods(repo_root: Path, selections):
    root = Path(repo_root).resolve()
    loaded = []
    for selection in selections:
        method = selection["id"]
        if method not in METHODS:
            raise ValueError("面试方法不在应用白名单中。")
        relative = Path("coach") / "skills" / method / "SKILL.md"
        path = (root / relative).resolve()
        if not path.is_relative_to(root / "coach" / "skills") or path != root / relative:
            raise ValueError("面试方法路径越界；未读取外部资源。")
        raw = path.read_bytes()
        content = raw.decode("utf-8")
        if f"name: {method}\n" not in content.replace("\r\n", "\n") or "版本：1" not in content:
            raise ValueError("面试方法标识或版本不匹配。")
        loaded.append({**selection, "version": 1, "path": relative.as_posix(),
                       "sha256": hashlib.sha256(raw).hexdigest(), "content": content})
    return loaded
