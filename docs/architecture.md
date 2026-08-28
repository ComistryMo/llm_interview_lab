# 架构边界

LLM Interview Lab 是 local-first、clone-first 的确定性训练核心。一个学习档案有求职材料、刷题训练和模拟面试三个入口，共享固定公共模型与隐私边界。

```text
curriculum/catalog + skills + roles + interviews
                     ↓
        planner / grader / interview engine
                     ↓
       workspace events and local artifacts
                     ↓
       ApplicationService → CLI / Qt GUI / AI
```

## 唯一事实源

- 固定课程：`curriculum/catalog/*.yaml`；
- 个人 Practice 历史：当前 Profile 的 `events.jsonl`；
- Skills / Roles / Blueprints：各自公共 YAML；
- 当前任务、错误、复测、掌握率和路线覆盖率均由 reducer 计算。

## 依赖方向

- curriculum 不依赖个人 Workspace；
- Workspace 只引用公共 ID，不复制定义；
- Planner / Grader 不调用模型决定测试或 mastery；
- AI 可以读取获准的课程与个人状态，但不能修改固定 DAG；
- CLI 与 GUI 共用 `ApplicationService`，GUI 不解析 CLI 输出；
- 打包桌面只替换数据根目录解析，不复制业务逻辑。

## 桌面双模式

- 源码模式：仓库内 `workspace/`；
- 打包模式：Qt `QStandardPaths.AppDataLocation`；
- macOS 不写 `.app/Contents`，Windows 不写 EXE 旁目录；
- API Key 使用系统 Keyring；
- Provider 与 Codex 延迟加载，不阻塞首窗口和 No-AI。

## 明确不做

当前 Alpha 不引入数据库、Web UI、本地 HTTP 服务、账号、云同步、多 Agent Runtime、插件市场或在线排行榜。本地 Grader 不是恶意代码沙箱。
