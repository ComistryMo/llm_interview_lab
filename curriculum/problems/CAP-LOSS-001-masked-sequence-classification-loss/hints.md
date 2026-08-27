# 分级提示

## H1

分别核对最大有效位置的定义、矩阵乘法 Shape，以及 Cross Entropy 的 max-shift
恒等式。先写出每个中间 Tensor 的 Shape，不要从循环开始。

## H2

用位置序列与 boolean Mask 构造每行最大有效下标；沿序列轴 gather 一行 hidden。
对 logits 每行减去一个不改变 Softmax 的常数，再组合 LogSumExp 与目标类别值。

## H3

按“完整契约校验 → 最大有效 index → batch gather → affine → stable logsumexp →
目标类别 gather → mean → argmax”分段实现。校验必须先于任何可能产生部分结果的操作，
不要将 selected states 或 logits 转成 Python 数值。
