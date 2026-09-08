# PT-003 分级提示

## H1

先核对题面接口、归约轴、允许的 API；阅读题面末尾的技术来源。

## H2

先每行减去最大 logit，再计算 `logsumexp(centered_logits)-centered_target_logit`，忽略位置置零后求和，分母为有效标签数量。这样还避免 `logsumexp` 加回巨大公共偏置后再相减造成的消减误差。FP16/BF16 转 FP32 做指数和归约；FP64 测试保留 FP64。检查标签不能先把 `-100` 直接交给 `gather`。

## H3

先实现最小非退化输入，再补状态和边界。`[1000,1000]` 与 FP32 `[1e20,1e20]` 对任意合法标签的损失都应约等于 `log(2)`；在输入差异仍可表示的前提下，对所有类别同时加常数，损失不变；任意改变被忽略位置的有限 logits 不改变损失；全忽略返回零且反传梯度为零。随机小张量应与官方交叉熵的非空有效子集对齐。输入极端到 FP32 减法本身溢出时，升级 FP64 或拒绝，减最大值并不能解决所有有限精度问题。

## 口述追问

加类别权重后，`mean` 的分母还是 token 数吗？做 label smoothing 时，忽略位置和目标分布应如何处理？技术定义参考 [PyTorch CrossEntropyLoss](https://docs.pytorch.org/docs/stable/generated/torch.nn.CrossEntropyLoss.html)、[logsumexp](https://docs.pytorch.org/docs/stable/generated/torch.logsumexp.html)。

## 复测方向

D+2：关闭旧作答，改成显式状态/批次输入，重新独立实现。D+7：用本题最容易混淆的定义设计一个反例，再验证原实现。当前未提供已验证的独立复测资产，不据此自动授予 retention。
