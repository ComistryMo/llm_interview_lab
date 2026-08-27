# OSS LEAN-V2 Vertical Slice 1 ExecPlan

## 1. 目标与可观察结果

在不修改当前学习者答案、不删除旧公共 fixture、不扩展外部课程包的前提下，打通一个 clone-first、repository-local 的最小训练闭环：

```text
Catalog FND-001
→ llm-lab init / next / show / start
→ Workspace submission
→ 独立 pytest 子进程 + 统一 loader
→ llm-lab test / submit
→ events.jsonl reducer
```

完成时必须满足：

- Python 3.11 环境下 Repository Health、旧 validators 与新测试通过；
- 根 pytest 不收集课程公开测试、真实 Profile 或 learner submission；
- `workspace/profiles/*` 默认忽略，仅 `.gitkeep` 被跟踪；
- FND-001 目录只有 `task.md`、`starter.py`、`test_public.py`、`hints.md`；
- starter 通过正式 grader 失败，独立基础设施 fixture 通过正式 grader；
- 测试通过不被描述为 mastered；
- 旧维护者数据仍保留原位，安全副本只存在于 ignored Profile；
- 不合并 main、不打 tag、不发布 release、不重写历史。

## 2. 批准范围

批准标识：`LEAN-V2 VERTICAL SLICE 1`。

允许修改的现有文件仅为：

- `.gitignore`；
- `pyproject.toml`；
- `requirements.txt`；
- `.github/workflows/ci.yml`；
- `README.md`；
- `tests/infrastructure/test_repository_contract.py`；
- 本 ExecPlan。

允许新增：

- `src/llm_interview_lab/` 最小 package；
- 最小 Catalog Schema、单个 FND-001 Catalog shard 与 DAG validation；
- `workspace/` 模板、Schema、完全虚构 Demo 与 ignored profiles 边界；
- FND-001 四文件题目；
- 纵向闭环所需 infrastructure tests 与完全独立的 grader fixtures。

明确暂缓修改：

- `ROADMAP.md`；
- `CONTRIBUTING.md`；
- `curriculum/README.md`；
- `docs/GETTING_STARTED.md`；
- `docs/REPO_ARCHITECTURE.md`；
- `docs/CURRICULUM_METADATA.md`；
- `docs/STATE_MODEL.md`；
- `docs/PRIVACY_AND_SECURITY.md`；
- `AGENTS.md`、`docs/COACHING_PROTOCOL.md` 和 AI Coach Schema；
- 现有脚本、Makefile、external pack、当前答案和旧个人 fixture。

禁止新增未被 FND-001 闭环调用的未来抽象，禁止创建其他课程问题目录或批量 Planned Catalog 节点。

## 3. 批准修正逐项确认

### 3.1 Oracle 与 Runner 分离

FND-001 使用以下语义：

```yaml
assessment:
  runner:
    kind: pytest
    public_tests: test_public.py
  oracle:
    kind: fixture_expected
    description: Expected counts and contract violations are declared by public fixtures.
```

Schema 为 `oracle.kind` 预留：

- `fixture_expected`；
- `closed_form`；
- `framework_reference`；
- `brute_force`；
- `cross_implementation`；
- `property_only`。

pytest 是执行器，不是正确性 Oracle。

### 3.2 Grader 进程与 plugin

- grader 使用独立 Python 子进程运行精确 pytest 文件；
- 统一 pytest plugin 负责读取 grader 传入的 submission 路径和 symbol；
- plugin 只调用唯一 submission loader；
- 课程测试只依赖 `submission` fixture；
- 课程测试不导入 starter、不修改 `sys.path`、不硬编码 Workspace 路径、不复制 loader。

### 3.3 Infrastructure-only 正向 fixture

`tests/fixtures/grader/add_one/` 是基础设施测试资产，不是固定课程节点，也不包含 FND-001 答案。它覆盖：

- valid submission；
- missing symbol；
- syntax error；
- import error；
- runtime error；
- wrong path；
- module cache isolation；
- SHA-256。

### 3.4 安全边界

`llm-lab` 只执行本地用户本人信任的代码。路径校验用于避免误加载，不构成恶意代码安全沙箱。本切片不实现容器、权限/网络隔离、多租户执行或复杂 hardlink/reparse 防御。

必须保证：

- resolve 后路径位于当前 Profile 的 submissions 根目录；
- 不加载 starter；
- 不接受目录；
- 不接受明显 symlink；
- 只接受 `.py`；
- 唯一模块名避免缓存污染。

### 3.5 Event Schema 与 reducer

