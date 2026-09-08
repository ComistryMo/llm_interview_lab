# INF-013 · LoRA 线性层与合并一致性

资料映射：AI06。这是原创训练任务，不代表某公司必考题。

推荐准备：[NNL-001](../NNL-001-linear/task.md)。推荐顺序不等于硬解锁条件；实际解锁条件见课程入口。

## 接口

```python
def lora_forward(x, weight, bias, a, b, alpha=1.0): ...
def merge_lora(weight, a, b, alpha=1.0): ...
```

## 题目要求

- weight[out,in] 和可选 bias[out] 冻结，A[r,in]、B[out,r] 可训练
- X[...,in]。输出 XWᵀ+bias+(alpha/r)*(XAᵀ)Bᵀ，r>0。实现 merge_lora(weight,a,b,alpha=1) 返回独立合并权重，绝不原地修改 W 或累计合并
- 无 dropout/量化。即使 W/bias requires_grad=True，也必须停止其梯度。初始化 B=0 时与基础层一致，A 初始梯度可为 0。O(in*out+r(in+out)) 每 token。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。张量位于同一设备；浮点使用 float32/float64，保持输出设备与明确的梯度路径；禁止直接调用题目要求手写的整层/算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- B 零初始化时 A 的梯度为零，是否证明计算图断开？
- 为什么 A、B 同时为零不利于学习？
- 重复 merge 怎样避免累积同一更新？
- 量化或 dropout 存在时合并等价性需要什么条件？

## 来源

- [技术定义 1](https://github.com/microsoft/LoRA)
- [技术定义 2](https://github.com/microsoft/LoRA/blob/main/loralib/layers.py)
