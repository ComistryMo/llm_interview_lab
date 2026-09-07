# LOSS-002 · 标签平滑交叉熵

## 任务

手写带 ignore_index 的标签平滑交叉熵。模型的 logits 还未经过 softmax；平滑目标是在硬标签与**所有 C 类均匀分布**之间混合，不是只分配给错误类别。

## 接口

```python
def label_smoothed_cross_entropy(logits, targets, smoothing, ignore_index=-100):
    """返回对有效样本取平均的标量 Tensor。"""
```

- logits：(B,C)，B>=1、C>=2，有限 float32/float64；targets：(B,) int64，同一 device。
- targets 为 [0,C) 内类别或 ignore_index。smoothing 为有限实数，0<=smoothing<=1，不接受 bool；ignore_index 为整数且不能是 bool。
- 平滑目标 q=(1-smoothing)*one_hot(target)+smoothing/C。结果是有效样本交叉熵的均值。
- 被忽略样本既不影响分子也不影响分母，梯度为零。**全部忽略时返回可反向传播的零**（本项目明确约定，不同于直接调用 PyTorch mean reduction 可能得到 NaN）。
- 保留 logits 的梯度、dtype/device；不修改输入。
- 非法形状、标签、类型或非有限值抛 ValueError。
- 可用 logsumexp 和基本 Tensor 运算；禁止调用 cross_entropy、nll_loss、CrossEntropyLoss、NLLLoss。

## 示例

logits 为 2×3 全零，targets=[2,-100]，smoothing=0.1：返回 log(3)≈1.0986123。
第二个样本不参与平均。在 logits 每行都加上同一个常数后，结果不变。

## 验证与复杂度

时间 O(BC)，额外空间不超过 O(BC)。注意大 logits 的数值稳定性。
运行：`llm-lab test LOSS-002 --profile <id>`。

## 口述追问

1. epsilon 的质量是分给 C 类还是 C-1 类？两种定义为何不能混用？
2. ignore_index 的样本应在什么时候排除？
3. 为什么不能用 batch_size 固定除法处理忽略标签？
4. 平滑到 1 是否意味着任意预测都产生相同损失？用一个反例解释。

## 来源与边界

定义参考 [PyTorch CrossEntropyLoss](https://docs.pytorch.org/docs/stable/generated/torch.nn.CrossEntropyLoss.html)；本题接口、样例和测试原创。未提供参考实现；D+2/D+7 尚未上线。
