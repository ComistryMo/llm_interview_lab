"""Small Chinese-first desktop vocabulary without a translation framework."""

from __future__ import annotations

from typing import Any


TEXT: dict[str, str] = {
    "nav.home": "首页",
    "nav.career": "求职材料",
    "nav.learn": "刷题训练",
    "nav.interview": "模拟面试",
    "nav.coach": "AI 教练",
    "nav.progress": "学习进度",
    "nav.connections": "AI 连接",
    "nav.settings": "设置",
    "page.exercise": "答题工作区",
    "status.ai_offline": "AI 未连接 · 本地功能可用",
    "status.ai_connected": "AI 已连接",
    "status.codex_connected": "Codex 已连接",
    "status.codex_ready": "Codex 就绪",
    "error.generic": "操作未完成。请检查输入后重试；本地训练仍可继续。",
    "error.provider": "AI 服务当前不可用。请检查网络、模型与密钥；你仍可继续本地训练和手动模拟面试。",
    "error.keyring": "系统密钥环不可用，未保存 API Key。你仍可使用无需 AI 的本地模式。",
    "error.codex_missing": "未检测到 Codex。请安装 Codex，或在设置中选择可执行文件；本地训练不受影响。",
    "error.codex_login": "Codex 尚未登录。请先完成登录；本地训练不受影响。",
}


ROLE_TEXT: dict[str, tuple[str, str, str]] = {
    "ai_product_manager": (
        "AI 产品经理",
        "把用户问题转化为可评测、可迭代的 AI 产品方案。",
        "产品案例、指标设计、评测、安全与跨团队协作",
    ),
    "applied_ai_engineer": (
        "AI 应用工程师",
        "构建可靠的 LLM、RAG 与 Tool Calling 应用。",
        "编码、系统设计、评测、成本与故障降级",
    ),
    "ai_agent_engineer": (
        "AI Agent 工程师",
        "设计工具调用、状态、轨迹与长任务恢复。",
        "Agent Loop、调试、轨迹评测与系统设计",
    ),
    "ai_algorithm_research_engineer": (
        "AI 算法 / 研究工程师",
        "用数学、PyTorch 与实验解释并验证模型机制。",
        "算法手撕、模型原理、实验设计与项目深挖",
    ),
    "post_training_engineer": (
        "大模型后训练工程师",
        "围绕 SFT、偏好优化、Reward 与 Rollout 建设训练能力。",
        "DPO、PPO / GRPO、训练稳定性与数据闭环",
    ),
    "ai_infra_engineer": (
        "AI Infra / ML 平台工程师",
        "建设可靠、可观测、可恢复的训练与数据平台。",
        "分布式训练、调度、Checkpoint、可观测性与成本",
    ),
    "ai_inference_systems_engineer": (
        "AI 推理 / 系统工程师",
        "优化服务时延、吞吐、显存与 Kernel 性能。",
        "KV Cache、量化、Serving、CUDA / Triton 与性能分析",
    ),
    "ai_evaluation_data_safety_engineer": (
        "AI 评测 / 数据 / 安全工程师",
        "建立可信 Benchmark、Rubric、数据质量与安全评测。",
        "评测设计、污染检测、统计分析与 Red Team",
    ),
}


def text(key: str, fallback: str = "") -> str:
    return TEXT.get(key, fallback or key)


def localize_role(card: dict[str, Any]) -> dict[str, Any]:
    localized = ROLE_TEXT.get(str(card.get("id", "")))
    if localized is None:
        return card
    title, summary, interview_content = localized
    return {
        **card,
        "title": title,
        "summary": summary,
        "interview_content": interview_content,
    }


def friendly_error(error: BaseException | str) -> str:
    message = str(error).lower()
    if "keyring" in message or "credential" in message:
        return TEXT["error.keyring"]
    if "codex" in message and ("not found" in message or "executable" in message):
        return TEXT["error.codex_missing"]
    if "codex" in message and ("sign" in message or "account" in message):
        return TEXT["error.codex_login"]
    if any(token in message for token in ("401", "429", "500", "provider", "connection", "timeout")):
        return TEXT["error.provider"]
    return TEXT["error.generic"]
