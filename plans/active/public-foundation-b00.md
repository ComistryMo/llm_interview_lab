# Public Foundation B00 ExecPlan

## 1. 目标与可观察结果

把当前个人训练原型升级为可公开维护、可复用、可由不同 AI 教练适配的训练仓库，同时不改动学习者当前答案。

完成时应能观察到：

1. Python 3.10+ 环境要求和唯一 pytest 入口可被机器检查；
2. 默认测试不因未解锁 TODO 永久为红；
3. 任务状态、帮助等级和复测状态有唯一、可校验的定义；
4. 项目事实模板不会诱导用户提交雇主敏感信息；
5. handoff 导出采用显式 allowlist、拒绝符号链接并生成 manifest；
6. README 能指导新用户完成安装、个性化、一次训练闭环和 AI 适配；
7. 开源治理文件、贡献流程和安全说明齐全；
8. 当前学习者 `src/` 的函数、TODO 和行为不被修改；仅允许注释级隐私净化；
9. 所有可运行测试通过，已知未完成学习任务被准确隔离；
10. 仓库初始化 Git、建立公开基线提交并推送到指定 GitHub 远端。

## 2. 审计开始时的仓库事实

- 本地目录当时尚未初始化 Git；现已建立 `main` 与 `origin`，尚未创建首提交；
- 远端 `git@github.com:ComistryMo/llm_interview_lab.git` 可通过 SSH 访问且当前无 refs；
- 当前解释器为 Python 3.9.2，`python -m pytest` 为 pytest 8.4.2，`torch` 未安装；
- 当前 Task 是 00A-1，状态 `needs_revision`；定向测试为 5 passed, 1 failed；
- 后续 00A-2、00B、00C 均有 TODO，因此当前全套测试本来就不应作为绿灯；
- 当时的 handoff 误复制了 Progress，现已替换为通用 `state/HANDOFF.md`；
- 多份总计划重复；
- 项目事实模板和 denylist 导出器不适合直接公开；
- 用户明确授权实施 B00a/B00b/B00c/B00d、初始化 Git、同步 GitHub，并将仓库维护成公开可复用项目。

## 3. 范围与明确不做

### 范围

- 环境元数据、pytest 配置、环境检查；
- 状态机、事件 ledger、状态校验；
- 隐私边界、公开模板、安全导出；
- 文档去重、跨平台安装、AI 适配指南；
- 开源许可证、贡献、安全、行为准则、issue/PR 模板和 CI；
- Git 初始化、基线提交、远端推送。

### 明确不做

- 不修改 `src/` 中任何学习者函数、答案逻辑或 TODO；公开发布只做两处 docstring 隐私净化；
- 不让 00A-1 测试通过；
- 不提前实现 B01 之后的课程内容；
- 不把公司源码、路径、配置、日志、指标或原始证据放入仓库；
- 不创建几十个未来空 Task 文件；
- 不伪造测试结果、项目经历或 upstream 贡献；
- 不自动提交用户未审阅的后续学习答案。

## 4. 分阶段里程碑

### M0：公开发布阻塞审计

- 完成架构、隐私、工具三路只读审计；
- 确认远端为空、SSH 可用；
- 建立本 ExecPlan。

### M1：B00a 环境与测试入口

- 增加 Python 3.10+ 项目元数据与 pytest markers；
- 增加环境检查脚本；
- 默认测试只跑已解锁/基础设施测试；
- 当前 Task 与未来 TODO 测试有明确入口；
- 跨平台命令不依赖 Make。

### M2：B00b 状态模型

- 统一 `implemented/reviewed/retained_48h/retained_7d/mastered`；
- `demonstration_only` 作为 attempt 属性；
- 增加 append-only JSONL ledger 与校验脚本；
- 修复 handoff 和状态文档，但保持当前 Task 仍为 `needs_revision`。

### M3：B00c 隐私和导出

