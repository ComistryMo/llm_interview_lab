# VLM-015 分级提示

## H1 · 官方文档 / 单一语法

查看 bool key mask 的广播轴、torch.erf 的定义。

## H2 · 概念方向

ViT token 可以双向通信。mask 只控制哪些 key/value 可见；query 的残差仍然存在。

## H3 · 结构步骤

先画出两条 Pre-LayerNorm 残差；分开验证 attention 与 MLP 的退化情况，再加入 key padding 与全屏蔽行，最后检查未来 token 的影响及全部梯度。

## 复测方向

更换 padding query 处理方式时先重写契约，再独立实现。尚无独立已验证 D+2/D+7 资产；H4/H5 后须新的无帮助变式。
