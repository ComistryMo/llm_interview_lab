# VLM-001 · ViT Patch Embedding 与卷积等价性

资料映射：AI39。这是原创训练任务，不代表某公司必考题。

推荐准备：[NNL-009](../NNL-009-conv2d-cross-correlation/task.md)、[NNL-001](../NNL-001-linear/task.md)。推荐顺序不等于硬解锁条件；实际解锁条件见课程入口。

## 接口

```python
def patch_embedding(images, weight, bias, patch_size): ...
```

## 题目要求

- images[B,C,H,W]，H/W 都能被正整数 P=patch_size 整除
- weight[E,C*P*P]，bias[E]。按 patch 行→patch 列的顺序输出 [B,(H/P)*(W/P),E]
- 每个 patch 内按通道→像素行→像素列展开，做共享线性投影。不要将 reshape 当作任意 permute 的替代。禁止 conv2d/现成 patch 层
- 等价 Conv2d(kernel=P,stride=P,weight.reshape(E,C,P,P)) 后空间展平转置。O(BHWC E)，保持梯度。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。张量位于同一设备；浮点使用 float32/float64，保持输出设备与明确的梯度路径；禁止直接调用题目要求手写的整层/算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- patch 内通道和像素顺序如何对应卷积核？
- reshape 为什么不能随意替代 permute？
- 单位脉冲如何检查核方向和 patch 顺序？
- 图像尺寸不能整除 patch size 时应先明确什么策略？

## 来源

- [技术定义 1](https://docs.pytorch.org/docs/stable/generated/torch.nn.Conv2d.html)