- 建立公开项目事实模板；
- 明确禁止 AI 读取雇主材料；
- 导出器改为仓库内显式 allowlist、拒绝 symlink、输出 manifest/hash；
- 为路径逃逸、敏感文件、符号链接、重名和 dry-run 增加测试。

### M4：B00d 与开源化

- README 重写为公共项目入口；
- 一个 Master Plan 为权威计划；
- 增加个性化与 AI 适配指南；
- 增加 LICENSE、CONTRIBUTING、SECURITY、CODE_OF_CONDUCT、CHANGELOG；
- 增加 GitHub CI、issue/PR 模板；
- 保留 Codex 的 `AGENTS.md`，并提供其他 AI 可读取的通用协议入口。

### M5：验证与发布

- 运行基础设施测试、当前定向测试和默认测试；
- 检查链接、敏感词、TODO 与打包 manifest；
- 进行三路复审并修正；
- 初始化 Git，提交一次公开基线；
- 基于本地基线提交运行 tracked-only 导出预检；
- 对最终 index 和提交重新做隐私检查；
- 添加 origin，推送默认分支；
- 验证远端 branch 和可见性。

## 5. 测试命令

预期逐步建立并运行：

```text
python -m pytest -q
python -m pytest tests/stage00/test_task_00a1.py -q
python -m pytest tests/infrastructure -q
python scripts/check_environment.py
python scripts/validate_state.py
python scripts/export_handoff.py --dry-run
```

当前 A1 定向测试预期仍为 5 passed, 1 failed；这不是 B00 回归失败。

## 6. 风险、回退和停止条件

### 风险

- 公开仓库中残留个人/雇主敏感信息；
- pytest marker 误隐藏已解锁回归；
- 状态校验与 Markdown 事实漂移；
- 导出器 fail-open；
- 开源文档过度绑定单一 AI；
- 首次提交混入缓存、附件或私有文件。

### 回退

- Git 初始化前保留逐文件 patch 审查；
- 首个 Git 基线建立后，每个后续逻辑阶段使用独立提交；
- 推送前再次检查 `git status --short` 和 `git diff --cached`；
- 若远端出现意外历史，停止并比较，不 force push；
- 若无法证明公开安全，停止推送。

### 停止条件

- 发现疑似公司源码、配置、真实日志、凭据或不可确认公开的指标；
- 远端不再为空且历史来源不明；
- SSH 身份与目标仓库不匹配；
- 默认测试或安全测试出现未解释失败；
- 用户当前答案被意外修改。

## 7. 决策日志

- 2026-08-26：选择先治理后推送，避免把个人原型和潜在敏感模板直接公开。
- 2026-08-26：保留 `AGENTS.md` 作为 Codex 原生适配；通用教练规则放在 `docs/AI_COACH_ADAPTER.md`，避免绑定单一厂商。
- 2026-08-26：不使用未来 TODO 的失败作为默认测试失败；通过 marker/目录入口区分 current、regression 和 locked。
- 2026-08-26：不在 B00 中修改任何 `src/` 答案。
- 2026-08-26：采用 Apache-2.0；公开版本标为 alpha，Template 功能留待物理分离后。
- 2026-08-26：新增私人 workspace 生成器，避免新用户继承维护者 fixture，并禁用 upstream push。
- 2026-08-26：`src/` 仅净化两处雇主指向的 docstring；函数体、签名、TODO 和行为保持不变。

## 8. 当前进度

- [x] 读取仓库规则、学习者状态、教练协议和当前任务；
- [x] 核验远端可访问且为空；
- [x] 建立 ExecPlan；
- [x] 完成三路设计审计与第二轮复审；
- [x] M1 B00a；
- [x] M2 B00b；
- [x] M3 B00c；
- [x] M4 B00d/开源化；
- [ ] M5 验证和推送。

## 9. 最终复盘

待完成后填写：最终测试、公开 URL、提交 SHA、已知限制、后续 B01 建议。
