# NNL-018 · D+7 候选：共享词嵌入与输出投影的 VJP

**待审资产，尚未开放为正式复测。** NumPy 手写梯度；不调用 autograd。

```python
def shared_embedding_projection_vjp(token_ids: np.ndarray, hidden: np.ndarray,
                                    weight: np.ndarray, grad_embeddings: np.ndarray,
                                    grad_logits: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ...
```

同一参数 `weight:[V,D]` 有两个用途：`embeddings = weight[token_ids]` 与 `logits = hidden @ weight.T`。已给出两路上游梯度，返回 `(grad_hidden, grad_weight)`。**hidden 是独立输入，不是本题 embeddings 的后续计算结果**，不要臆造第三条链路。

## 明确契约

- token_ids 为 int64 ndarray，至少一维，shape 可以与 hidden 的 leading shape 不同；每个 ID 满足 `0 <= id < V`，允许重复 ID。所有浮点数组为有限 float64 ndarray。
- weight 必须二维，V/D 为正。hidden 至少一维且尾维 D；grad_logits 的 shape 必须等于 `hidden.shape[:-1] + (V,)`；grad_embeddings 必须等于 `token_ids.shape + (D,)`。
- grad_weight 必须包含**两路**对共享参数的贡献。重复 token 每次出现都贡献梯度，不去重、不按出现次数缩放；没有 padding 特例。
- 对样本位置求和，不进行 loss 平均。输出分别为 hidden.shape、weight.shape，float64，不修改输入，不与输入共享可写存储。
- 支持空 token 数组、零长度 hidden batch、独立向量 hidden 和不连续视图。ID 越界或 shape 不满足上述要求抛 `ValueError`。
- 时间目标为 `O(H×D×V + E×D)`，H/E 分别为 hidden/token 位置总数。禁止生成 E×V 的 one-hot；只需返回梯度及大小可解释的临时量。

## 示例

weight=`[[1.,2.],[3.,4.]]`，token_ids=`[1,1]`，hidden=`[[2.,-1.]]`；grad_embeddings=`[[1.,0.],[2.,1.]]`，grad_logits=`[[.5,1.]]`。
应返回 grad_hidden=`[[3.5,5.]]`，grad_weight=`[[1.,-.5],[5.,0.]]`。其中重复 ID 的两次贡献不能相互覆盖。

## 口述与迁移

与不共享参数相比为何要合并两条梯度路径？如果 hidden 实际来自某个 embedding 网络，还缺什么信息才能继续链式求导？重复 ID 很多时，普通高级索引的原位加法可靠吗？如何用有限差分构造标量目标验证两路，而不是只测其中一路？若新增 padding_idx 或 scale_grad_by_freq，应分别改哪一条契约，为什么本题不能擅自启用？
