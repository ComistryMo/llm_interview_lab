# PT-022 分级提示

## H1

先核对题面接口、归约轴、允许的 API；阅读题面末尾的技术来源。

## H2

对齐 `logits[:,:-1]` 与 `tokens[:,1:]`，mask 同样右移；只在回答 token 上求和。令 `margin=(logπ_c-logπ_r)-(logref_c-logref_r)`，loss=`softplus(-β*margin)`。参考 log-prob 停止梯度。标准序列 DPO 不擅自把求和换成长度平均；那会改变优化对象。

## H3

先实现最小非退化输入，再补状态和边界。策略等于参考时 loss=`log(2)`；增大 chosen 相对优势应降低 loss；同时给 chosen/rejected 的策略 log-prob 加同一个常数不改变 loss。completion 不包含 prompt/padding，是否包含 EOS 要由数据契约固定；本题包含真实回答终止 EOS，排除 padding。空回答监督报错。

## 口述追问

reference 是旧策略还是固定参考模型？chosen 更长时，sum 和 mean 各自改变了什么？定义参考 [DPO 原论文 §4 与附录 B](https://arxiv.org/html/2305.18290v3)。

## 复测方向

D+2：关闭旧作答，改成显式状态/批次输入，重新独立实现。D+7：用本题最容易混淆的定义设计一个反例，再验证原实现。当前未提供已验证的独立复测资产，不据此自动授予 retention。
