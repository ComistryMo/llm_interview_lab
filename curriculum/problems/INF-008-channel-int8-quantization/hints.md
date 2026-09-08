# INF-008 分级提示

## H1

先核对题面接口、归约轴、允许的 API；阅读题面末尾的技术来源。

## H2

`scale=max(abs(W),axis=1)/127`；全零通道 scale 本题置 1。`q=clip(round(W/scale),-127,127)` 后转 int8；反量化 `q*scale`。规定舍入使用 ties-to-even，广播 scale 到 `[out,1]`。这是明确的教学量化器，不是 AWQ/GPTQ。[PyTorch per-channel 量化接口](https://docs.pytorch.org/docs/2.8/generated/torch.quantize_per_channel.html)

## H3

先实现最小非退化输入，再补状态和边界。全零行返回全零；每行最大绝对值可映射到端点；正常有限精度下单个元素误差不超过约 scale/2；要先 clip 再转整数，不能依赖越界转换结果。

## 口述追问

改变一个输入规模或边界条件后，公式和复杂度是否仍成立？给出可复现的小例子。

## 复测方向

D+2：关闭旧作答，改成显式状态/批次输入，重新独立实现。D+7：用本题最容易混淆的定义设计一个反例，再验证原实现。当前未提供已验证的独立复测资产，不据此自动授予 retention。
