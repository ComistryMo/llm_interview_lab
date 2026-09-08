# PT-024 分级提示

## H1

先核对题面接口、归约轴、允许的 API；阅读题面末尾的技术来源。

## H2

`allowed[i,j]=(segment_i==segment_j) and (position_j<=position_i)`，叠加有效 token 约束。损失位置 i 仅在 i 与 i+1 同段、且目标 token i+1 应被监督时有效；因此边界需同时影响 attention 与 label。段内 position 从零开始，并不自动令任意模型实现注意力隔离。

## H3

先实现最小非退化输入，再补状态和边界。A 长 2、B 长 3 时，允许矩阵应包含互不连通的 2×2、3×3 下三角块。任意改变 A 的内容，不应改变 B 的输出或有效 token loss；分别训练与 packing 训练应按同一 token 权重近似一致。仅插入 EOS 不是硬隔离。

## 口述追问

只设置 labels=-100，信息泄漏是否解决？含卷积或线性注意力的模型，重置 position_ids 是否足够？当前实现边界参考 [Transformers Padding-free training](https://huggingface.co/docs/transformers/en/padding_free)。

## 复测方向

D+2：关闭旧作答，改成显式状态/批次输入，重新独立实现。D+7：用本题最容易混淆的定义设计一个反例，再验证原实现。当前未提供已验证的独立复测资产，不据此自动授予 retention。
