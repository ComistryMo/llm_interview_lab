# Luna Max 动态面试当前状态报告

更新时间：2026-09-02  
仓库：`E:\\hz-llm-interview-lab-codex`  
分支：`feature/product-v1-phase2-reliability`  
基线 HEAD：`8eefde9fdfe74be6ca330cb638e08c00a02268bf`

> 本报告只记录当前实现和人工验收发现。本轮按用户要求不修复下列两个问题，不构建 Windows/macOS，不运行全量回归。

## 一、当前实现概况

当前分支已经包含以下已提交前的源码修改：

- 动态面试首题路径：创建真实 `dynamic_ai` Session，仅持久化 `q-001` 本地开场题；
- 上下文确认弹窗：按“岗位技能与面试流程 / 求职意向与能力自评 / 授权材料”分行展示，材料 SHA 使用短摘要；
- Codex 面试官入口：支持连接、模型与推理强度配置的现有路径；
- 动态后续问题调用链：回答锁定并请求 Codex/Provider 评估后，只有返回非空 `follow_up` 时才追加一个下一问题；
- 异步操作的 Profile、Interview、Question、Operation ID 隔离和 busy 门控；
- Interview 页面确认弹窗底部按钮颜色和布局已改为深色主题一致；
- 启动运行时、错误状态、Schema 和针对性桌面测试已有相应变更。

## 二、人工验收发现（按要求暂不修复）

### 1. 输入框提示与实际输入重叠

**现象**：在回答框输入“我叫洪洲”或在评估证据框输入“aa”后，灰色提示仍停留在输入区域，与用户文字重叠，导致文字难以阅读；同时用户观察到文字基线/对齐不稳定。

**源码位置**：`src/llm_interview_lab/desktop/qml/pages/InterviewPage.qml` 中的 `TextArea` 对象：

- `id: answer`（主回答）；
- `id: evidence`（回答证据）；
- `id: followupAnswer`（追问回答）；
- Coding 区的 `id: codingEditor` 也使用同一类编辑器样式。

这些控件当前依赖 Qt `placeholderText` 与 `padding` 的组合。截图证明当前实现没有满足“开始输入后提示立即消失、文本与边距一致”的用户可见契约。

**状态**：`OPEN / P0 UX`。本报告不修改实现。

### 2. 当前人工路径只看到一个问题

**源码事实**：

- `role_interviews.create_dynamic_role_interview()` 创建 Session 时只写入 `q-001`；
- `q-001` 的来源为 `process_opening`，标题为“自我介绍与经历概述”；
- 后续问题只能经由 `append_dynamic_role_question()` 追加；
- Controller 只有在当前回答已锁定、Codex/Provider 评估返回合法结果且 `follow_up` 非空时，才追加一个 `q-002`，并重新加载当前 Session。

**产品语义**：这不是“开始时生成完整题单”，而是一问一答的动态模型。首屏只有一个问题是当前设计的预期行为；但“回答后能否实际得到下一问”仍需要一次成功的 Codex/Provider 真实传输才能证明。

**人工验收状态**：本次截图/操作停留在首题或上下文确认流程，尚未取得成功的 `q-002` 证据。因此不能声称动态追问已经在真实 Codex 会话中可用，也不能把“只有一个问题”描述成已完成的动态面试体验。

**状态**：`OPEN / P0 FUNCTIONAL VERIFICATION`。按用户要求本轮不修复、不扩展题库。

## 三、测试与运行证据

本轮之前已执行的直接验证：

```text
.venv\\Scripts\\python.exe -m pytest tests/infrastructure/test_desktop.py -k "dynamic_interview_enters_with_local_opening or codex_dynamic_first_question or interview_setup_uses_profile_role_availability_and_real_report or standalone_runtime_seeds_public_assets" -q
5 passed, 33 deselected in 16.45s

QT_QPA_PLATFORM=offscreen .venv\\Scripts\\python.exe -m llm_interview_lab.desktop.main --smoke-test --window-size 1280x800
status: ok
```

真实隔离 Controller 探针曾得到：

```text
delivery_mode = dynamic_ai
interview.status = active
total_questions = 1
question_id = q-001
source.kind = process_opening
busy = false
```

本报告生成后没有再次运行测试，没有运行 `pytest -q` 全量，没有构建应用，没有触发 CI。

## 四、数据与未提交文件

当前工作树仍包含已有源码修改以及人工 UAT 目录。以下文件/目录被保留但不应进入源代码提交：

- `.uat-phase2-manual-0902/`、`.uat-luna-manual-0902/`、`.uat-luna-visual-0902/`：隔离 UAT 数据、日志和截图；
- `.tmp_controller_extract.txt`：临时探针文件；
- 用户提供的产品计划、反馈、评审和 `test结果.md`；
- `app-icon-quiet-forge-v1.png`：用户提供的原始图标资产。

这些文件没有被删除、覆盖或清理。源代码提交只包含已跟踪的实现/测试/Schema 修改，以及本报告和现有动态面试实施计划。

## 五、下一步（不在本轮执行）

1. 用 Fake Codex 或真实可用 Codex 完成一次“锁定 q-001 → 请求评估 → 追加 q-002”的定向验证；
2. 单独修复所有 `TextArea` 的 placeholder 可见性和文本边距对齐；
3. 在上述两项通过后，再由维护者进行人工 UAT，不以静态截图或单个 smoke-test 代替。

## 当前裁决

`WAITING_FOR_MANUAL_INTERVIEW_UAT`  
本报告记录了两个未修复问题；当前实现不能宣称“输入框体验已修复”或“Codex 动态多轮面试已完成”。
