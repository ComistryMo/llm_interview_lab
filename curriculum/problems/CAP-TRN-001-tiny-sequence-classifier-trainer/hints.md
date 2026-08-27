# 分级提示

## H1

先写出三个参数、pooled states、logits 与 loss 的 Shape，再逐项核对 deterministic
初始化、Mini-Batch 顺序、zero-grad 与 AdamW state 的生命周期。

## H2

把实现分为：完整前置校验、局部 Generator 初始化、连续 batch 切片、masked mean、
stable CE、backward、记录梯度证据、no-grad AdamW、返回 defensive copies。每个参数独立
维护 moment 与 step。

## H3

先让单个 full-batch step 的 loss、梯度和 AdamW 更新与手算/官方组件对齐，再套 epoch
与 batch 循环。Stable CE 可由 per-row max shift、LogSumExp 与目标 logits 组合；更新前
保存 grad norm，更新后把 `.grad` 设为 `None`，不要 detach 前向路径。
