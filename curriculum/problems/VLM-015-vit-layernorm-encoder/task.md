# VLM-015 · ViT Transformer Block：双向注意力与 GELU

资料映射：题目.md 第 27 项。图片未提供；本题固定无 dropout 的 ViT encoder 训练变体，精确 GELU 由题面指定。

## 接口

~~~python
def vit_block(x, weights, num_heads, valid_tokens=None, eps=1e-6): ...
~~~

## 题目要求

- x[B,T,E]，B、T、E、头数 H 为正且 E 能被 H 整除。weights 的矩阵按 [out,in]：wqkv[3E,E]、bqkv[3E]；wo[E,E]、bo[E]；w1[F,E]、b1[F]；w2[E,F]、b2[E]，F 为任意正整数。ln1_weight/ln1_bias/ln2_weight/ln2_bias 各 [E]。
- U=LayerNorm1(x)，按 Q、K、V 顺序投影/分头，按 sqrt(E/H) 缩放做双向 self-attention；合头经 wo、bo 得 A。h=x+A；输出 y=h+Linear2(GELU(Linear1(LayerNorm2(h))))。
- 两个 LayerNorm 都在最后轴减均值，使用总体方差与 eps。GELU 固定精确形式 0.5*z*(1+erf(z/sqrt(2)))。无 causal mask、KV cache、RoPE、dropout 或额外最终 LayerNorm。
- valid_tokens 是 None 或 bool[B,T]，True 表示该位置可以作为 key/value。仅屏蔽 key/value，不强制把 query/残差/MLP 清零。某 batch 所有 key 都被屏蔽时，该 batch 的 A 必须为零（包括输出 bias），前向、反向均须有限；后续残差与 MLP 照常执行。
- 返回 y[B,T,E]。非法 x/头数、mask shape/dtype、eps（有限正数）抛 ValueError；权重键/形状保证合法。输入与权重均保留梯度，不原地修改。
- 允许基础矩阵乘、softmax、erf、均值/方差；手写 LayerNorm、GELU、attention，禁止对应整层/SDPA API。时间 O(BTE²+BHT²D+BTEF)，attention 主存储 O(BHT²)。
- 推荐准备 VLM-001、NNL-006、ATT-019。x 已是 patch/CLS 加位置后的 token；本题补完整 encoder，VLM-001 只覆盖 patch projection。ATT-008 的因果 RMSNorm/SwiGLU decoder 不能代替本契约。

## 共同约定

输入不得被原地修改。除题面明确的异常外，输入形状合法、数值有限，不要求防御任意恶意输入。PyTorch 浮点输入同 dtype、同 device，支持 float32/float64 及非连续张量，保留输出设备和梯度。NumPy 题使用 float64，不使用 autograd。公开测试通过只是实现证据，不代表 mastered。

## 验收与复盘

解释接口、正常/边界/异常、输入突变和时间/空间复杂度；PyTorch 题补充 shape、dtype、device、数值稳定及梯度。H4/H5 后须另做新的无帮助变式，本题没有新增已验证的 D+2/D+7 资产。

## 口述与追问

- 为何后面 patch 的变化应能影响前面 token，怎样反证误加 causal mask？
- key padding mask 是否自动让 padding query 输出为零？
- Pre-LayerNorm 的残差路径在常量平移下有什么性质？
- patch embedding、CLS、位置编码、block 与最后的 encoder norm 分别属于哪一层？

## 来源

- [Google Vision Transformer 官方 encoder 结构](https://github.com/google-research/vision_transformer/blob/main/vit_jax/models_vit.py)
- [An Image is Worth 16x16 Words](https://arxiv.org/abs/2010.11929)
