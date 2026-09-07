# 首页、AI 手撕与面试追问迭代

基线：`daa2047616c0eff7e7d35f6a5db210f44ef8a610`；分支：`fix/dynamic-interview-full-flow-20260905`。

## 目标与范围

- 首页：单一当前任务、清楚的训练/面试入口、次级学习记录；取消并排大统计卡。保留当前任务、复测、面试恢复的已有动作，不更改业务优先级。
- 内容：已有 SGD、Momentum、MHA、GRPO Advantage/Loss 不重复建立。从 planned 落地 OPT-003 Nesterov、LOSS-002 标签平滑、ATT-003 因果与填充掩码、PT-019 GSPO 序列比率；保留原 ID，除下述解锁问题外保留前置。提供中文题面、原创建议接口、公开测试、提示与口述追问。通过私有 Oracle 后才提升验证等级。
- 面试：外部资料分清官方指南与个人面经；细化八岗位追问角度、级别与难度、答不上来时换角度。复用实际每轮发送的策略，不生成整场题单。
- 不改 Provider、事件、掌握状态、面试状态机，不读取真实档案，不全量回归、不打包、不触发 CI 或发布。

## 事实与取舍

已查看当前正式首页截图：大卡片过重，统计与主要动作同级，面试岗位标题仍为英文。已有基础手撕均有对应节点，本轮补相邻能力而不是增加重复题。

研究只保留可核查的摘要/来源。个人面经属于 anecdotal/unverified，不能推断公司统一标准或题目频率；算法定义使用官方文档/论文。低可信聚合“标准答案”不用于题面。

DEC-001：PT-019 原规划硬依赖 PT-015，但 `ApplicationService.start_practice` 要求前置 mastered，而 PT-015 没有 D+2/D+7，实际无法解锁。GSPO 接口不调用 GRPO 实现，因此把 PT-015 留作题面推荐顺序，硬前置改为实际需要且已有复测的 LOSS-008/TNS-010。只调整这个新落地节点的边，不重构 DAG 或降低掌握标准；新增测试检查四题全部祖先的复测可用性。

## 实施与验证

1. 首页局部 QML；现有 Home 领域测试 + 正式页面 900×620、1080×680、1280×800、1440×900，深浅色与放大字体，查看截图。
2. 四个节点及私有 Oracle：逐题 `scripts/validate_oracle.py <ID>`；只跑新增内容的静态/资产测试，不跑其他题目的 Oracle。
3. 面试策略：`tests/infrastructure/test_dynamic_interview_flow.py` 定向验证真实上下文注入、流程边界；若做真实模型探针，使用合成背景并单独记录，不把提示词静态测试当作模型效果证明。
4. 最终检查 `git diff --check`、定向文档/题库契约；分逻辑提交并推送当前分支，提交标记 `[skip ci]`。

## 风险与停止条件

不覆盖任何已存在用户文件或 Oracle。新题前置必须可达；无匹配验证证据不得称为已验证；没有实现的 D+2/D+7 明确说明，不授予掌握。若首页出现裁切先修布局，不缩小字体遮掩。真实用户 UAT、macOS 和打包均不在本轮证据范围。

## 完成与证据

- [x] 首页：一项当前任务，次级浏览/进度，三列轻量记录；中文岗位名，最近面试使用本地时间，未完成场次不突出零分。
- [x] 原生 Windows、正式 Main.qml/AppController、隔离合成档案：900×620（125% 字号）、1080×680、1280×800、1440×900，各深浅色。实际点击继续面试、题库、进度和开始训练；已查看小窗口、深色与浅色截图。公开四张实图见[清单](../../docs/images/home-polish-20260907/manifest.json)，不是 demo controller。
- [x] 新增四题：42 项公开 + 12 项独立私有验证通过；Catalog 现为 Ready 49、Planned 180、Oracle 37，Retention-ready 仍 24。四题自身没有复测资产，不能授予掌握；全部硬前置祖先都有实际 D+2/D+7。
- [x] 八岗位每轮策略注入、级别/难度分离、本人证据/取舍/反例/换角度；三条面试来源明确区分官方、个人自报与聚合经验，四条数学来源采用官方文档/原论文。
- [x] 真实 DeepSeek：仅用既有合成 UAT 连接的 Keyring 引用，合成后训练实习简历/JD；简单与高压各连续三次调用，均从 q-001 接续到 q-004。每次请求到下一问持久化 2.64–5.55 秒。没有调用真实用户档案，没有把 Key 写入文件。
- [x] 源码/文档按切片提交；向原分支正常推送，不合 main、不创建 Tag、不发布。

