# ATT-003 · 因果与填充掩码：从训练到解码

## 任务

为 MHA / GQA 构造可广播的布尔掩码。重点是 **True 表示允许关注**、padding 的语义，以及带 KV Cache 时 query 与 key 的位置不同，不能简单画一个左上角三角形。

## 接口

```python
def causal_padding_mask(query_positions, key_positions, query_valid, key_valid):
    """返回 (B,1,Q,K) 的 bool Tensor。"""
```

- query_positions：(Q,)；key_positions：(K,)，均为 int64、非负绝对位置；Q、K>=1。
- query_valid：(B,Q)，key_valid：(B,K)，B>=1，均为 bool；True 表示非 padding。
- 四个 Tensor 必须位于同一 device；返回结果也在该 device。
- 一个位置允许关注，当且仅当 query 和 key 均有效，且 key 的绝对位置不晚于 query。
- 无效 query 对应全 False 行；全 padding 的样本也返回全 False。**本函数不计算 attention / softmax**；调用方需要自己定义全屏蔽行的数值处理。
- 不修改输入；形状、dtype、负位置或 device 不一致抛 ValueError。
- 可以比较和广播 Tensor，禁止 torch.tril / torch.triu（它们不能代替绝对位置语义）。

## 示例

query_positions=[2,3]，key_positions=[0,1,2,3]；
query_valid=[[True,True]]，key_valid=[[True,False,True,True]]。

返回形状 (1,1,2,4)，两行为：

```text
True  False True  False
True  False True  True
```

## 验证与复杂度

时间/输出空间 O(BQK)。用 batch、非连续输入、左 padding、增量解码与全屏蔽行检查实现。
运行：`llm-lab test ATT-003 --profile <id>`。

## 口述追问

1. 为什么输出中 head 维是 1，而不是实际 head 数？
2. KV Cache 中 Q=1、K>1 时，简单使用左上三角会错在哪里？
3. 布尔 mask 在不同 attention API 中是否含义一致？
4. 全屏蔽行直接做负无穷 softmax 会怎样？本函数与调用者各负责什么？

## 来源与边界

参考 [PyTorch scaled_dot_product_attention](https://docs.pytorch.org/docs/stable/generated/torch.nn.functional.scaled_dot_product_attention.html) 的可见性约定；接口、示例、测试原创。不是 MHA 完整实现的复制题，也不是性能优化 Kernel。D+2/D+7 尚未上线。
