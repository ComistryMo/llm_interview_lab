# INF-008 · 按通道 INT8 量化与反量化

资料映射：AI33。这是原创训练任务，不代表某公司必考题。

## 接口

```python
def quantize_per_channel(weight): ...
```

## 题目要求

- weight[out,in] 为非空 float64，逐输出通道对称量化。返回 (q[int8,out,in], scale[out,1], reconstructed[out,in])。整数范围 [-127,127]，zero point=0
- scale=absmax/127，全零行 scale=1
- ties-to-even 舍入，先 clip 再转 int8。禁止现成量化 API
- O(out*in)。这不是 AWQ/GPTQ，也不承诺加速。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。NumPy 浮点验收采用 float64；禁止 PyTorch/autograd 或现成的目标算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 逐输出通道量化与整张量量化的误差分布有何区别？
- 全零通道为什么需要显式 scale 规则？
- ties-to-even 与输入浮点误差怎样影响临界值？
- 权重更小是否保证端到端推理更快？

## 来源

- [技术定义 1](https://docs.pytorch.org/docs/2.8/generated/torch.quantize_per_channel.html)
