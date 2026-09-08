# LOSS-004 分级提示

## H1

先核对题面接口、归约轴、允许的 API；阅读题面末尾的技术来源。

## H2

FP32 中计算 `log_p=log_softmax(teacher.detach()/τ)`、`log_q=log_softmax(student/τ)`，逐 token 先沿词表求 `sum(exp(log_p)*(log_p-log_q))`，再应用 mask，最后除以 mask 的总和。τ² 是本题采用的蒸馏缩放约定，不是 KL 的数学定义本身。

## H3

先实现最小非退化输入，再补状态和边界。两组 logits 相同，KL≈0；交换 teacher/student 一般改变数值；增加 padding 不改变结果；teacher 梯度为空，student 梯度有限。若 `[B,T,V]` 直接调用 `batchmean`，只按 B 除，通常不等于有效 token 平均。top-k 截断后重归一化定义了另一种目标，不能称为全词表 KL 的无损替代。

## 口述追问

token 来自 student rollout 就自动保证 on-policy 吗？不同 tokenizer 的 teacher 能直接做逐 token KL 吗？接口与温度原则参考 [PyTorch KLDivLoss](https://docs.pytorch.org/docs/stable/generated/torch.nn.KLDivLoss.html)、[Distilling the Knowledge in a Neural Network](https://arxiv.org/abs/1503.02531)。

## 复测方向

D+2：关闭旧作答，改成显式状态/批次输入，重新独立实现。D+7：用本题最容易混淆的定义设计一个反例，再验证原实现。当前未提供已验证的独立复测资产，不据此自动授予 retention。
