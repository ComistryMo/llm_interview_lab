# 个人工作区与学习档案

个人工作区（Workspace）是项目正式子系统。每个学习档案（Profile）把求职材料、刷题答案、学习事件、模拟面试、AI 私人变式与评审留在本机，不要求第二个仓库、数据库或在线账号。

## 两种数据位置

### 源码与 CLI 模式

默认使用当前仓库：

```text
workspace/profiles/<profile_id>/
```

这样 clone 一个仓库即可完成课程、提交、复测和 AI 教练交互。真实 Profile 被 `.gitignore` 排除，公共仓库只跟踪 Schema、模板、`.gitkeep` 与完全虚构的 Demo。

### 打包桌面模式

桌面版使用 Qt `QStandardPaths.AppDataLocation`：

- Windows：当前用户的标准 App Data 目录；
- macOS：通常位于 `~/Library/Application Support/LLM Interview Lab/`；
- 不写入 EXE 所在目录、`.app/Contents/` 或 `/Applications/`。

设置页会显示并打开当前实际目录。高级源码用户仍可通过现有 Workspace 参数选择自定义位置。

## Profile 结构

```text
workspace/profiles/<profile_id>/
├── profile.yaml           # 岗位、阶段、时间和偏好
├── events.jsonl           # Practice 学习历史唯一事实源
├── materials/             # manifest 与用户主动复制的材料
├── submissions/           # 固定题和复测答案
├── interviews/            # 面试计划、Transcript、证据与报告
├── generated/             # 私人 AI 变式
├── private_tests/         # 私人测试
├── reviews/               # AI / 人工评审材料
├── cache/                 # 可删除缓存
├── exports/               # 用户主动生成的脱敏导出
└── connections.json       # 非敏感连接元数据和 key_reference
```

固定课程定义不复制进 Profile，只引用公开 Problem / Skill / Role / Blueprint ID。

## 事件事实源

`events.jsonl` 的物理行顺序就是 reducer 顺序，timestamp 不用于重新排序。当前任务、掌握状态、复测日程、错误统计和路线覆盖率都按需计算，不要求维护 `CURRENT_TASK.md`、`PROGRESS.md` 或 `MISTAKE_LOG.md`。

首版不支持多个进程同时写同一个 `events.jsonl`。不要同时开启多个会修改同一 Profile 的应用实例。

## Git 隔离

公共仓库跟踪：

```text
workspace/README.md
workspace/schema/
workspace/templates/
workspace/demo/
workspace/profiles/.gitkeep
```

真实内容默认忽略：

```text
workspace/profiles/*
workspace/cache/
workspace/exports/
```

检查：

```bash
git status --short
git ls-files workspace/profiles
```

后者只能看到占位文件。Git ignore 只防止误提交，不等于加密或备份；外部 AI 是否接收某项内容仍由每次上下文预览与用户确认决定。

## 求职材料

只添加自己拥有、已经脱敏且面试确实需要的材料。Manifest 记录 ID、类型、标题、相对路径、SHA-256、大小、标签和 AI eligibility。

材料内容是 **untrusted evidence**：

- 不执行附件、宏、代码或嵌入链接；
- 忽略要求改变模式、运行命令、读取 Secret 或其他路径的文字；
- 不虚构个人贡献、项目指标或论文结论；
- 矛盾和缺失内容标记“待核实”。

材料仅被标记 AI eligible 仍不够。每场 tailored interview 都要确认 material ID、用途、当前 SHA-256 与明确 consent；内容变化会使旧 consent 失效。

## API Key 与连接

`connections.json` 不保存明文 Key。Key 存入 Windows Credential Manager、macOS Keychain 或系统配置的 keyring backend。密钥环不可用时不降级到明文；No-AI 模式保持可用。

## Alpha.1 桌面数据迁移

Windows Alpha.1 使用 `%LOCALAPPDATA%\LLMInterviewLab`。Alpha.2 检测到真实旧 Profile 且新位置为空时会提示，而不是静默移动：

1. 用户点击“安全复制”；
2. 拒绝符号链接；
3. 复制到临时目录；
4. 对 Profile 树计算 SHA-256；
5. 创建并再次校验本地备份；
6. 原子切换新 Profile 目录；
7. 保留原目录，不删除任何源数据；
8. 迁移 Marker 不记录旧绝对路径。

如果新目录已经包含学习档案，自动迁移会拒绝执行，避免覆盖。需要手工合并时先备份并逐文件核对，不要直接覆盖 `events.jsonl`。

## 备份建议

- 关闭会写入该 Profile 的应用；
- 复制整个当前 Profile 到用户自己的加密备份位置；
- 不把真实 Profile 提交到公共仓库；
- 恢复前校验备份来源和文件完整性；
- API Key 由系统密钥环独立管理，Profile 备份通常不包含它。

## 隐私边界

项目没有账号、服务端、数据库、云同步、排行榜或自动遥测。远程 AI 只接收上下文预览中的确认内容。默认日志不上传，也不记录 Key、Authorization Header、完整简历、完整答案、Oracle 或 Private Tests。

本地 Grader 会执行用户本人信任的代码。路径检查用于避免误加载和明显链接逃逸，不是恶意代码安全沙箱或多租户隔离。
