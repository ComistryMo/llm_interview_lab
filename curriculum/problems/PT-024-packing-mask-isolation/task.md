# PT-024 · Packing：attention 隔离与监督隔离是两件事

资料映射：AI12。这是原创训练任务，不代表某公司必考题。

推荐准备：[PT-001](../PT-001-sft-label-mask/task.md)、[ATT-003](../ATT-003-causal-padding-mask/task.md)。推荐顺序不等于硬解锁条件；实际解锁条件见课程入口。

## 接口

```python
def packing_masks(segment_ids, position_ids, supervised): ...
```

## 题目要求

- 一维 int64 segment_ids[T]、position_ids[T]，bool supervised[T]。非负 segment ID 标识独立样本，-1 为 padding
- 同段 position 从零递增。返回 (allowed[T,T], loss_mask[T])，均 bool。attention 只允许同段有效 token 且 key_position≤query_position
- loss_mask[i] 仅在 i/i+1 有效且同段、supervised[i+1] 为真时有效，最后一位永远 False。空输入返回空矩阵/向量。O(T²)。只重置位置或设置 labels=-100 不能替代双重隔离。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。张量位于同一设备；浮点使用 float32/float64，保持输出设备与明确的梯度路径；禁止直接调用题目要求手写的整层/算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 仅 labels=-100 能阻止跨样本 attention 吗？
- 为什么段尾 token 不能监督下一段开头？
- 重置 position_ids 是否对所有序列模型都实现隔离？
- packing 与分开训练的 loss 怎样保持同一权重口径？

## 来源

- [技术定义 1](https://huggingface.co/docs/transformers/en/padding_free)
