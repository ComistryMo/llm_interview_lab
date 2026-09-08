# ATT-008 · 完整 Decoder Block：把组件真正接起来

资料映射：AI36。这是原创训练任务，不代表某公司必考题。

推荐准备：[ATT-019](../ATT-019-projected-masked-mha/task.md)、[ATT-021](../ATT-021-rope-position-offsets/task.md)、[NNL-005](../NNL-005-swiglu-ffn/task.md)、[NNL-008](../NNL-008-rmsnorm/task.md)。推荐顺序不等于硬解锁条件；实际解锁条件见课程入口。

## 接口

```python
def decoder_block(x, weights, num_heads, position_ids, cache=None, eps=1e-5, base=10000.0): ...
```

## 题目要求

- X[B,T,E]，E/num_heads 为正偶数。weights 字典：norm1/norm2[E]，wq/wk/wv/wo[E,E]（out,in），w_gate/w_up[Hff,E]、w_down[E,Hff]，无 bias。执行两条 Pre-RMSNorm 残差：H=X+MHA(RMSNorm1(X))，Y=H+SwiGLU(RMSNorm2(H))。Q/K 用相邻配对 RoPE，position_ids[B,T] 是本块真实绝对位置
- causal mask
- 无 dropout。返回 (Y, (cached_rotated_K,cached_V))，cache 可为 None 或 [B,H,P,D] 历史
- 历史 K 不能二次旋转。允许重用自己已完成的原始算子代码，禁止 Transformer/MHA/SDPA 库层，不依赖其他 learner submission。零 wo、w_down 时整体恒等。O(BTE²+BHT²D+BTEHff)
- 缓存推理按 P+T 计。LayerNorm/GELU 与非因果 encoder 是口述迁移，不能暗中切换本题公式。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。张量位于同一设备；浮点使用 float32/float64，保持输出设备与明确的梯度路径；禁止直接调用题目要求手写的整层/算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 两次 norm 参数为何必须独立？
- 输出投影为零时残差 block 应退化成什么？
- 缓存中的 RoPE K 二次旋转如何破坏增量一致性？
- 换成 LayerNorm/GELU 或 encoder 时需要明确哪些契约变化？

## 来源

- [技术定义 1](https://github.com/meta-llama/llama3/blob/main/llama/model.py)
