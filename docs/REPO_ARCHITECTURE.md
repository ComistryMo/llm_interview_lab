# 仓库架构

## 两层使用模型

```text
public upstream
├── 课程、协议、模板、测试基础设施、虚构示例
├── 一个明确标注、脱敏但与维护者公共账号关联的流程 fixture
└── 除该 fixture 外不接收任何人的真实训练材料

private learner repository
├── 个人档案、答案、review、progress、项目 claim
└── v0.1 只挑选公共基础设施补丁，不直接 merge fixture 路径
```

当前 v0.1 alpha 的 fixture 用于验证状态和审查流程；它不是 starter。`create_private_workspace.py` 会从公共 HEAD 生成无答案私人 workspace，并在替换 fixture 后丢弃公共 Git 历史、初始化全新 `main`。公共 starter 尚未物理拆成独立发行树，因此暂不启用 GitHub Template。

生成器只保存 upstream 的 fetch URL，禁用 upstream push，且不建立共同历史。由于 v0.1 的 `src/state/reviews/progress` 仍与公共 fixture 共用路径，私人仓库不要直接 merge 或 pull upstream；只在审查 diff 后挑选与个人路径无关的基础设施提交。物理分离和安全同步工具属于 v0.2。

## 目录边界

| 路径 | 内容 | 主要维护者 | 是否含答案 |
|---|---|---|---|
| `src/` | 学员实现区 | 学习者 | 可以，默认 AI 只读 |
| `tests/infrastructure/` | 仓库工具契约 | 维护者 | 否 |
| `tests/regression/` | 已验收公共回归 | 维护者 | 不泄露完整答案 |
| `tests/stage00/` | 当前/锁定训练测试 | 教练与维护者 | 不泄露完整答案 |
| `curriculum/` | Task Card 与依赖 | 课程维护者 | 否 |
| `curriculum/catalog.json` | 公共任务发现、runtime、测试节点和路由元数据 | 课程维护者 | 否 |
| `curriculum/NAVIGATION.md` | catalog 的确定性生成视图 | 自动生成 | 否 |
| `curriculum/external/` | 第三方课程固定版本的兼容元数据、导航与原创教练 Task Card；不含上游材料 | 课程维护者/自动生成 | 否 |
| `hints/` | 按 Task/等级隔离的正式提示；v0.1 仅有规则 | 课程维护者 | 不放 H5 |
| `state/` | 当前快照、ledger、错误 | 私人副本中的学习者/教练 | 否 |
| `reviews/` | 有证据的正式审查 | 教练 | 可引用少量 diff，不放答案全文 |
| `progress/` | 周考/月考与测试摘要 | 学习者/教练 | 否 |
| `notes/` | 公开安全的原理/claim | 学习者 | 只放抽象事实 |
| `templates/` | 私人副本初始化模板 | 维护者 | 否 |
| `prompts/` | 可复制短指令 | 维护者 | 否 |
| `scripts/` | 环境、状态、导出工具 | 维护者 | 否 |
| `references/` | 固定 revision 的外部来源登记，不镜像内容 | 维护者 | 否 |
| `plans/` | 重大跨目录 ExecPlan | 维护者 | 否 |
| `.github/` | CI 与贡献入口 | 维护者 | 否 |

没有真实内容前不创建 `benchmarks/`、`examples/` 或几十个任务空目录。

## 权威事实

- ledger 是状态历史唯一事实源；
- `CURRENT_TASK.md` 是当前人类快照；
- `PROGRESS.md` 与 handoff 是派生视图；
- `MISTAKE_LOG.md` 保存定性复盘，不决定状态；
- 任务要求以对应 `curriculum/` 文件为准；
- 跨任务发现、依赖边和运行策略以 `curriculum/catalog.json` 为准；
- `curriculum/NAVIGATION.md` 是生成视图，不是第二份手工事实；
- 外部设计影响与许可证证据以 `references/registry.json` 为准；
- 外部课程的 problem/test/runtime 覆盖以对应 manifest 为准；`curriculum/external/NAVIGATION.md` 只是生成视图；
- AI 行为以 `COACHING_PROTOCOL.md` 为准。

校验器必须发现而不是掩盖这些文件的漂移。

## 依赖与测试

基础设施只有 Python 3.10+ 与 pytest。Torch 是阶段依赖，不进入最小安装。默认 pytest 不收集当前或锁定训练题；显式定向命令负责训练反馈。每张 task 声明最低 runtime 与 GPU 验收策略；达到 `validated` 的 CPU 任务不能靠 CUDA 缺失整体跳过。Makefile 只是快捷方式，权威文档始终给出跨平台 Python 命令。

`.external/` 是被忽略的第三方 checkout 根目录，不是仓库内容层。通用安装器固定 commit、拒绝覆盖、禁用官方远端 push，且不执行第三方代码。安装器不写 learner ledger；学习者正式选择一个外部 problem-group Task 时，必须通过教练/状态流程把它登记为唯一 `CURRENT_TASK`，而不是并行开启第二条 Implementation Lane。详见[外部课程包](EXTERNAL_COURSE_PACKS.md)。

`scripts/run_current_task.py` 从已校验 ledger 和 catalog 动态选择原生 pytest nodes，不读取或执行 Markdown 中的 shell。若当前任务属于外部课程，它只给出当前 problem group 的人工审阅入口并返回退出码 2（表示需要人工动作，不表示仓库测试失败），不自动运行第三方命令。`scripts/select_current_task.py` 默认只预览；显式应用时只追加必要的注册事件并重建当前快照，不产生实现或掌握证据。

## 生命周期

课程新增遵循 Task Card → starter → 可见测试 → 提示 → 变式 → review。已掌握模块只有满足公开迁出 Gate 后才进入独立作品仓库；训练仓库中的一次全绿不得直接复制出去。