### 实际命令与结果

仓库 `.venv/Scripts/python.exe`，`PYTHONPATH=src`；原生 UI 设置 `QT_QPA_PLATFORM=windows`，截图输出到 ignored `workspace/maintainer/home-polish-20260907/ui`。

```text
python scripts/validate_oracle.py OPT-003    # public 13 + private 2 passed
python scripts/validate_oracle.py LOSS-002   # public 10 + private 5 passed
python scripts/validate_oracle.py ATT-003    # public 9 + private 2 passed
python scripts/validate_oracle.py PT-019     # public 10 + private 3 passed
```

PT-019 因 DEC-001 修改题面/前置后仅重跑该题一次并更新 fingerprint；没有跑其他既有题的 Oracle。源码指纹和四种接口均由新增内容契约核验。

```text
python -m pytest tests/infrastructure/test_alpha4_home_p1.py tests/infrastructure/test_dynamic_interview_flow.py tests/infrastructure/test_interview_input_runtime.py tests/infrastructure/test_ai_handwriting_expansion.py -k "home_layout_and_real_entry_points or new_handwriting or conversation_strategy or original_assets or prerequisites_ready or due_d2_replaces or due_d7_replaces or dashboard_counts_all or compact_evidence or standard_home" -q
18 passed, 68 deselected (33.75s)

python -m pytest tests/infrastructure/test_chinese_docs.py tests/infrastructure/test_lean_v2_catalog.py -k "readme_relative_links or readme_statistics or four_public_assets or problem_tests_depend_only or dag_order or ready_problems_never_require" -q
6 passed, 17 deselected (3.73s)

python -m pytest tests/infrastructure/test_chinese_docs.py -k "readme_relative_links or screenshots_are_real_png" -q
2 passed, 8 deselected (0.16s) — 更新截图链接后定向复查

git diff --check
四张新截图 SHA-256、PNG 尺寸、source commit 存在性：通过
```

开发中的失败没有隐瞒：初版 UI 测试错用了不存在的页面 objectName，改为实际路由与可见编辑器断言；随后原生交互复现 `HomePage.qml` 在切换题目时读取空 `focusProblem.environment`，已加局部加载判断并重跑通过。初版新增题候选测试误将所有题归入实习/后训练，修正为已有级别与岗位映射，没有为了测试放宽面试规则。

真实模型探针为 ignored `workspace/maintainer/home-polish-20260907/probe_interviewer.py`。简单模式三轮均成功，但探针收尾误调用不存在的方法，结果文件如实保留 `AttributeError`；改用既有 `finish_interview` 后高压三轮及收尾成功，简单场次也已本地按未完成结束，未为此重复模型调用。结果在同目录 `strategy-result.json` / `strategy-hard-result.json`，不提交原始对话。

### 复盘与边界

简单示例由“介绍去重工作”追问哈希对文本扰动的行为，再根据候选人“没有验证”转向其分组脚本；高压样本更关注未覆盖扰动与异常用户 ID。每轮仍是一项主题，未捏造实习/论文或训练成果。只有一份合成背景、两种难度的小样本，不能推断全岗位质量；也没有在本轮重新验证 Codex、多模型完整面试或 macOS。

未运行：完整 pytest、全课程 Oracle、RC CI、Windows/macOS 打包、跨平台实机、真实用户 Field Run。私有参考/测试、运行记录、原有用户未跟踪文件均留在原处，未加入提交。

代码提交：`85e2d62` 首页，`5f66a75` 四题与中文展示，`8038a20` 面试策略/来源；文档与截图在后续独立提交。版本号未递增，旧 Release 未变；用户可继续使用 `docs/desktop-app.md` 的源码启动命令，不需要重置原 UAT 数据。
