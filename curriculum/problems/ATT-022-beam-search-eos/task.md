# ATT-022 · Beam Search：候选分数、EOS 与缓存重排

资料映射：AI29。这是原创训练任务，不代表某公司必考题。

## 接口

```python
def beam_search(step, beam_width, max_new_tokens, eos_id): ...
```

## 题目要求

- step(prefix_tuple) 返回词表顺序的 log-prob 序列，允许 -inf 禁用候选。前缀初始为 ()，beam_width≥1、max_new_tokens≥1。返回列表，每项 {tokens: tuple, score: float, finished: bool}。完成项占 beam 名额，EOS 后不得再调用 step
- 每轮按累计 log-prob 取最多 K 个，分数同分按 token tuple 字典序
- 所有保留项结束或达到上限才停止。无长度惩罚，未遇 EOS 的路径 finished=False。禁止现成生成框架。O(TKV log(KV))，不含 step。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。使用 Python 标准库，不依赖额外机器学习库。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 为什么累计 log-prob 不能换成每步概率求和？
- 完成路径是否继续占 beam 名额？
- 父 beam 重排后 KV cache 应如何重排？
- 增加长度惩罚后原来的早停规则还成立吗？

## 来源

- [技术定义 1](https://huggingface.co/docs/transformers/en/generation_strategies)
