# 桌面候选版 ExecPlan · 2026-09-09

## 目标与可观察结果

在现有桌面功能上完成六项人工反馈，并交付可运行的 Windows x64 候选包、macOS arm64 CI 证据、公共题库覆盖、正式页面对照、性能与升级验证。仅候选分支；不推送 main、不打公开 Tag、不发布或覆盖 Release。所有数据为本轮 synthetic；不访问真实 Profile、材料、答案、密钥或历史 Oracle。

## 当前事实与保留基线

- 源目录：`E:/hz-llm-interview-lab-codex`。起始 HEAD：`cb3d13bba6368ee26a2efeb660f625e22b43edce`，起始分支 main。
- 工作分支：`candidate/desktop-release-20260909`，从当前带未提交改动的工作树原地分支，未丢弃任何修改。
- 必须保留的未提交产品基线：Zipformer 流式预览 + Qwen3-ASR 0.6B 停句校准、模型下载/许可和测试、相关文档/比较脚本；六项反馈的 Controller/QML/中文题面修改。
- 未知附件、`.uat-*`、临时 Controller 摘录、用户原始图标/反馈/计划不批量提交、读取或删除。新实验只放 `workspace/maintainer/release-candidate-20260909/`。
- 源码版本目前 `0.4.0a3`；发布 workflow 写死 alpha.3，正式 publish 有覆盖旧资产行为，需要改为显式门禁且拒绝覆盖。
- Windows：Python 3.11 虚拟环境；PySide6 6.11.2、Nuitka 4.2、sherpa-onnx 1.13.7、PyTorch 2.13.0 已存在；E 盘约 67 GiB 空闲。`gh` 未登录，继续通过已配置 SSH 验证 Git 推送；不能把未执行的 CI/实机验收说成通过。
- 旧报告中的测试数量不是本轮证据。当前中文 Practice 原先误用简短摘要；完整翻译中 OPT-005 旧 SHA 分支也误拦了已中文化原文，现已修正待最终定向验收。

## 范围与不做

保留 Qt Quick/ApplicationService/CLI；不重写 Controller、业务协议或历史数据。保留计时、模型选择、逐场授权、冻结问答、评分证据、运行/测试区别、No-AI、语音、IME、草稿、连接密钥环。仅用户主动检查/下载官方 GitHub Release，不自动安装。课程新增资产未获人工审查不得提升验证等级或算进发布覆盖。

## 里程碑与验收

1. **六项反馈与基线（进行中）**：可收起侧栏、移除左下档案装饰（设置保留切换）、宽屏自然布局、完整中英题面、恢复配置与 SHA 绑定的材料选择、启动自动连接。真实 QML 输入/点击/重启与四尺寸双主题字体检查。逐场发送确认保留，记住选择不是启动发送。
2. **可靠性与测量**：先测冷/热启动、知识首次打开/重复查询、长历史渲染/滚动、提交本地开销、工作集；冻结阈值后优化。实现 Profile/session/question/revision 绑定的防抖口述草稿、切页/退出/IME/写入失败恢复；审计已有代码/知识草稿。禁止草稿自动提交或改写锁定答案。
3. **公共内容与更新**：生成精确覆盖矩阵及随包清单；补发现筛选/关联入口；依缺口准备少量待审训练闭环资产。新增官方 Release 查询、版本渠道比较、后台下载/取消/校验/打开位置和错误重试；检查公共资源同步及旧 synthetic 数据升级。发布脚本版本统一、禁止未经门禁发布/覆盖。
4. **集成、构建、证据**：仅此时一次全量回归；Windows 完整构建和无开发环境依赖启动，中文空格路径/升级数据验证；推送独立候选分支运行现有 CI 的 macOS arm64 构建/Artifact 检查。整理包 SHA、测试/性能/内容/UI、发布与回退说明。为本阶段保留排期最后三分之一；不在收尾新增架构。

### 命令与证据位置

所有命令采用隔离数据目录、QSettings 与无真实凭证的测试 fixtures。

