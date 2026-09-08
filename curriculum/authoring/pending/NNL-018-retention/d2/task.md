# NNL-018 · D+2 候选：微批 Linear 梯度累积

**待审资产，尚未开放为正式复测。** 使用 NumPy 手写反向，不调用 autograd。

```python
def accumulate_linear_vjp(chunks: list[tuple[np.ndarray, np.ndarray]],
                          weight: np.ndarray) -> tuple[list[np.ndarray], np.ndarray, np.ndarray]:
    ...
```

`weight` 为 `[O, I]`；每个 chunk 包含 `x:[...,I]` 和上游 `grad_output:[...,O]`，表示 `y = x @ weight.T + b`。所有 chunk 共用同一组 weight 和 bias。返回按原顺序排列的各批 `grad_x`、汇总的 `grad_weight:[O,I]` 与 `grad_bias:[O]`。

## 明确契约

- 浮点输入是有限 `numpy.ndarray`，dtype 为 float64；`I,O > 0`。支持不连续视图、单向量及零长度 leading 维。
- 各 chunk 的 leading shape 可不同，但同一个 chunk 的 x 和 grad_output 的 leading shape 必须完全相同。不得广播掩盖 shape 不匹配。
- 每个批的参数梯度以及跨批梯度都按**和**累积；不额外除以批大小、token 数或 chunk 数。上游梯度可能已包含 loss 的归一化。
- 空 chunks 返回空列表与正确 shape 的全零参数梯度；空微批仍返回对应 shape 的空 grad_x。
- weight 非二维、I/O 非正、x/grad_output 维数或 shape 不符合要求时抛 `ValueError`。不要求支持其他容器或 dtype；不要为约定外输入新增规则。
- 不改变 chunks、weight、x 或 grad_output。输出 float64，与输入不共享可写存储。
- 不拼接整批激活。时间为 `O(总样本位置数 × I × O)`，除返回的 grad_x 外，累积状态为 `O(I×O + O)`。

## 示例

weight=`[[2., -1.]]`，单个 chunk 的 x=`[[1.,3.],[2.,5.]]`，grad_output=`[[.5],[1.5]]`。
结果为 grad_x 列表中的 `[[1.,-.5],[3.,-1.5]]`、grad_weight=`[[3.5,9.]]`、grad_bias=`[2.]`。

## 口述与变式

为什么已平均 loss 的梯度不能再平均一次？最后一个微批更短时会有什么问题？如何证明重新切分相同样本不会改变参数梯度？如果各 chunk 的 loss 权重不同，应由本函数还是上游表达？说明保存全部 grad_x 与仅保存累积状态的内存区别。
