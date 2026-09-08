# NNL-016 分级提示

## H1

先核对题面接口、归约轴、允许的 API；阅读题面末尾的技术来源。

## H2

每通道在 `N,H,W` 上统计。若对齐 PyTorch 的这一接口，训练前向用总体方差；更新 running variance 使用无偏估计。令每通道样本数 `M=NHW`，无偏方差为总体方差乘 `M/(M-1)`，基础题训练时要求 M>1。运行统计按 `(1-m)*old+m*current` 更新；eval 使用保存的统计，不再更新。[PyTorch BatchNorm2d](https://docs.pytorch.org/docs/2.8/generated/torch.nn.BatchNorm2d.html)

## H3

先实现最小非退化输入，再补状态和边界。手算一个通道的两个元素，分别检查本批归一化输出和 running variance；eval 中把同一个样本放入不同 batch，输出不应因同批其他样本变化；检查 gamma/beta 的广播轴。

## 口述追问

改变一个输入规模或边界条件后，公式和复杂度是否仍成立？给出可复现的小例子。

## 复测方向

D+2：关闭旧作答，改成显式状态/批次输入，重新独立实现。D+7：用本题最容易混淆的定义设计一个反例，再验证原实现。当前未提供已验证的独立复测资产，不据此自动授予 retention。
