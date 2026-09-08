# ATT-023 · MLA：联合 KV 压缩与解耦 RoPE 缓存

资料映射：题目.md 第 8 项。题名未提供公式；本题依据 MLA 公开数学机制固定训练接口，不复制模型实现，不声称完整复现生产 kernel。

## 接口

~~~python
def mla_attention(x, weights, num_heads, position_ids, cache=None, base=10000.0): ...
~~~

## 题目要求

- x[B,T,E]，B、T、E 和头数 H 为正。weights 全为无 bias、按 [out,in] 的矩阵：w_dkv[R,E]、w_uk[H*Dc,R]、w_uv[H*Dv,R]；w_dq[Rq,E]、w_uq[H*Dc,Rq]、w_qr[H*Dr,Rq]、w_kr[Dr,E]；wo[E,H*Dv]。R、Rq、Dc、Dv 为正，Dr 为正偶数。
- cKV=x@w_dkv.T；cQ=x@w_dq.T。content query 为 cQ@w_uq.T，content key/value 分别由 cKV@w_uk.T、cKV@w_uv.T 展开，按头分为 Dc/Dv 通道。
- rotary query 由 cQ@w_qr.T 分成 H 个 Dr 通道，rotary key 由 x@w_kr.T 生成并在所有头共享。仅这两路应用相邻偶奇配对 RoPE：第 i 对角度 position/base**(2i/Dr)，旋转 (a,b) 为 (a*cos-b*sin,a*sin+b*cos)。position_ids 为 torch.int32/int64 的非负整数 [B,T]，允许 batch 不同和有间隔的绝对位置。
- 每头 attention logits 是 (q_content·k_content + q_rotary·k_rotary)/sqrt(Dc+Dr)。因果可见性按追加序列顺序而非 position 数值决定。加权的是 content value，合头后做 wo 投影，输出 [B,T,E]。
- 返回 (output,(all_cKV,all_rotary_key))。cache 为 None 或 ([B,P,R],[B,P,Dr])，返回长度 P+T；每个 token 仅缓存 R+Dr 个数，不持久保存 H 份展开 K/V。历史 rotary key 不重复旋转；旧缓存不原地修改、不 detach，浮点输入和权重保留梯度。
- 本练习可选择展开 K/V 或吸收投影计算，必须数值等价。省略 latent RMSNorm、YaRN、量化、dropout 和其它模型组件；固定标准 RoPE。单层缓存 O(B(P+T)(R+Dr))；朴素展开实现允许 O(BH(P+T)(Dc+Dv)) 临时存储和 O(BHT(P+T)(Dc+Dr+Dv)) attention 运算，另计线性投影。缓存减少不是 GPU 性能实测。
- 非法 x/头数、Dr、position shape/dtype/负值、base（需有限且大于 1）、cache shape/dtype/device 抛 ValueError；其它权重 shape 保证合法。禁止现成 MHA/SDPA，允许基础矩阵运算和 softmax。推荐准备 ATT-019、ATT-020、ATT-021；仅学习顺序，不增加硬前置。

## 共同约定

输入不得被原地修改。除题面明确的异常外，输入形状合法、数值有限，不要求防御任意恶意输入。PyTorch 浮点输入同 dtype、同 device，支持 float32/float64 及非连续张量，保留输出设备和梯度。NumPy 题使用 float64，不使用 autograd。公开测试通过只是实现证据，不代表 mastered。

## 验收与复盘

解释接口、正常/边界/异常、输入突变和时间/空间复杂度；PyTorch 题补充 shape、dtype、device、数值稳定及梯度。H4/H5 后须另做新的无帮助变式，本题没有新增已验证的 D+2/D+7 资产。

## 口述与追问

- 缓存 cKV 与共享旋转 key 分别解决哪部分问题，元素数如何计算？
- 为什么将 RoPE 直接施加在所有 content key 上会妨碍投影吸收？
- query 低秩压缩为什么不直接减少 KV cache？
- 展开 K/V 与吸收投影的数值等价是否能直接证明 GPU 速度更快？

## 来源

- [DeepSeek-V2 第 2.1 节和附录 C 的 MLA 定义](https://arxiv.org/html/2405.04434v5)
