"""Small Chinese-first desktop vocabulary without a translation framework."""

from __future__ import annotations

from typing import Any


TEXT: dict[str, str] = {
    "nav.home": "首页",
    "nav.career": "求职材料",
    "nav.learn": "刷题训练",
    "nav.interview": "模拟面试",
    "nav.coach": "AI 辅助（可选）",
    "nav.progress": "学习进度",
    "nav.connections": "AI 连接",
    "nav.settings": "设置",
    "page.exercise": "答题工作区",
    "status.ai_offline": "AI 未连接 · 本地功能可用",
    "status.ai_connected": "AI 已连接",
    "status.codex_connected": "Codex 已连接",
    "status.codex_ready": "Codex 已发现（尚未连接）",
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
    "status.codex_ready": "Codex found (not connected)",
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


# Problem assets keep their stable English ids and source contracts.  The
# desktop surface uses this small vocabulary to make the first reading pass
# Chinese-first without changing Catalog fingerprints or public task files.
PROBLEM_TITLE_ZH: dict[str, str] = {
    "FND-001": "统计错误预测样本",
    "FND-002": "校验样本契约",
    "FND-003": "筛选困难样本",
    "FND-004": "汇总困难样本",
    "FND-005": "流式读取 JSONL",
    "FND-006": "实现小批量迭代器",
    "CAP-FND-001": "困难样本数据流水线",
    "TNS-002": "重排、置换与连续内存",
    "TNS-003": "张量广播",
    "TNS-006": "张量 Gather",
    "TNS-010": "序列 Mask",
    "TNS-011": "取最后一个有效 Token",
    "TNS-013": "Autograd、Detach 与 No-Grad",
    "LOSS-007": "稳定 Softmax",
    "LOSS-008": "LogSumExp",
    "LOSS-013": "带 Logits 的 BCE",
    "LOSS-014": "交叉熵损失",
    "CAP-LOSS-001": "带 Mask 的序列分类损失",
    "NNL-001": "Linear 层",
    "NNL-002": "Embedding 层",
    "NNL-008": "RMSNorm",
    "OPT-001": "SGD 优化器",
    "OPT-002": "Momentum 优化器",
    "OPT-004": "Adam 优化器",
    "OPT-005": "AdamW 优化器",
    "CAP-TRN-001": "小型序列分类训练器",
    "ATT-002": "缩放点积注意力",
    "ATT-004": "多头注意力",
    "ATT-005": "多查询注意力",
    "ATT-006": "分组查询注意力",
    "ATT-007": "旋转位置编码",
    "ATT-009": "KV Cache",
    "PT-001": "SFT 标签 Mask",
    "PT-002": "Token / 序列 Logprob",
    "PT-005": "偏好对契约校验",
    "PT-006": "DPO 损失",
    "PT-014": "GRPO 分组优势",
    "PT-015": "GRPO 损失",
    "PT-016": "无效 Completion 处理",
    "AGT-001": "工具 Schema",
    "AGT-002": "工具注册表",
    "AGT-006": "工具调用 Agent Loop",
    "AGT-009": "Trajectory JSONL",
    "VLM-007": "多模态标签 Mask",
}


PROBLEM_BRIEF_ZH: dict[str, str] = {
    "FND-001": "实现一个纯函数，统计预测与标签不一致的样本数量。请处理空输入、长度不一致和输入不变性，并返回稳定的整数结果。\n\n完整接口与边界契约仍以当前题目文件和公开测试为准。",
    "FND-002": "检查每条训练样本是否满足字段、类型和标签范围契约；遇到无效样本时给出可定位的结果，不要修改原始数据。",
    "FND-003": "根据预测错误、置信度或损失等信号筛选困难样本。保持样本顺序和输入不变，并明确空结果的行为。",
    "FND-004": "对困难样本做确定性统计，输出数量、错误分布和可用于复盘的摘要。注意空集合和缺失字段。",
    "FND-005": "逐行读取 JSONL 数据并转换为样本记录；跳过或报告坏行的策略必须稳定，不能一次性把整个文件加载进内存。",
    "FND-006": "把样本按 batch_size 迭代输出，正确处理最后一个不完整批次、空输入和重复迭代。迭代过程不得改写原始样本。",
    "TNS-002": "实现 reshape、permute 与 contiguous 的组合操作，保持元素语义和目标 Shape；特别注意非连续输入和内存布局。",
    "TNS-003": "实现符合 PyTorch 规则的广播计算，处理标量、不同维度和不可广播输入，并保持 dtype 与输入不变。",
    "TNS-006": "沿指定维度 gather 张量中的元素，校验索引范围并保持结果 Shape；不要用循环掩盖维度错误。",
    "TNS-010": "根据序列长度或有效位置生成 attention mask，支持批次内不同长度并保持 CPU、dtype 和输入不变性。",
    "TNS-011": "利用 mask 找到每条序列最后一个有效 Token。全 Padding 样本必须明确报错，不能悄悄取到 Padding。",
    "TNS-013": "解释并实现需要梯度、detach 和 no_grad 的边界；返回值应保持正确的 requires_grad 与反向传播关系。",
    "LOSS-007": "实现数值稳定的 Softmax，避免极端 logits 溢出，并保持维度、dtype 与梯度行为符合 PyTorch 语义。",
    "LOSS-008": "实现稳定的 LogSumExp，使用平移技巧处理极端值，并支持指定维度、保留维度和梯度回传。",
    "LOSS-014": "实现稳定交叉熵：从 logits 计算每个样本的损失，处理 class 维度、reduction、极端值和梯度。",
    "NNL-001": "实现带权重和偏置的 Linear 前向计算，支持批量输入、dtype 和梯度回传，不修改参数或输入。",
    "NNL-002": "实现 Embedding 查表，处理索引 dtype、边界和重复索引，并验证梯度只回传到被使用的行。",
    "NNL-008": "实现 RMSNorm 的归一化、缩放和数值稳定项，支持不同 Shape、dtype 与反向传播。",
    "OPT-001": "实现多步 SGD 更新，正确处理学习率、None gradient、参数组和 state_dict 语义。",
    "OPT-002": "在 SGD 基础上加入动量状态，验证多步更新、零梯度和状态演化。",
    "OPT-004": "实现带一阶/二阶矩和偏置修正的 Adam，确保多参数、多步更新与官方参考对齐。",
    "OPT-005": "实现 AdamW 的解耦 weight decay，处理参数组、None gradient、状态恢复和零梯度行为。",
    "ATT-002": "实现缩放点积注意力，计算 Q/K/V 的 Shape、缩放和权重归一化；支持 mask、极端值和梯度。",
    "ATT-004": "实现多头注意力的头拆分、转置、合并和投影，验证非连续输入、mask 与输出 Shape。",
    "ATT-005": "实现共享 K/V 的多查询注意力，明确 Query 与 KV 头数关系，并检查 Cache 友好的布局。",
    "ATT-006": "实现分组查询注意力，在 Query 头与 KV 头之间进行分组映射，保持数值和 Shape 正确。",
    "ATT-007": "实现旋转位置编码，处理偶数维度、位置索引和 cos/sin 广播，保证输入不被修改。",
    "ATT-009": "实现 KV Cache 的追加、读取和长度管理，处理批次、位置和容量边界。",
    "PT-001": "构造 SFT 标签 Mask，使提示部分不参与损失而答案部分保留监督信号；处理 Padding 和边界。",
    "PT-002": "从 logits 中提取 Token 与序列级 Logprob，处理 shift、Mask 和长度差异，不把 Padding 计入分数。",
    "PT-005": "校验 chosen/rejected 偏好对的字段、长度和有效性，输出确定性错误信息并保持原始数据不变。",
    "PT-006": "实现 DPO 损失，分离 current/reference logprob，处理 beta、Mask、长度差异和数值稳定。",
    "PT-014": "按组计算 GRPO 优势，处理组内均值、方差为零和无效 completion。",
    "PT-015": "实现 GRPO 损失的比率、裁剪和优势加权，明确 sign、Mask 与 reduction 语义。",
    "PT-016": "识别并稳定处理无效 completion，避免把错误轨迹当作正向训练信号。",
    "AGT-001": "定义工具名称、参数 Schema 和返回契约，拒绝未知字段或无效参数，并给出可修复错误。",
    "AGT-002": "实现工具注册和查找，处理重复名称、未知工具和不可调用工具。",
    "AGT-006": "实现包含 parser、validation、executor 的最小工具调用循环，处理异常、超时和最大步数。",
    "AGT-009": "按 JSONL 记录完整 Agent 轨迹，保证事件顺序、工具输入输出和失败原因可复盘。",
    "VLM-007": "为图像与文本混合序列构造标签 Mask，正确区分视觉占位符、Padding 和监督 Token。",
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


def problem_title(problem_id: str, fallback: str = "", language: str = "zh-CN") -> str:
    """Return the user-facing title while keeping the catalog title stable."""

    if language in {"en", "en-US", "en-GB"}:
        return fallback or problem_id
    return PROBLEM_TITLE_ZH.get(str(problem_id), fallback or problem_id)


def problem_brief(problem_id: str, fallback: str = "", language: str = "zh-CN") -> str:
    """Return a concise Chinese first-read contract; English remains opt-in."""

    if language in {"en", "en-US", "en-GB"}:
        return fallback
    return PROBLEM_BRIEF_ZH.get(
        str(problem_id),
        f"本题训练“{problem_title(problem_id, fallback, language)}”相关能力。请结合接口、约束和公开测试完成实现。",
    )


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
    if "unknown variant" in message and "sandbox" in message:
        return "Codex 已发现，但当前版本协议不兼容。请更新 Codex CLI 后重试；本地训练和 No-AI 不受影响。"
    if "codex" in message and ("could not be started" in message or "winerror 193" in message):
        return "Codex 已找到，但 Windows 无法直接启动该命令包装器。请在设置中重新测试；若仍失败，请选择 codex.exe 或更新 Codex CLI。"
    if "codex" in message and ("sign" in message or "account" in message):
        return TEXT["error.codex_login"]
    if any(token in message for token in ("401", "429", "500", "provider", "connection", "timeout")):
        return TEXT["error.provider"]
    return TEXT["error.generic"]
