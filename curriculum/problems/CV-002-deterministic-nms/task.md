# CV-002 · IoU 与 NMS：坐标、同分和阈值都要写清

资料映射：AI26。这是原创训练任务，不代表某公司必考题。

## 接口

```python
def nms(boxes, scores, threshold=0.5): ...
```

## 题目要求

- boxes[N,4] 是连续 xyxy 坐标，x2≥x1,y2≥y1
- scores[N]。返回保留原下标的 int64 数组，按选择顺序排列。单类别 hard NMS，IoU 严格大于 threshold 才抑制，0≤threshold≤1
- 分数同分优先较小原下标
- 退化框 IoU=0
- 空 (0,4) 输入返回空。面积不加 1。最坏 O(N²) 时间、O(N) 辅助空间。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。NumPy 浮点验收采用 float64；禁止 PyTorch/autograd 或现成的目标算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 连续坐标面积是否要加 1？
- IoU 等于阈值时保留还是抑制？
- 不同类别可否直接互相执行 NMS？
- Soft-NMS 改分后为什么可能要重新确定顺序？

## 来源

- [技术定义 1](https://docs.pytorch.org/vision/stable/generated/torchvision.ops.nms.html)
