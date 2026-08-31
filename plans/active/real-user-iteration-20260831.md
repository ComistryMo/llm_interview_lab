# 真实用户迭代（2026-08-31）

- [x] 复现并记录基线；Luna 审计因 429 不可用，改由主控按同一分工核验
- [x] Slice A：活动 Profile 恢复、首题失败解耦、材料能力提示
- [x] Slice B：中文首屏与 Coach/Home/Command Palette 布局修正
- [x] Slice C：No-AI 面试边界与 AI 面试入口核验；语音 MVP 未实现，需明确阻断
- [x] Slice D：PDF / DOCX 文本快照、AI 生成计划预览确认、动态追问与真实语音转录通道（源码级 MVP 已完成；平台/麦克风实机验收仍待补）
- [x] 完成定向测试与唯一一次本地全量回归（507 passed, 14 skipped）
- [x] 生成并人工抽查 64 格合成截图矩阵；截图契约通过
- [ ] RC CI 与 Windows/macOS 候选产物实机验收（本轮尚未触发，发布阻断）
- [x] 生成 `REAL_USER_ITERATION_FINAL_ZH.md`，最终裁决标记为 PARTIAL

范围冻结：不新增课程/角色/顶层目录，不重写 Core/Events/Workspace，不提交真实 Profile、材料、答案、Secret 或 Oracle。

Slice D 复用现有 `RoleInterview`、Provider、Catalog Grader 与 Profile 隔离：只走通 `post_training_engineer + new_grad + medium + OpenAI-compatible` 的真实 Golden Path。非代码题由 AI 生成后先预览确认；Coding 仍由验证过的 Catalog 题冻结。PDF/DOCX 仅在本地生成绑定源文件 SHA-256 的文本快照；语音实现本地录音、用户明确同意后的 OpenAI-compatible 转录和可编辑文本降级，不新增实时语音 Agent。连接就绪由控制器布尔状态裁决，QML 不解析展示文案；切换 Profile 会清理语音和待确认计划状态。
