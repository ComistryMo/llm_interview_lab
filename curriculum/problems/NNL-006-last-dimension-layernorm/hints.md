# NNL-006 分级提示

## H1

先核对题面接口、归约轴、允许的 API；阅读题面末尾的技术来源。

## H2

LayerNorm 计算 `μ=mean(x)`、`var=mean((x-μ)^2)`，输出 `gamma*(x-μ)/sqrt(var+eps)+beta`；RMSNorm 使用 `gamma*x/sqrt(mean(x²)+eps)`，本题无 beta。方差必须按 D 而不是 D−1 作分母；FP16/BF16 的平方与归约先升精度。

## H3

先实现最小非退化输入，再补状态和边界。全零、常量向量、D=1 都不应 NaN；LayerNorm 的常量输入输出 beta，而 RMSNorm 对非零常量一般不为零。随机输入逐项对齐官方实现，同时比较反向梯度；对比时统一 eps、参数 dtype 和计算精度，不能拿不同默认值作结论。

## 口述追问

RMSNorm 是否保证零均值？Pre-Norm 与 Post-Norm 改变的是归一化公式还是残差路径的位置？依据 [PyTorch LayerNorm](https://docs.pytorch.org/docs/stable/generated/torch.nn.LayerNorm.html)、[RMSNorm 原论文](https://arxiv.org/abs/1910.07467)。

## 复测方向

D+2：关闭旧作答，改成显式状态/批次输入，重新独立实现。D+7：用本题最容易混淆的定义设计一个反例，再验证原实现。当前未提供已验证的独立复测资产，不据此自动授予 retention。
