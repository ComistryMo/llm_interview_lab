# TOK-001 · 带确定性 tie-break 的最小 BPE

资料映射：AI19。这是原创训练任务，不代表某公司必考题。

推荐准备：[FND-002](../FND-002-sample-contract-validation/task.md)。推荐顺序不等于硬解锁条件；实际解锁条件见课程入口。

## 接口

```python
def train_bpe(vocab, num_merges): ...
def encode_bpe(tokens, merges): ...
```

## 题目要求

- vocab 是 {tuple[str,...]: 正整数词频}，允许空 tuple
- num_merges≥0。返回 (merges, encoded_vocab)：merges 是依次合并的字符串 pair 列表，encoded_vocab 为合并后的词频字典（碰撞需累加）。每轮统计相邻 pair 的加权次数，同分按 pair 字典序
- 从左向右非重叠合并，没 pair 时终止。同时实现 encode_bpe(tokens, merges)→tuple，推理按训练得到的 merge 次序，不重新统计。例 aaaa 一轮变 (aa,aa)，不是 aaa+a。全扫描约 O(MN)，不要求 byte-level 或工业 tokenizer。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。使用 Python 标准库，不依赖额外机器学习库。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- aaaa 的 pair 出现次数与一次实际合并次数为何不同？
- 推理时为什么不能重新用测试输入词频训练 merges？
- word frequency 与 tie-break 如何保证可重复？
- byte-level 编码能覆盖未见 Unicode 字符的什么部分？

## 来源

- [技术定义 1](https://huggingface.co/learn/llm-course/en/chapter6/5)
