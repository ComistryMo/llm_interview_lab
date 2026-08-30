# PT-005 · Preference Pair Contract Validator

This is a small, synthetic data-contract exercise. The interface, examples, tests,
and hints are authored for this curriculum; the DPO and instruction-tuning papers
listed in the catalog motivate surrounding concepts but do not define this contract.

## 目标

在计算 DPO 或训练奖励模型之前，验证一条合成的偏好样本是否保留了清晰、可审计的
`prompt / chosen / rejected` 边界。函数只做数据契约检查，不判断哪一个回答“更好”。

## 接口

```python
from typing import Mapping

def validate_preference_pair(pair: Mapping[str, object]) -> dict[str, object]:
    """Return a deterministic, content-minimizing validation report."""
```

## 输入契约

- `pair` 必须是 `Mapping`；非映射对象抛出 `TypeError`。
- 必须包含 `prompt`、`chosen`、`rejected` 三个字段，且三者都必须是严格的 `str`（即 `type(value) is str`；不接受 `bool`、数字或 `str` 子类）。缺字段或类型错误抛出 `ValueError`。
- `prompt`、`chosen`、`rejected` 是语义字段：空白去除后为空时不抛异常，而是在报告中分别加入 `EMPTY_PROMPT`、`EMPTY_CHOSEN` 或 `EMPTY_REJECTED`。
- 可以提供 `pair_id`。若提供，必须是严格的 `str`，且去除首尾空白后非空；报告保留原始标识，不把它当作文本规范化的一部分。
- 可以提供 `metadata`。若提供，必须是 `Mapping`，键必须是严格 `str`；返回报告时要做浅拷贝，不能让调用者通过报告修改原映射。
- 可以提供 `truncation`，格式必须是只含 `chosen` 和 `rejected` 两个键的 `Mapping`，值必须是严格 `bool`。缺键、多余键或值类型错误都是 `ValueError`；两侧截断标记不一致时，这条样本语义上无效。
- 不认识的顶层字段不影响检查，但不能被函数原地修改或删除。

只有容器、字段存在性和运行时类型等契约错误抛出异常；可由内容判断的
语义无效样本都返回报告。这样调用方可以把坏样本计数并保留确定性的原因，
而不会把异常路径和样本质量混为一谈。

## 规范化与语义规则

比较文本时使用 `unicodedata.normalize("NFKC", text)`，再把连续的 Unicode
空白压缩成一个 ASCII 空格（等价于 `' '.join(value.split())`），最后
`casefold()`；报告只返回长度和标识，不回显回答正文。长度是该规范化
结果的 Unicode code-point 数量。

按以下固定顺序收集语义错误（同一错误只出现一次）：

1. `EMPTY_PROMPT`、`EMPTY_CHOSEN`、`EMPTY_REJECTED`；
2. `IDENTICAL_RESPONSES`：两个规范化后的回答都非空且相同；
3. `PROMPT_LEAKAGE`：规范化后的 prompt 和回答都非空，且回答等于 prompt，或以 `prompt + " "` 开头；
4. `ASYMMETRIC_TRUNCATION`：truncation 两侧一真一假。

语义错误不抛异常，而是返回 `valid: false` 的报告。报告至少包含：

```python
{
    "valid": bool,
    "errors": list[str],
    "pair_id": str | None,
    "lengths": {"prompt": int, "chosen": int, "rejected": int},
    "metadata": dict[str, object],
}
```

`errors` 顺序必须稳定；没有语义错误时为空列表。函数不得修改 `pair`、
嵌套 `metadata` 或任何文本对象。

## 验收

公开测试覆盖合法样本、严格类型、空字段、Unicode 等价回答、Prompt 泄漏、截断边界、
元数据隔离、确定性错误顺序和输入不变性。测试只通过统一 `submission` fixture 加载学习者实现，
不会导入 `starter.py`。

## 口述答辩

1. 为什么偏好验证应先于 DPO loss，而不是把坏样本交给 loss 再观察？
2. 为什么需要区分“结构/类型错误”和“语义上无效但可报告”的样本？
3. Unicode 规范化、大小写折叠和空白压缩各会带来什么误报风险？
4. 为什么截断两侧不对称会改变偏好标签的可比性？
5. 如何扩展到 annotator disagreement，同时避免把长度当作质量？
