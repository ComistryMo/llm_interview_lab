# ATT-008 分级提示

## H1

先核对题面接口、归约轴、允许的 API；阅读题面末尾的技术来源。

## H2

`H=X+Attention(Norm1(X))`，`Y=H+FFN(Norm2(H))`。在 attention 内执行 Q/K/V 投影、Q/K 位置旋转、因果 mask、合头和输出投影；两次 norm 参数独立。首版不接 cache，第二版接入 AI03 并验证增量等价。该任务是教学组合，不承诺逐行复刻具体模型。[Meta Llama 3 作者实现](https://github.com/meta-llama/llama3/blob/main/llama/model.py)

## H3

先实现最小非退化输入，再补状态和边界。Attention 输出投影和 FFN down projection 都置零，整个 block 为恒等映射；修改未来位置不影响过去位置输出；同一输入完整前向与正确 cache 前向逐位置一致。检查最后一维与所有残差支路 shape。

## 口述追问

改变一个输入规模或边界条件后，公式和复杂度是否仍成立？给出可复现的小例子。

## 复测方向

D+2：关闭旧作答，改成显式状态/批次输入，重新独立实现。D+7：用本题最容易混淆的定义设计一个反例，再验证原实现。当前未提供已验证的独立复测资产，不据此自动授予 retention。