每个事件至少包含：

```json
{
  "schema_version": 1,
  "event_id": "evt-...",
  "timestamp": "2026-08-27T12:00:00+08:00",
  "profile_id": "demo-learner",
  "event_type": "public_tests_run",
  "problem_id": "FND-001",
  "attempt_id": "attempt-0001",
  "payload": {}
}
```

- 文件物理顺序是 reducer 顺序，timestamp 不参与重新排序；
- 第一版不支持多进程并发写 `events.jsonl`；
- `task_implemented` 对相同 problem、attempt、submission SHA 幂等；
- `public_tests_run.payload` 至少记录 `submission_sha256`、`exit_code`、`status`、`passed`、`failed`、`duration_ms`；
- 事件不得记录绝对路径。

### 3.6 start 幂等性

- 没有 attempt 时创建 `attempt-0001`；
- 存在未完成 attempt 时返回原目录且不覆盖；
- 已 implemented 时拒绝普通 start；
- 本切片不实现 `--new-attempt`；
- 绝不覆盖已有 `submission.py`。

### 3.7 依赖事实源

`pyproject.toml` 是依赖唯一事实源。`requirements.txt` 只保留兼容入口：

```text
-e .[dev]
```

不在 requirements 中复制版本。

### 3.8 FND-001 无歧义契约

- `label` 必须满足 `type(label) is int`；
- `predictions` 必须满足 `type(predictions) is list`；
- 每个 prediction 必须满足 `type(prediction) is int`；
- `bool` 在 label 和 prediction 位置均拒绝；
- 空 predictions 抛出 `ValueError`；
- 输入不得被修改；
- 上述契约错误统一抛出 `ValueError`；
- 正常返回与 label 不同的 prediction 数量。

### 3.9 规模约束

目标规模：

- Production Python：600–1000 行；
- Schema/Catalog/Template：250–450 行；
- 测试：700–1200 行；
- README 之外的新增说明仅本 ExecPlan；
- 总新增目标少于 3000 行。

若超过 3000 行，必须先删除未被纵向闭环调用的抽象；仍无法压缩时，在最终报告逐模块解释。

## 4. 变更前基线

- 分支基点：`1f3f57689e37b60ec61f4673dfcacf754047011e`；
- 实施分支：`refactor/oss-lean-v2`；
- Python：CPython `3.11.9`；
- pytest：`8.4.2`；
- `python -m pytest --collect-only -q`：177 个 Repository Health 节点；
- `python -m pytest -q`：174 passed，3 skipped；
- `scripts/validate_curriculum.py`：通过，4 tasks；
- `scripts/validate_external_courses.py`：通过，1 pack / 5 assignments / 124 problems；
- `scripts/validate_state.py`：通过，当前 `00A-1:needs_revision`；
- `scripts/export_handoff.py --dry-run`：通过且未写归档；
- 当前定向测试：5 passed，1 failed；失败为非整数 prediction 未抛 `ValueError`。

根健康测试目前没有收集 `tests/stage00/`；该训练测试继续通过精确命令人工运行，不纳入 CI 成功条件。

## 5. 实施里程碑

### M1：公共边界与 package

- 更新 ignore、package discovery、依赖入口；
- 创建 Workspace 模板、Schema、Demo 和 profiles 边界；
- 实现 Workspace 初始化与事件 reducer。

验收：定向 Workspace/Event 测试通过，真实 Profile 创建前 ignore 检查通过。

### M2：Catalog 与 FND-001

- 创建单节点 YAML Catalog 与 JSON Schema；
- 实现 Schema 和 DAG 校验；
- 添加 FND-001 四文件资产。

验收：Catalog、DAG、资产完整性和契约测试通过；无其他问题目录。

### M3：Loader、grader 与 CLI

- 实现统一 loader；
- 实现 pytest plugin 与独立子进程 grader；
- 实现批准的七个 CLI 命令；
- 加入 infrastructure-only add_one fixture。

验收：正负 grader 路径、start 幂等性、事件幂等性和 CLI 闭环通过。

### M4：迁移与兼容验证

- 复制前验证 Profile 路径被忽略；
- 对 allowlist 源文件做安全复制；
- 校验逐文件 SHA-256 相等；
- 校验旧状态与新 reducer 的语义等价；
- 原文件继续保留。

验收：`git status` 不显示 Profile；`git ls-files workspace/profiles` 只有 `.gitkeep`。

### M5：全量验收与提交

- 运行变更后 collect-only；
- 运行所有新旧测试和 validators；
- 演示 CLI starter 失败与 infrastructure fixture 成功；
- 补全本报告并移动到 `plans/completed/`；
- 分逻辑提交，不推送、不合并。

