# ATT-020 · GQA 与 KV cache：增量解码一致性

资料映射：AI03。这是原创训练任务，不代表某公司必考题。

推荐准备：[ATT-006](../ATT-006-grouped-query-attention/task.md)、[ATT-009](../ATT-009-kv-cache/task.md)。推荐顺序不等于硬解锁条件；实际解锁条件见课程入口。

## 接口

```python
def cached_gqa(query, key, value, cache=None): ...
```

## 题目要求

- 已投影 query[B,Hq,L,D]、新 key/value[B,Hkv,L,D]，Hq%Hkv=0
- cache=None 或 (past_k,past_v)，历史 [B,Hkv,P,D]。等长无 padding 基础版，返回 (output[B,Hq,L,D], (new_k,new_v))，新缓存长 P+L 且只存 Hkv 个头。连续 Hq/Hkv 个 Q 头共享同一 KV 头
- 当前 query 绝对位置 P+i，允许 key≤P+i。缓存中的 K 视作已完成一次位置旋转，不要再旋转。允许教学版拼接，但不修改旧缓存
- 禁止 MHA/SDPA。全量、单 token、[3,1,3] 分块结果须一致
- 复杂度 O(BHqL(P+L)D)。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。张量位于同一设备；浮点使用 float32/float64，保持输出设备与明确的梯度路径；禁止直接调用题目要求手写的整层/算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 单 token 解码为什么不能直接用左上对齐的 tril？
- GQA 减少 KV 存储，为什么不等于总计算降低相同倍数？
- RoPE 后的历史 K 为什么不能再次旋转？
- batch 内位置不同或 beam 重排时需要保存什么状态？

## 来源

- [技术定义 1](https://arxiv.org/html/2305.13245v3#S2.SS2)
