"""Strict decoding for provider-authored non-coding interview prompts."""

from __future__ import annotations

import json
from typing import Any, Mapping

from ..roles import InterviewBlueprint


class InterviewPlannerError(RuntimeError):
    """Raised when a provider response cannot become a frozen interview plan."""


def _json_object(text: str) -> Mapping[str, Any]:
    value = text.strip()
    if value.startswith("```"):
        lines = value.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            value = "\n".join(lines[1:-1]).strip()
            if value.lower().startswith("json\n"):
                value = value[5:].lstrip()
    try:
        loaded = json.loads(value)
    except (TypeError, json.JSONDecodeError) as error:
        raise InterviewPlannerError("AI 返回的面试计划不是有效 JSON，请重试") from error
    if not isinstance(loaded, Mapping) or set(loaded) != {"questions"}:
        raise InterviewPlannerError("AI 面试计划必须只包含 questions")
    return loaded


def decode_dynamic_question(
    text: str,
    allowed_kinds: set[str] | frozenset[str],
) -> dict[str, str]:
    """Decode one current-turn question; never accepts a future question list."""

    value = text.strip()
    if value.startswith("```"):
        lines = value.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            value = "\n".join(lines[1:-1]).strip()
            if value.lower().startswith("json\n"):
                value = value[5:].lstrip()
    try:
        loaded = json.loads(value)
    except (TypeError, json.JSONDecodeError) as error:
        raise InterviewPlannerError("AI 返回的当前问题不是有效 JSON，请重试") from error
    if not isinstance(loaded, Mapping) or set(loaded) != {"kind", "title", "prompt"}:
        raise InterviewPlannerError("当前问题必须只包含 kind、title 和 prompt")
    kind = loaded["kind"]
    title = loaded["title"]
    prompt = loaded["prompt"]
    if not isinstance(kind, str) or kind not in set(allowed_kinds):
        raise InterviewPlannerError("AI 返回了当前岗位不允许的问题类型")
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
        raise InterviewPlannerError("当前问题标题长度必须为 1 到 120 个字符")
    if not isinstance(prompt, str) or not 10 <= len(prompt.strip()) <= 5000:
        raise InterviewPlannerError("当前问题正文长度必须为 10 到 5000 个字符")
    return {"kind": kind, "title": title.strip(), "prompt": prompt.strip()}


def decode_personalized_questions(
    text: str,
    blueprint: InterviewBlueprint,
) -> tuple[dict[str, Any], ...]:
    """Validate one provider response against the public blueprint.

    The provider controls only title and prompt. Kind, skills, timebox,
    rubric and coding selection remain local deterministic facts.
    """

    loaded = _json_object(text)
    raw_questions = loaded["questions"]
    if not isinstance(raw_questions, list):
        raise InterviewPlannerError("AI 面试计划的 questions 必须是数组")
    expected: list[tuple[int, str, int]] = []
    for round_index, round_value in enumerate(blueprint.rounds):
        if round_value.type == "coding":
            continue
        for item_index in range(round_value.item_count):
            expected.append((round_index, round_value.type, item_index))
    if len(raw_questions) != len(expected):
        raise InterviewPlannerError(
            f"AI 面试计划需要 {len(expected)} 个非代码问题，实际返回 {len(raw_questions)} 个"
        )
    decoded: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    per_round: dict[int, int] = {}
    expected_kinds = {
        index: round_value.type
        for index, round_value in enumerate(blueprint.rounds)
        if round_value.type != "coding"
    }
    expected_counts = {
        index: round_value.item_count
        for index, round_value in enumerate(blueprint.rounds)
        if round_value.type != "coding"
    }
    for raw in raw_questions:
        if not isinstance(raw, Mapping) or set(raw) != {
            "round_index",
            "kind",
            "title",
            "prompt",
        }:
            raise InterviewPlannerError(
                "每个 AI 问题必须只包含 round_index、kind、title 和 prompt"
            )
        round_index = raw["round_index"]
        kind = raw["kind"]
        title = raw["title"]
        prompt = raw["prompt"]
        if type(round_index) is not int or round_index not in expected_kinds:
            raise InterviewPlannerError("AI 问题引用了无效或代码类 round_index")
        if kind != expected_kinds[round_index]:
            raise InterviewPlannerError("AI 问题 kind 与冻结蓝图不一致")
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
            raise InterviewPlannerError("AI 问题标题必须包含 1 到 120 个字符")
        if not isinstance(prompt, str) or not 10 <= len(prompt.strip()) <= 5000:
            raise InterviewPlannerError("AI 主问题必须包含 10 到 5000 个字符")
        item_index = per_round.get(round_index, 0)
        if item_index >= expected_counts[round_index]:
            raise InterviewPlannerError("AI 返回了超过蓝图数量的问题")
        identity = (round_index, item_index)
        if identity in seen:
            raise InterviewPlannerError("AI 面试计划包含重复问题位置")
        seen.add(identity)
        per_round[round_index] = item_index + 1
        decoded.append(
            {
                "round_index": round_index,
                "item_index": item_index,
                "kind": kind,
                "title": title.strip(),
                "prompt": prompt.strip(),
            }
        )
    if any(per_round.get(index, 0) != count for index, count in expected_counts.items()):
        raise InterviewPlannerError("AI 面试计划没有覆盖全部非代码轮次")
    return tuple(sorted(decoded, key=lambda item: (item["round_index"], item["item_index"])))
