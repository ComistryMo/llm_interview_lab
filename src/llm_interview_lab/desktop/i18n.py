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
    "status.codex_connecting": "Codex 连接中……",
    "status.codex_switching": "Codex 工作流切换中……",
    "error.generic": "操作未完成。请检查输入后重试；本地训练仍可继续。",
    "error.provider": "AI 服务当前不可用。请检查网络、模型与密钥；你仍可继续本地训练和手动模拟面试。",
    "error.keyring": "系统密钥环不可用，未保存 API Key。你仍可使用无需 AI 的本地模式。",
    "error.codex_missing": "未检测到 Codex。请安装 Codex，或在设置中选择可执行文件；本地训练不受影响。",
    "error.codex_login": "Codex 尚未登录。请先完成登录；本地训练不受影响。",
    "profile.not_found": "没有找到上次使用的学习档案。请从设置选择现有档案，或创建一个新档案。",
    "profile.corrupted": "学习档案文件无法读取。请先备份数据目录，再修复或移除损坏文件。",
    "profile.switch_unsaved": "当前题目有未保存修改。请先保存，或明确放弃修改后再切换档案。",
    "profile.switch_busy": "当前操作尚未结束，请等待完成后再切换学习档案。",
    "profile.not_ready": "这个学习档案当前不可用，请从设置选择其他档案。",
    "codex.checking": "正在查找 Codex（PATH 和常见安装位置）……",
    "codex.found": "已发现 Codex：",
    "codex.missing": "未发现 Codex。你仍可使用 No-AI 本地训练；如需 AI 面试，请安装并登录 Codex，或点击“选择 Codex”指定可执行文件。也可以选择普通 LLM / Ollama。",
}