## 6. 风险、停止条件与回滚

立即停止条件：

- Python 3.11 环境不可用；
- 变更前基线失败；
- ignore 检查失败；
- SHA-256 或 reducer 等价失败；
- 需要修改当前维护者答案才能继续；
- 旧 Repository Health 节点静默消失；
- 根 pytest 收集课程题或 Profile；
- Demo 或 tracked diff 出现真实个人信息。

回滚不使用 `git reset --hard`：

- 未合并时 `git switch main` 恢复原项目视图；
- 单个逻辑错误使用 `git revert <commit>`；
- 保留 feature branch 和 ignored 迁移副本供审计；
- 不自动删除原始或复制后的个人数据；
- 不重写 Git 历史。

## 7. 决策日志

- 2026-08-27：批准只做 Vertical Slice 1，不分别完成 B1–B5。
- 2026-08-27：文档修改缩减为 README 与本 ExecPlan；其余文档等待真实实现稳定。
- 2026-08-27：Runner 与 Oracle 分离，pytest 不作为 Oracle。
- 2026-08-27：grader 正向 CI 使用独立 add_one fixture，不依赖 ignored maintainer Profile。
- 2026-08-27：依赖版本只维护在 `pyproject.toml`。
- 2026-08-27：Python 3.11.9 Gate 和 177-node collect-only 基线通过。

## 8. 当前进度

- [x] 创建功能分支；
- [x] 建立 Python 3.11 环境；
- [x] 记录变更前 collect-only 与完整基线；
- [x] 固化批准修正和停止条件；
- [x] 实现公共边界、Catalog、Workspace 和 CLI；
- [x] 安全复制并验证维护者数据；
- [x] 完成全量验收、提交与复盘。

## 9. 最终复盘

### 9.1 实现结果

- 新 package 只包含 Vertical Slice 1 调用链：Catalog/DAG、Workspace、Events、Submission Loader、pytest plugin、Grader 和 CLI；
- 新 Catalog 只有 `FND-001`，旧 ID `00A-1` 作为迁移映射；
- FND-001 目录严格只有四个 public asset，没有参考答案；
- Workspace 只跟踪模板、Schema、虚构 Demo 和 `.gitkeep`；
- CLI 只有批准的 `doctor/init/next/show/start/test/submit`；
- `requirements.txt` 只含 `-e .[dev]`，所有依赖版本只在 `pyproject.toml`；
- 旧脚本、Makefile、external pack、state、review、progress 和当前答案均保留。

### 9.2 收集与测试证据

变更前：

- collect-only：177 nodes；
- Repository Health：174 passed，3 skipped；
- 当前旧定向测试：5 passed，1 failed。

变更后：

- collect-only：205 nodes；
- 新增 28 nodes，全部来自四个 `test_lean_v2_*` 基础设施文件；
- 没有旧 Repository Health node 被迁移或排除；
- Repository Health：201 passed，4 skipped；新增 skip 是 Windows 无权创建 symlink，测试未被 xfail 或隐藏；
- 旧 `validate_curriculum.py`：4 tasks，通过；
- 旧 `validate_external_courses.py`：1 pack / 5 assignments / 124 problems，通过；
- 旧 `validate_state.py`：`00A-1:needs_revision`，通过；
- 旧 `export_handoff.py --dry-run`：通过且没有写归档；
- 旧定向测试仍为 5 passed，1 failed，`src/stage00/hard_sample_miner.py` 无 diff。

根 pytest 继续只由 `tests/infrastructure` 与 `tests/regression` 提供节点。课程 `test_public.py`、`workspace/profiles/*` 和 learner submission 不在根收集中。旧兼容健康测试继续由 CI 的 `python -m pytest -q` 运行，旧 validators 保留独立 CI step。

### 9.3 CLI 证据

Answer-free starter Profile：

- `init` 创建本地 Profile；
- `next` 只显示 FND-001；
- 第一次 `start` 创建 `attempt-0001`；
- 第二次 `start` 返回同一路径，SHA-256 不变；
- 正式 grader 结果为 17 failed；
- `submit` 只记录失败 submission，不写 implemented；
- 输出始终为 `MASTERY: NOT YET`。

正向 Grader：

