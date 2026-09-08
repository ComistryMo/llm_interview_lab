# TNS-014 分级提示

## H1

先核对题面接口、归约轴、允许的 API；阅读题面末尾的技术来源。

## H2

先获得整个更新窗口的总有效 token 数 N；每个 microbatch 反传 `Sᵢ/N`，窗口结束只 step 一次。也可先累计未归一化的梯度，再统一除 N，之后裁剪梯度。DDP 默认对梯度跨 rank 平均时，若 N 为全局 token 总数，每个 rank 本地反传的缩放需包含 R，才能抵消该平均；若框架已自动缩放，不得再乘一次。

## H3

先实现最小非退化输入，再补状态和边界。n=[1,3]、各 microbatch token 平均 loss 为 [1,3]，正确总 loss=2.5，直接平均 microbatch loss 得2。相同线性模型和同一批 token，完整 batch 与不等长拆分后梯度近似一致。末尾不足 M 个 microbatch 的窗口也按实际 token 数归约；N=0 时跳过更新，不能触发 weight decay 或调度器步进。

## 口述追问

为什么梯度裁剪应在累计完成后？AMP 的 unscale 与按 N 归约的顺序如何安排？依据 [Hugging Face 梯度累积修复说明](https://huggingface.co/blog/gradient_accumulation)、[Accelerate 变长样本示例](https://huggingface.co/docs/accelerate/en/usage_guides/gradient_accumulation)。

## 复测方向

D+2：关闭旧作答，改成显式状态/批次输入，重新独立实现。D+7：用本题最容易混淆的定义设计一个反例，再验证原实现。当前未提供已验证的独立复测资产，不据此自动授予 retention。