# English is intentionally a small, opt-in vocabulary.  Chinese remains the
# canonical default; keeping the map here avoids introducing a translation
# framework while allowing the setting to persist across launches.
EN_TEXT: dict[str, str] = {
    "nav.home": "Home",
    "nav.career": "Career materials",
    "nav.learn": "Practice",
    "nav.interview": "Mock interview",
    "nav.coach": "AI Coach",
    "nav.progress": "Progress",
    "nav.connections": "AI connections",
    "nav.settings": "Settings",
    "page.exercise": "Exercise workspace",
    "status.ai_offline": "AI offline · Local features available",
    "status.ai_connected": "AI connected",
    "status.codex_connected": "Codex connected",
    "status.codex_ready": "Codex ready",
    "status.codex_connecting": "Connecting to Codex…",
    "status.codex_switching": "Switching Codex workflow…",
    "error.generic": "The operation could not be completed. Check the input and try again; local practice remains available.",
    "error.provider": "The AI service is unavailable. Check the network, model, and key; local practice and manual interviews remain available.",
    "error.keyring": "The system keyring is unavailable, so the API key was not saved. You can continue in No-AI mode.",
    "error.codex_missing": "Codex was not found. Install it or choose its executable in Settings; local practice is unaffected.",
    "error.codex_login": "Codex is not signed in. Complete sign-in first; local practice is unaffected.",
    "profile.not_found": "The last-used learning profile was not found. Choose an existing profile in Settings or create a new one.",
    "profile.corrupted": "The learning profile cannot be read. Back up the data directory, then repair or remove the damaged file.",
    "profile.switch_unsaved": "The current exercise has unsaved changes. Save them, or explicitly discard them before switching profiles.",
    "profile.switch_busy": "The current operation is still running. Wait for it to finish before switching profiles.",
    "profile.not_ready": "This learning profile is not available. Choose another profile in Settings.",
    "codex.checking": "Looking for Codex (PATH and common locations)…",
    "codex.found": "Codex found: ",
    "codex.missing": "Codex was not found. No-AI local practice is still available; install and sign in, or choose the Codex executable in Settings. You can also use an LLM / Ollama provider for AI interviews.",
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


ONBOARDING_ERRORS: dict[str, str] = {
    "PROFILE_ID_INVALID": "档案标识需以小写字母开头，并且只能包含小写字母、数字或连字符。",
    "ROLE_REQUIRED": "请选择一个目标岗位后继续。",
    "ROLE_NOT_FOUND": "所选岗位已不可用，请返回岗位页重新选择。",
    "SENIORITY_UNSUPPORTED": "当前岗位不支持所选求职阶段，请重新选择。",
    "ASSESSMENT_INVALID": "能力自评数据无效，请返回上一步重新填写或选择跳过。",
    "AI_MODE_INVALID": "AI 连接选项无效，请重新选择；你也可以使用无需 AI 的本地模式。",
    "WORKSPACE_NOT_WRITABLE": "无法写入本地学习目录，请检查目录权限后重试。",
    "PROFILE_CORRUPTED": "现有学习档案无法读取，请先从设置打开数据目录并检查该档案。",
    "PUBLIC_ASSETS_MISSING": "应用缺少公共课程资源，请重新解压或重新下载桌面应用。",
    "ONBOARDING_UNEXPECTED": "创建学习档案失败。详细原因已写入本地日志。",
}

EN_ONBOARDING_ERRORS: dict[str, str] = {
    "PROFILE_ID_INVALID": "The profile ID must start with a lowercase letter and contain only lowercase letters, digits, or hyphens.",
    "ROLE_REQUIRED": "Choose a target role before continuing.",
    "ROLE_NOT_FOUND": "That role is no longer available. Return to the role step and choose another one.",
    "SENIORITY_UNSUPPORTED": "This role does not support the selected career stage. Choose another stage.",
    "ASSESSMENT_INVALID": "The self-assessment is invalid. Go back and correct it, or skip the assessment.",
    "AI_MODE_INVALID": "The AI connection choice is invalid. Choose it again, or continue in No-AI mode.",
    "WORKSPACE_NOT_WRITABLE": "The local learning directory cannot be written. Check its permissions and try again.",
    "PROFILE_CORRUPTED": "The existing learning profile cannot be read. Open its data directory in Settings and inspect it first.",
    "PUBLIC_ASSETS_MISSING": "Public curriculum assets are missing. Re-extract or download the desktop application again.",
    "ONBOARDING_UNEXPECTED": "The learning profile could not be created. Details were written to the local log.",
}


def text(key: str, fallback: str = "", language: str = "zh-CN") -> str:
    """Resolve one small UI string without changing the public call shape."""

    table = EN_TEXT if language in {"en", "en-US", "en-GB"} else TEXT
    return table.get(key, fallback or TEXT.get(key, key))


def onboarding_error_text(code: str, language: str = "zh-CN") -> str:
    table = EN_ONBOARDING_ERRORS if language in {"en", "en-US", "en-GB"} else ONBOARDING_ERRORS
    fallback = "ONBOARDING_UNEXPECTED"
    return table.get(code, table[fallback])


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
    raw = str(error).strip()
    message = raw.lower()
    # Audio and transcription errors are already sanitized by the local
    # recorder / transcriber boundary.  Preserve their actionable next step
    # instead of collapsing them into the generic provider hint.
    if any(token in raw for token in ("录音", "转录", "音频")):
        return raw[:400] or TEXT["error.generic"]
    if "connection id must" in message:
        return "连接 ID 只能使用小写字母、数字和连字符，并且要以字母开头。请展开高级设置后修改。"
    if "provider is not supported" in message:
        return "当前桌面版本不支持这个 AI 服务，请从服务下拉框中重新选择。"
    if "model and display name must" in message:
        return "模型和显示名称不能为空；请检查对应字段后重试。"
    if "endpoint must be an http" in message:
        return "地址必须是不含账号密码的 HTTP(S) 地址，请检查 Endpoint。"
    if "custom endpoints are available" in message:
        return "自定义地址只适用于 OpenAI-compatible 或 Ollama，请更换服务类型或清空地址。"
    if "remote providers require" in message:
        return "远程 AI 服务需要 API Key；请填写新 Key，或确认系统密钥环可用。"
    # Keep the next action visible for the practice flow. These messages
    # must not collapse into the generic offline-training hint.
    if "当前答案已修改" in message or "current answer has changed" in message:
        return "当前答案已修改，请先保存并重新运行测试后再提交。"
    if "attempt changed" in message or "题目或作答轮次已变化" in message:
        return "当前题目或作答轮次已变化，请重新打开这道题后再运行测试。"
    if "problem has not been started" in message or "没有可用的作答目录" in message:
        return "这道题还没有开始作答，请先点击“开始”后再运行测试。"
    if "submission could not be saved" in message:
        return "答案保存失败，请检查本地学习档案权限后重试。"
    if "pdf and docx" in message or (
        "opaque" in message and "ai_access" in message
    ):
        return "当前版本只保存 PDF / DOCX 原文件，不读取其中内容；如需授权 AI，请选择 UTF-8 文本材料。"
    if "缺少满足岗位、难度与技能要求" in message or "no eligible fixed item" in message:
        return "当前岗位、阶段和难度没有完整的固定面试题组合，请更换难度或岗位后重试。"
    if "retention is not due until" in message:
        return "间隔复测尚未到期，请按页面显示的到期时间再开始。"
    if "retention assets unavailable" in message:
        return "这道题尚无经过验证的复测资产，当前不能进入间隔复测。"
    if "d+2 retention must pass" in message:
        return "请先通过 D+2 间隔复测，再开始 D+7。"
    if "keyring" in message or "credential" in message:
        return TEXT["error.keyring"]
    if "codex" in message and ("not found" in message or "executable" in message):
        return TEXT["error.codex_missing"]
    if "codex" in message and ("sign" in message or "account" in message):
        return TEXT["error.codex_login"]
    if any(token in message for token in ("401", "429", "500", "provider", "connection", "timeout")):
        return TEXT["error.provider"]
    return TEXT["error.generic"]
