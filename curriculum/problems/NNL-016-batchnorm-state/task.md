# NNL-016 · BatchNorm：训练与推理两套统计量

资料映射：AI24。这是原创训练任务，不代表某公司必考题。

推荐准备：[NNL-006](../NNL-006-last-dimension-layernorm/task.md)。推荐顺序不等于硬解锁条件；实际解锁条件见课程入口。

## 接口

```python
def batch_norm(x, gamma, beta, running_mean, running_var, training=True, momentum=0.1, eps=1e-5): ...
```

## 题目要求

- X[N,C,H,W] 或 X[N,C]，参数和 running stats[C]。返回 (output, new_mean, new_var)，不原地改输入 running stats。训练前向用每通道总体方差，running variance 更新使用无偏方差 M/(M−1)，M=N*H*W（2D 时 M=N），训练 M>1。更新 (1-m)*old+m*batch_stat，新统计 detach。eval 使用输入 running stats、不更新、不依赖同批其他样本。0<m≤1，eps>0
- 保持参数/输入梯度。O(NCHW)，状态 O(C)。禁止 BatchNorm 库层。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。张量位于同一设备；浮点使用 float32/float64，保持输出设备与明确的梯度路径；禁止直接调用题目要求手写的整层/算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 训练归一化和 running variance 为什么使用不同方差估计？
- eval 输出应否依赖同批其他样本？
- 梯度累积会增加 BN 的统计 batch 吗？
- SyncBN 为什么不能只平均各卡的方差？

## 来源

- [技术定义 1](https://docs.pytorch.org/docs/2.8/generated/torch.nn.BatchNorm2d.html)
