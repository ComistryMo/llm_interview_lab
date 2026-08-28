# 本地个人工作区

`workspace/` 是源码模式下学习档案（Profile）的仓库内数据根目录。只需克隆一次仓库，然后创建一个本地档案：

```bash
llm-lab init --profile default
```

Git 只跟踪 Schema、默认模板、完全虚构的 Demo 和 `profiles/.gitkeep`。`workspace/profiles/` 下的真实档案默认全部忽略，请勿使用 `git add -f` 强制提交。

每个档案包含 `profile.yaml`、只追加的 `events.jsonl`，以及 `materials/`、`submissions/`、`generated/`、`private_tests/`、`reviews/`、`interviews/`、`cache/` 和 `exports/`。结构化求职意向位于 `profile.yaml`；已登记材料的元数据和 SHA-256 位于 `materials/manifest.json`。

事件文件是学习历史的唯一事实源。Reducer 按文件物理行顺序处理事件，时间戳只作为证据，不参与重新排序。错题摘要由事件动态计算，不再维护第二份状态文件。当前经过验证的间隔复测是 D+2 和 D+7；没有 D+5 Gate。第一版同一档案只支持一个写入进程。

只有显式执行 `llm-lab material add` 后，材料才会被复制进个人工作区。AI 读取还要求：材料可安全转成文本、明确的材料 ID、逐场同意和匹配的 SHA-256。脱敏后的真实面试题使用 `interview_question` 类型，始终属于私人材料，不会自动进入公共 Catalog。

在源码中的自带 AI（Bring Your Own AI）流程里，使用 `llm-lab context`，并把其中的 `read_allowlist` 视为完整读取边界。桌面端远程 AI 只发送“上下文预览”中明确勾选的内容；项目不会扫描其他档案，AI 输出也不能授予“已掌握”。

`demo/` 档案为测试专门虚构，并非真实学习记录脱敏而来。CI 不得读取 `profiles/`。

打包桌面应用使用系统应用数据目录，而不是把资料写入 `.exe` 或 `.app`。详见[个人工作区](../docs/workspace.md)、[Windows 指南](../docs/windows.md)和 [macOS 指南](../docs/macos.md)。
