# ATT-024 · GPT-2 Block：LayerNorm、GELU 与因果缓存

资料映射：题目.md 第 37 项。图片未提供，本题固定 GPT-2 风格 block 的原创函数式接口，未复原图片代码。

## 接口

~~~python
def gpt2_block(x, weights, num_heads, cache=None, eps=1e-5): ...
~~~

## 题目要求

- x[B,T,E]，B、T、E、num_heads 为正，E 能被头数 H 整除，D=E/H。weights 中矩阵均按 [out,in] 存储：wqkv[3E,E]、bqkv[3E]；wo[E,E]、bo[E]；w1[4E,E]、b1[4E]；w2[E,4E]、b2[E]；ln1_weight/ln1_bias/ln2_weight/ln2_bias 各 [E]。
- 先 U=LayerNorm1(x)，由 U 一次投影并按 Q、K、V 顺序拆分。每头按 sqrt(D) 缩放做因果 self-attention，经 wo、bo 投影后得到 A，令 h=x+A。
- 再 z=LayerNorm2(h)，y=h+Linear2(GELU(Linear1(z)))。LayerNorm 在最后轴减均值，使用总体方差与 eps；GELU 固定 0.5*z*(1+tanh(sqrt(2/pi)*(z+0.044715*z**3)))。
- x 已含调用者添加的绝对位置 embedding；block 不添加位置、不用 RoPE、无 dropout、无额外最终 LayerNorm。对应 ATT-008 的 RMSNorm/SwiGLU 是另一架构契约。
- 返回 (y,(all_k,all_v))；cache 是 None 或一对 [B,H,P,D]，返回缓存长 P+T。query t 仅可访问 cache 全部 P 项及当前块 0..t 项。历史 K/V 不重复投影；不得修改、detach 或覆盖输入与旧缓存，保留所有浮点输入的梯度。
- 非法头数、x 形状、eps（需有限正数）、cache shape/dtype/device 抛 ValueError；weights 的键与形状保证满足以上约定。
- 允许基础矩阵乘、softmax、tanh、均值/方差；须手写 norm、GELU 与 attention，禁止现成 Transformer/MHA/SDPA/LayerNorm/GELU。时间 O(BTE²+BHT(P+T)D)，主要 attention 存储 O(BHT(P+T))，缓存 O(BH(P+T)D)。推荐准备 NNL-006、ATT-019、ATT-020；推荐顺序不增加硬前置。

## 共同约定

输入不得被原地修改。除题面明确的异常外，输入形状合法、数值有限，不要求防御任意恶意输入。PyTorch 浮点输入同 dtype、同 device，支持 float32/float64 及非连续张量，保留输出设备和梯度。NumPy 题使用 float64，不使用 autograd。公开测试通过只是实现证据，不代表 mastered。

## 验收与复盘

解释接口、正常/边界/异常、输入突变和时间/空间复杂度；PyTorch 题补充 shape、dtype、device、数值稳定及梯度。H4/H5 后须另做新的无帮助变式，本题没有新增已验证的 D+2/D+7 资产。

## 口述与追问

- 为什么两次 LayerNorm 的参数必须独立，且必须减去均值？
- GPT-2 的位置向量应在哪加入，为什么不能在缓存 K 上额外施加 RoPE？
- 多 token chunk 接在 cache 后面时，因果对角线偏移是多少？
- tanh-GELU、精确 GELU 与 SwiGLU 会改变哪些数值或形状？

## 来源

- [OpenAI GPT-2 原始 block、norm、gelu 定义](https://github.com/openai/gpt-2/blob/master/src/model.py)
