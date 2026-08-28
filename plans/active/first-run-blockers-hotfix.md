# 首次使用阻断 Hotfix Checklist

目标：只恢复“打开应用 → 明确选择岗位 → No-AI → 点击一次开始训练 → 进入首题或首页；失败时给出可操作原因”的最短链路。基线为 `main@5e83f8f`；用户提供的未跟踪评审文件仅作为证据，不修改、不提交。

## 复现

- [x] 临时数据根复现岗位布局与 `completeOnboarding`，记录输入、失败阶段、异常类型和脱敏日志。
- [x] 核对 Windows one-file 启动、资源准备、日志初始化与不可见 stderr 链路。

## 岗位选择

- [x] 显式几何的 2/1 列岗位卡片、主动选择、稳定选中态、空状态、内联错误和不遮挡 CTA 的 Toast。
- [x] 1536×992、1280×800、1100×700 截图与人工检查。

## 开始训练

- [x] 输入先验证后写档案；修复真实根因；专用错误码/中文提示；重复点击门控。
- [x] 成功进入首题或首页；无解锁和 AI 不可用均不阻断 Onboarding。

## Windows 启动

- [x] 推荐 portable 改为 standalone/onedir；one-file 若保留仅标实验性。
- [x] Repository 初始化前 bootstrap 日志；关键早期失败显示 Windows 原生错误框。

## 目标测试

- [x] 各切片仅运行直接相关测试；集成后只运行一次本地全量回归。
- [x] 直接相关的 RC 修正验证已触发；初次 Windows 包发现失败后只修复该 Job 路径，未重跑本地全量。

## 实机验收

- [x] macOS/源码临时数据根首用链路与重启持久化证据。
- [ ] Windows standalone 候选仍等待远端构建；在候选可下载并完成双击矩阵前保持阻断。

## 发布文档

- [x] 更新 README、Windows/桌面指南、截图和 `HOTFIX_FINAL_ZH.md`；不自动发布 Release。

回退：按独立小提交逐项 revert。停止条件：可能丢失真实 Profile/Submission/Key、需要重写历史、无法兼容公开 CLI，或必须扩大到冻结范围之外。
