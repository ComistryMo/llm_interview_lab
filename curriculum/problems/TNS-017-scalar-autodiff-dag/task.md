# TNS-017 · 最小标量自动微分引擎

资料映射：AI40。这是原创训练任务，不代表某公司必考题。

推荐准备：[TML-006](../TML-006-numpy-mlp-backprop/task.md)。推荐顺序不等于硬解锁条件；实际解锁条件见课程入口。

## 接口

```python
class Value:
    def __init__(self, data): ...
    def __add__(self, other): ...
    def __radd__(self, other): ...
    def __mul__(self, other): ...
    def __rmul__(self, other): ...
    def tanh(self): ...
    def backward(self): ...
```

## 题目要求

- 实现 Value(data)，字段 data 与 grad 为标量。支持 Value/数值的 +、*（含反向运算）、tanh() 与 backward()。局部反传必须累加共享节点贡献
- 每次 backward 前清零本输出可达的所有节点，再把本输出梯度设 1。禁止 autograd/数值差分实现主体。输出依赖图不是树，拓扑节点去重但边的贡献不能去重。例 x=3，y=x*x+x，y.backward() 后 x.grad=7
- 重复 backward 仍是 7。O(V+E)。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。使用 Python 标准库，不依赖额外机器学习库。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- 为什么共享子图不能按树递归重复反传？
- 同一父节点出现两次，拓扑去重会不会丢失两条边的贡献？
- 重复 backward 的清零语义与累加语义有什么区别？
- 扩展到张量时广播梯度需要哪些额外归约？

## 来源

- [技术定义 1](https://github.com/karpathy/micrograd)
