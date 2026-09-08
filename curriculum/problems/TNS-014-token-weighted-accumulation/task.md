# TNS-014 · 可变长度序列的梯度累积

资料映射：AI15。这是原创训练任务，不代表某公司必考题。

推荐准备：[TNS-013](../TNS-013-autograd-detach-no-grad/task.md)、[LOSS-014](../LOSS-014-cross-entropy/task.md)。推荐顺序不等于硬解锁条件；实际解锁条件见课程入口。

## 接口

```python
def accumulate_token_gradients(loss_factories, token_counts, global_token_count=None, world_size=1): ...
```

## 题目要求

- loss_factories 是按顺序调用的零参数函数列表，每个返回当前 microbatch 的可反传 token loss 总和 S_i
- token_counts 为对应非负有效数 n_i。在每个回调后立即 backward，再处理下个，返回本 rank 的归一化 loss 浮点数，不调用优化器、调度器或清零旧梯度。单进程目标 ΣS_i/Σn_i。global_token_count 若给出则为所有 rank 窗口的有效总数 N，DDP 梯度默认平均时，各 rank 反传 world_size*S_i/N
- 返回值仍为 ΣS_i/N。N=0 不调用回调、不反传、不更新任何状态，返回 0。仅 n_i=0 的回调跳过。计数和回调长度不匹配或负计数抛 ValueError。调用方在窗口前清零，窗口后 unscale/裁剪/step。额外保留一份 microbatch 图，不保留所有激活。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。张量位于同一设备；浮点使用 float32/float64，保持输出设备与明确的梯度路径；禁止直接调用题目要求手写的整层/算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 不等长 microbatch 的 loss 均值能直接平均吗？
- DDP 默认平均梯度时，全局 token 分母如何补偿？
- 为什么裁剪应在累计与 unscale 后进行？
- 空窗口为什么也不能触发 weight decay 或 scheduler？

## 来源

- [技术定义 1](https://huggingface.co/blog/gradient_accumulation)
- [技术定义 2](https://huggingface.co/docs/accelerate/en/usage_guides/gradient_accumulation)