- CI 使用完全独立的 `tests/fixtures/grader/add_one/`；
- valid submission 为 2 passed；
- missing symbol、syntax error、import error、runtime error、wrong path、cache isolation 与 SHA-256 均有测试；
- 一个 ignored FND-001 协议探针以固定调用顺序验证真实 CLI 正向链路：17 passed，随后 submit 写入一次 `task_implemented`；
- 重复 submit 没有重复追加 `task_implemented`；
- implemented 后普通 start 被拒绝；
- 协议探针不读取输入、不是通用解法、不进入 Git、不得作为学习证据。

### 9.4 维护者数据迁移

复制前，以下目标均由 `git check-ignore -v` 确认命中 `/workspace/profiles/*`，`.gitkeep` 由反向规则保留。

迁移采用 12 条明确 copy mapping，共 11 个不同源文件；当前答案同时保存为 legacy snapshot 和 FND-001 submission。来源覆盖：

- `state/` 六个现有状态文件；
- 当前 review 与 test run；
- handoff export 与 external-review handoff prompt；
- 当前 `hard_sample_miner.py`。

逐项源/目标 SHA-256 结果为 12/12 MATCH。摘要值没有写入公共报告；原文件全部保留且未修改。

新 reducer 等价断言全部通过：

```text
problem_mapping=true
revision_required=true
assistance_level=true
public_tests=true
not_implemented=true
```

新 Profile 事件为 `profile_created → legacy_import → public_tests_run`，映射 `00A-1 → FND-001`、H1、5 passed / 1 failed、revision required，且没有伪造 implemented/reviewed/mastered。

Profile 创建及复制前后的 `git status --porcelain` 无差异；提交后 `git ls-files workspace/profiles` 只有 `workspace/profiles/.gitkeep`。

### 9.5 规模偏差与理由

本切片相对 `main` 为 3442 个 Git 新增物理行、109 个删除物理行，因此按批准条件解释：

- Production Python 1547 行：七个 CLI 协调、Catalog/DAG、事件校验/reducer、Workspace 生命周期、唯一 loader、pytest plugin 和独立子进程 grader；每个模块均被 FND-001 或 doctor 实际调用；
- Schema/Catalog/Template 469 行：Catalog、Profile、Event 三个严格 Schema，以及单节点 Catalog、模板和 Demo；
- 新测试及 grader fixture 587 行，repository contract 另增 56 行：覆盖批准要求的所有正负路径，未以重复测试凑行数；
- FND-001 四文件资产 126 行：题面、无答案 starter、公开测试和 H1/H2/H3；
- README、Workspace README 和本 ExecPlan/迁移报告共新增 632 行；其余 25 行是 packaging、ignore 与 CI 边界。

Production Python 超出 1000 行的优先目标，主要来自 CLI 384、Events 281、Workspace 296、Catalog/DAG 243 和 Grader/Plugin/Loader 338；`__init__.py` 为 5 行。这里统一采用 `git diff --numstat` 的物理行口径，避免与忽略空行的逻辑行统计混用。没有 Web、数据库、AI Coach、Track/Quest/Capstone、生成器、未来节点或未调用扩展点；继续压缩会把事件契约、错误分类或路径边界重新塞进 CLI，降低可审查性。

### 9.6 实施中发现并修正的问题

- Editable install 首次暴露旧 metadata 冲突：许可证表达式与已废弃 classifier 重复；只删除冗余 classifier，Apache-2.0 未改变；
- 第一次定向测试发现注释字符串误判和运行时 `__pycache__` 被当作第五个资产；改为 tracked/public asset 严格四文件、运行时忽略 cache，并让 grader 子进程禁写 bytecode；
- PowerShell `python -c` 引号处理导致迁移事件脚本在解析前失败；此时只有 `profile_created`，无半写事件。改用 ignored cache 中一次性脚本，并在追加前断言事件序列只有初始化事件。

### 9.7 未迁移内容

- 旧公共 fixture 尚未删除，也尚未切换为新 Profile 权威源；
- 旧 `catalog.json`、Navigation、状态 Markdown 和旧脚本仍是兼容层；
- FND-002 及后续 Golden Path 未创建；
- 大规模 Planned Catalog、Track/Quest/Capstone、AI Coach Schema、动态变式、review/retention CLI 均未实现；
- 暂缓文档未修改；
- 本分支未合并、未打 tag、未发布、未推送真实 Profile、未重写历史。

### 9.8 回滚

- `git switch main` 可立即回到原公共项目视图；
- 功能分支保留所有提交和迁移报告，不需要 reset；
- 单个逻辑需要撤回时使用 `git revert <commit>`；
- ignored `maintainer-v1` 是副本，原数据仍在原位，不自动删除任一份；
- 本切片不执行 `git filter-repo`，也不自动删除分支或 Profile。
