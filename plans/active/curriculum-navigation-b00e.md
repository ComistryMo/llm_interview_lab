# Curriculum Navigation B00e ExecPlan

## 1. 目标与可观察结果

在不触碰 `src/`、不改变学习者状态、不复制第三方内容的前提下，为公共课程建立可审计的双轴导航、机器可读任务元数据、外部参考登记和离线自动校验。

完成时应能观察到：

1. 只登记仓库中已经存在的 Task Card，不创建未来空任务；
2. 用户可按依赖阶段或岗位方向查找任务；
3. `public_maturity` 与私人学习状态被明确分离；
4. runtime、GPU 验收策略、可见测试、帮助前参考暴露级别均可机器检查；
5. 外部参考固定到具体 commit，并记录许可证边界、采用的抽象机制与明确不复制的材料；
6. CI 离线发现断裂依赖、重复 ID、错误测试节点、导航漂移、危险路径和未固定参考；
7. 当前 00A-1 定向结果和 `state/` 完全不变。

## 2. 当前仓库事实

- B00a–d 已发布为 `v0.1.0`，默认基础设施测试全绿；
- 当前唯一 Task 是 00A-1，状态 `needs_revision`、帮助等级 H1；
- `curriculum/` 当前有 00A-1、00A-2、00B、00C 四张任务卡；
- `CORE_40.md` 与 `MASTER_TRAINING_PLAN.md` 是长期路线，不代表对应任务已经存在；
- 参考仓库 `datawhalechina/llm-algo-leetcode` 的本次审计快照固定为 `c7a81f957c170c88c01ec71dfd1a838cee90b4a4`；
- 用户明确授权 B00e，并限定为导航、元数据、参考登记和自动校验。

## 3. 范围与明确不做

### 范围

- `curriculum/catalog.json` 任务 catalog；
- 由 catalog 确定性生成的 `curriculum/NAVIGATION.md`；
- 参考与来源治理文档及机器可读 registry；
- curriculum/reference 校验器、基础设施测试和 CI 入口；
- 为上述入口更新必要的 README、架构、测试和贡献文档。

### 明确不做

- 不修改 `src/`、starter 答案或任何学习者实现；
- 不修改 `state/`、review、progress 或当前 Task；
- 不复制外部仓库的文字、代码、测试、公式、图示或 Notebook；
- 不增加未来 Task Card、答案、提示或训练测试；
- 不引入网站生成器、Notebook 镜像或网络依赖；
- 不把 `public_maturity` 当作学习者 mastery 证据。

## 4. 分阶段里程碑

### M1：模型与治理

- 定义 catalog 字段、状态边界和双轴路由；
- 定义 reference registry 与 provenance 规则；
- 只登记现有四张任务卡和一个固定外部参考。

### M2：导航与校验

- 生成依赖轴、岗位轴与运行要求表；
- 校验 JSON 重复键、未知字段、路径、测试节点、依赖 DAG、reference exposure 和固定 revision；
- 校验生成页无漂移，并正确转义 Markdown 表格中的管道符与反斜杠。

### M3：集成与验证

- 将校验入口加入默认 pytest、CI、Makefile 和维护文档；
- 运行定向测试、全量基础设施测试、状态校验和导出预检；
- 检查 `src/` 无 diff、外部内容无复制、工作树与公开隐私边界。

## 5. 测试命令

```text
python scripts/validate_curriculum.py
python -m pytest tests/infrastructure/test_validate_curriculum.py -q
python -m pytest -q
python scripts/validate_state.py
python scripts/export_handoff.py --dry-run
python -m pytest tests/stage00/test_task_00a1.py -q
```

最后一条仍预期 `5 passed, 1 failed`。

## 6. 风险、回退和停止条件

### 风险

- catalog 与 Task Card 重复事实产生漂移；
- 生成导航被手工编辑；
- public maturity 被误解为个人掌握状态；
- 测试节点登记不完整或 GPU 策略含糊；
- 外部参考未固定版本、许可证范围误述或形成隐性复制。

### 回退

- B00e 使用独立提交，必要时可整体 revert；
- catalog 只承载检索和验收元数据，任务契约仍由 Task Card 负责；
- 生成导航只从 catalog 构建，不维护第二份手工表；
- 校验完全离线，外部站点不可用不会破坏本地训练。

### 停止条件

- 发现必须复制外部内容才能实现导航；
- 需要修改 `src/` 或学习者状态才能让校验通过；
- 无法把参考事实固定到可审计版本；
- 默认测试出现无法解释的回归。

## 7. 决策日志

- 2026-08-26：选择 JSON catalog + 确定性 Markdown 导航，避免引入 YAML/站点依赖。
- 2026-08-26：只登记现有四张任务卡；长期路线继续留在 Master Plan，不制造空任务。
- 2026-08-26：参考仓库只作设计级来源，固定 commit 并记录双许可证声明，不复制其内容。
- 2026-08-26：GPU 验收策略按任务声明；不能用粗粒度环境 skip 掩盖 CPU 必跑任务。

## 8. 当前进度

- [x] 读取规则、状态、协议、当前任务卡和 B00 历史；
- [x] 审计现有课程、测试节点与参考仓库固定版本；
- [x] M1 模型与治理；
- [x] M2 导航与校验；
- [ ] M3 集成与验证（本地验证完成，待 committed-HEAD workspace smoke 与远端 CI）；
- [ ] 最终复盘并移动到 `plans/completed/`。

## 9. 最终复盘

待完成后填写。
