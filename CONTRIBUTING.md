# 参与贡献

欢迎提交小而可验证的基础设施、中文文档、跨平台修复、原创课程和结构化面试改进。

## 开始前

1. 阅读 [AGENTS.md](AGENTS.md) 与相关 Authoring 文档；
2. 搜索现有 Issue，避免重复；
3. 一次 PR 只解决一个边界清楚的问题；
4. 不读取或提交任何真实 `workspace/profiles/` 内容；
5. 不创建空课程目录或未来抽象。

## 固定题 PR

一个 `ready / stable` Coding Problem 至少包含：Catalog 节点、原创 `task.md`、无答案 starter、至少五个独立公开测试、H1 / H2 / H3、四个口述问题、前置与三维难度、Runner / Oracle、variant axes、invariants、common bugs、D+2 / D+7 与来源说明。

题目目录默认只有：

```text
task.md
starter.py
test_public.py
hints.md
```

不得提交 `solution.py`，也不得在测试名、错误文本或提示中泄露完整实现。`planned` 节点只写精简 Catalog 元数据，不创建空目录。

非代码面试 Item 使用 `task.md`、`response_template.md`、`rubric.yaml`、`hints.md`；Rubric 必须有权重、评分锚点、fatal issues 与证据要求。

## 来源、AI 与隐私

可以基于论文公式、官方 API 和许可清晰的源码重新设计内容，不得复制第三方题面、starter、测试、提示、答案或付费内容。

AI 可以辅助草拟，但贡献者必须人工验证数学、边界、测试独立性、许可证、重复度、隐私和中文表达。AI 生成内容不能未经 Schema、Oracle / property test、人工 Review 和真实训练验证就进入公共 Catalog。

PR 不得包含真实 Profile、简历、公司 / 客户材料、API Key、日志、权重、面试 Transcript、Oracle、Private Tests、本地绝对路径或学习者完整答案。

## 桌面与平台贡献

- CLI 与 GUI 共用 ApplicationService，不在 QML 复制业务规则；
- Windows / macOS 共用同一 GUI，不复制页面；
- 密钥只进入系统 Keyring；
- No-AI 必须在 Provider / Codex 失败时继续可用；
- Artifact 必须解包检查隐私边界；
- 不把 Grader 描述为恶意代码沙箱；
- 新用户可见文本以自然中文为规范版本，术语见 [docs/terminology.md](docs/terminology.md)。

## 验证

```bash
python -m pip install -e ".[dev]"
llm-lab doctor
python -m pytest --collect-only -q
python -m pytest -q
python scripts/validate_external_courses.py
git diff --check
```

PyTorch 题安装 `.[torch,dev]`。桌面改动安装 `.[desktop,ai,dev]` 并运行离屏 Smoke。PR 必须说明实际运行与未运行的检查，不得用 skip / xfail 隐藏回归。

详细规则见[固定课程编写指南](docs/curriculum-authoring.md)、[岗位画像](docs/role-profiles.md)和[安全政策](SECURITY.md)。
