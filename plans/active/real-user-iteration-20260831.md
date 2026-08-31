# 真实用户迭代（2026-08-31）

- [x] 复现并记录基线；Luna 审计因 429 不可用，改由主控按同一分工核验
- [x] Slice A：活动 Profile 恢复、首题失败解耦、材料能力提示
- [x] Slice B：中文首屏与 Coach/Home/Command Palette 布局修正
- [x] Slice C：No-AI 面试边界与 AI 面试入口核验；语音 MVP 未实现，需明确阻断
- [ ] 定向测试；所有 P0 收敛后仅一次全量回归；仅一次 RC CI
- [ ] 生成 `REAL_USER_ITERATION_FINAL_ZH.md`，如有未满足项明确标记 PARTIAL/BLOCKED

范围冻结：不新增课程/角色/顶层目录，不重写 Core/Events/Workspace，不提交真实 Profile、材料、答案、Secret 或 Oracle。