```powershell
.\.venv\Scripts\python.exe -m pytest tests/infrastructure/test_desktop_resume_polish.py -q
.\.venv\Scripts\python.exe -m pytest --collect-only -q
.\.venv\Scripts\llm-lab.exe doctor
.\.venv\Scripts\llm-lab.exe knowledge validate --with-catalog
.\.venv\Scripts\python.exe scripts/validate_external_courses.py
# 草稿、搜索、更新、发布脚本及受影响原有测试：随实现记录精确选择
# 最终一次：python -m pytest -q；CPU PyTorch 精确验证
# 现有 pyside6-deploy / check_desktop_artifact.py 与 build_macos_desktop.py / check_macos_artifact.py
git diff --check
```

正式视觉复核：900×620、1080×680、1280×800、1440×900 × light/dark × 100%/125%，另含 2560 宽屏；原生 Windows 中文字体。基线/After 都使用真实 Controller/QML + synthetic，不用 Phase 0 原型。采集环境、SHA、命令、图像 SHA 后才入公共证据。

## 性能指标（测量后冻结，暂未宣称优化）

同机相同 synthetic 公共资源，冷首次样本与后续热样本分开；每项至少 5 次，报告中位数/p95（小样本同时保留原始值），内存使用工作集。待基线确定常用热点后冻结目标；至少一个真实路径改善，其他关键路径无超过测量噪声的实质退化。不得以禁用校验/语音/状态恢复实现提速。

## 风险、回退与停止

- 当前真实应用进程与数据不触碰；测试仅新隔离目录。新代码引入自动连接，测试必须使用可控连接替身，不能读取系统真实 Keyring。
- 记住材料配置仅预填相同 ID/SHA；新场次仍检查并确认发送范围，变更/撤权不恢复授权。
- 新语音模型仅下载到用户缓存，不把已下载模型/个人录音打包或提交。
- 无 gh 登录不阻塞本地开发；SSH/公开 CI 证据不足时如实报告具体平台未通过，不绕过发布门禁。
- 回退使用候选提交的可恢复 revert 或保留完整旧包；不重写 main/历史，不覆盖用户数据。
- 核心交付未实测或平台门禁失败，结论必须为“尚不可发布”。时间耗尽不是完成。

## 决策日志

- 2026-09-09：用户新的候选目标允许独立分支/CI/最终全量/打包，覆盖先前本轮禁止构建、仅 main 的限制；仍禁止正式发布。
- 2026-09-09：在当前工作树创建候选分支，完整承接 STT 与反馈修改；不 checkout 旧版本，不动其他 worktree。
- 2026-09-09：中文题面使用完整显示层翻译/已中文原文，不改固定题契约与测试；原始英文仍可切换。

## 进度日志

- [x] 阅读目标与必读产品/架构/课程/发布上下文，检查 dirty baseline、工具和磁盘；创建候选分支。
- [x] 六项反馈的第一轮修改及定向复核：可折叠侧栏、移除底部档案块（设置保留切换）、宽屏面试和 Practice 布局、96 道完整中文显示、版本绑定材料偏好、启动 AI 恢复；材料仍逐场确认。
- [x] 未提交口述草稿绑定 Profile/session/question/题目 SHA 与文本 revision，600 ms 防抖、真实子进程重启、锁定回答优先、写盘失败阻止关闭并允许重试；知识练习增加防抖和退出前保存。
- [ ] 性能基线、草稿恢复、性能改善与公共覆盖。
- [ ] 更新功能及发布脚本/资源升级验证。
- [ ] 最终回归、Windows 包实际启动、macOS CI/Artifact。
- [ ] 最终报告、包与校验、候选提交/推送和发布裁决。

## 最终复盘

待实际验证后填写；当前状态 `IN_PROGRESS / NOT_RELEASE_READY`。

### 当前定向证据与待查

- 六项反馈测试初轮 8 passed；草稿/重启/偏好组合 7 passed；本地 STT 与知识测试 27 passed / 2 skipped（既有实际模型/录音环境要求未满足，不是新增跳过）。928 tests collected 为实现中快照，非最终测试总数。
- 所有上述网络动作是受控替身，无真实凭证、麦克风或付费 AI 调用；正式 Windows QML 截图仅证明布局，不证明 AI 已连通。
- 性能脚本在独立 Windows 子进程中出现 Qt 原生访问错误，定位在 QSettings 同步附近；同样的单独 QSettings 及定向测试通过，尚未确定根因。不可用失败样本给性能改善结论；诊断脚本未作为完成资产提交。没有修改生产序列化或编辑器实例来掩盖错误。
