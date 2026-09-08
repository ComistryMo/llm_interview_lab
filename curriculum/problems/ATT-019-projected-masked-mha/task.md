# ATT-019 · 多头注意力与复合 mask

资料映射：AI02。这是原创训练任务，不代表某公司必考题。

推荐准备：[ATT-004](../ATT-004-multi-head-attention/task.md)、[NNL-001](../NNL-001-linear/task.md)。推荐顺序不等于硬解锁条件；实际解锁条件见课程入口。

## 接口

```python
def projected_mha(query_input, context, wq, wk, wv, wo, num_heads, allowed=None): ...
```

## 题目要求

- query_input[B,L,E]、context[B,S,E]
- 四个无 bias 权重 [E,E] 按 [out,in] 存储，E 能被 num_heads 整除。自行完成 Q/K/V 投影、分头、按 sqrt(E/H) 缩放的 attention、合头、输出投影
- 返回 [B,L,E]。allowed 是可广播到 [B,H,L,S] 的 bool，True=可访问
- 完全屏蔽的 query 输出 0，包含输出投影后仍为 0。causal 与 padding 由调用方组合为 allowed。禁止 MHA/SDPA。此题比 ATT-004 增加真实投影，并支持 L≠S 的 cross-attention
- O(BHLSd+BE²(L+S))。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。张量位于同一设备；浮点使用 float32/float64，保持输出设备与明确的梯度路径；禁止直接调用题目要求手写的整层/算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- cross-attention 的 Q 与 KV 不同长时，每一步 shape 是什么？
- 完全屏蔽的 query 如何避免 NaN 和输出投影后的残留？
- SDPA 与 key_padding_mask 的 bool 语义有什么不同？
- causal 和 padding 组合后，如何设计一个信息隔离的反例？

## 来源

- [技术定义 1](https://docs.pytorch.org/docs/stable/generated/torch.nn.functional.scaled_dot_product_attention.html)
