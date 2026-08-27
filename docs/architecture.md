# Architecture

LEAN-V2 是本地、clone-first 的确定性核心：

```text
curriculum/catalog/*.yaml
        ↓ schema + DAG
planner / lifecycle / grader
        ↓ append-only evidence
workspace/profiles/<id>/events.jsonl
        ↓ reducer
CLI / one AI coach
```

`catalog.py` 读取 Problem、Track、Quest、Capstone；`dag.py` 只处理依赖；`workspace.py` 管理 ignored Profile 和新 attempt；`submissions.py` 是唯一代码 loader；`grader.py` 用独立 pytest 子进程、超时和输出截断产生证据；`events.py` 负责 append/reduce；`lifecycle.py` 验证 Review/retention/mastery；`cli.py` 只协调这些规则。

固定课程不依赖 Workspace。Workspace 只引用 Problem ID，不复制课程定义。AI 可读取二者进行教学，但不能修改固定图谱或直接判定 mastery。未来 UI 若出现，也必须调用相同应用层。

唯一事实源：固定课程是 Catalog shards；每个 Profile 的历史是一个 `events.jsonl`。CLI 页面、进度、到期复测和 Track 覆盖率都是生成视图。pytest 是 Runner；fixture、闭式公式、框架参考、brute force、交叉实现或 property 是 Oracle。

项目不包含 Web、数据库、账户、网络服务、多 Agent Runtime 或恶意代码沙箱。External course pack 是冻结的兼容元数据，不进入默认 DAG。
