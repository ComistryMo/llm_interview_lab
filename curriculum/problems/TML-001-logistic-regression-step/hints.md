# TML-001 分级提示

## H1

先核对题面接口、归约轴、允许的 API；阅读题面末尾的技术来源。

## H2

`z=X@w+b`；每样本损失用 `max(z,0)-y*z+log1p(exp(-abs(z)))`，避免先算概率再取 log。`dw=X.T@(sigmoid(z)-y)/N+lambda*w`，`db=mean(sigmoid(z)-y)`。sigmoid 用按正负分支的稳定实现。[scikit-learn：逻辑回归目标](https://scikit-learn.org/stable/modules/linear_model.html#logistic-regression)

## H3

先实现最小非退化输入，再补状态和边界。`z=0` 时数据损失 `log(2)`；`z=1000,y=1` 时损失趋近 0，`z=1000,y=0` 时约为 1000；有限差分与解析梯度相符。做实现对照时固定正则系数、损失归约和 bias 规则，不能仅比较参数名称。

## 口述追问

改变一个输入规模或边界条件后，公式和复杂度是否仍成立？给出可复现的小例子。

## 复测方向

D+2：关闭旧作答，改成显式状态/批次输入，重新独立实现。D+7：用本题最容易混淆的定义设计一个反例，再验证原实现。当前未提供已验证的独立复测资产，不据此自动授予 retention。
