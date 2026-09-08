# 题目集：全量练习与模拟面试覆盖

输入：用户提供的 `题目.md`，SHA-256 `4b9be92238921f4b8f06613a8164aa814ed8b1bb55b3081b83011da6e33f80bb`。按原顺序编号 **C001–C040 / T001–T160**。原文只引用了图片文件名，未提供图片正文；本轮没有猜测图片公式，而是明确选定并验证下列数学契约。

## 如何使用

1. 桌面「刷题训练 → 知识库」按 `T001` 等编号或关键词搜索；先在回答框独立作答、保存，再展开要点、推导、追问与 L1–L4 自查依据。草稿只存当前 Profile，不作为 Mastery 或面试评分证据。
2. 下表手撕题链接对应真实中文题面、starter 和公开测试；在「刷题训练」按题号搜索并进入原有作答工作区。环境缺少 NumPy/PyTorch 或前置未完成时会显示原因，不伪装成可运行。
3. AI 模拟面试进入原理阶段时，Codex / 普通 API 共用的真实 Context 会根据岗位、当前回答和已授权背景获得最多 8 张相关主问题及追问，不发送整套参考答案、不冻结未来题单。编码阶段只从真实可运行的验证题库选择。

## 本轮覆盖与边界

- 40 项手撕全部映射到经过验证的固定题；补齐 8 个代码缺口（其中 ATT-001 复用原 planned ID）。当前 Catalog 共 254 节点，84 个 ready 且验证通过的可推荐题。
- 160 项八股经重复主题合并为 135 张本轮完整题卡；现有知识库共 255 张卡、258 条来源记录。每个原条目的子问题仍保留覆盖说明。
- 原理题以官方论文/文档支持机制，中文表述、例子、追问和自查依据重新编写；不宣称这些就是某公司的官方面试标准。
- FlashAttention 练习是 CPU 分块在线 softmax 的精确数学实现，不是 GPU kernel 或性能认证。GPT-2 与 ViT 分别固定 LN/GELU、因果/双向语义，不用 RoPE/SwiGLU 的其他 block 冒充。
- MQA 是 Hkv=1 的明确特例；GRPO/KL 惩罚固定采样 k3 与归约口径，KL 普通散度采用 teacher→student、T=1；Pairwise Contrastive 与 InfoNCE 分开，具体约束以题面为准。
- 新增题没有 D+2/D+7 私人变式，因此不会据此宣称可达 Mastery；它们可练习、测试和用于模拟面试，不改变现有掌握规则。
- Practice 保留一次一题规则：已有实现或复盘尚未完成时，关联代码入口显示具体阻断题号；先返回当前题完成，再开启另一题。口述练习不受这一代码任务限制。
- 本轮自动化证明入口、保存隔离、候选可达性和真实状态转换；没有使用用户简历、Key 或真实 AI 服务，不能把本地测试说成 160 题均经过真人/远程模型面试验证。

## 手撕：40 / 40

| 原编号 | 主题 | 实际练习 | 契约 / 复用说明 |
| --- | --- | --- | --- |
| C001 | MHA | [ATT-019](../../curriculum/problems/ATT-019-projected-masked-mha/task.md)、[ATT-004](../../curriculum/problems/ATT-004-multi-head-attention/task.md) | 投影 self/cross 接口复用 |
| C002 | GRPO Loss | [PT-023](../../curriculum/problems/PT-023-grpo-response-mean-kl/task.md)、[PT-015](../../curriculum/problems/PT-015-grpo-loss/task.md) | 逐回答 mean + k3；旧题全 token mean 不同 |
| C003 | PPO Clipped Loss | [PT-009](../../curriculum/problems/PT-009-ppo-loss-components/task.md) | policy/value/entropy，区分三项 |
| C004 | DPO Loss | [PT-022](../../curriculum/problems/PT-022-shifted-completion-dpo/task.md) | completion-token 对齐的已验证 DPO；PT-002 仍为 contract，不计当前可执行覆盖 |
| C005 | Softmax | [LOSS-007](../../curriculum/problems/LOSS-007-stable-softmax/task.md)、[LOSS-016](../../curriculum/problems/LOSS-016-softmax-manual-backward/task.md) | 稳定前向及手算 VJP |
| C006 | KV Cache Attention | [ATT-020](../../curriculum/problems/ATT-020-gqa-incremental-cache/task.md)、[ATT-009](../../curriculum/problems/ATT-009-kv-cache/task.md) | 增量 attention；缓存容器为准备 |
| C007 | GQA | [ATT-006](../../curriculum/problems/ATT-006-grouped-query-attention/task.md)、[ATT-020](../../curriculum/problems/ATT-020-gqa-incremental-cache/task.md) | 分组 KV 与增量一致性 |
| C008 | MLA | [ATT-023](../../curriculum/problems/ATT-023-mla-latent-cache/task.md) | 新增 joint latent cache + decoupled RoPE |
| C009 | RoPE | [ATT-021](../../curriculum/problems/ATT-021-rope-position-offsets/task.md) | 已验证相邻布局与绝对位置偏移；ATT-007 仍为 contract，不计当前可执行覆盖 |
| C010 | softmax Attention | [ATT-002](../../curriculum/problems/ATT-002-scaled-dot-product-attention/task.md) | scaled dot-product attention |
| C011 | Multi-Head Cross Attention | [ATT-019](../../curriculum/problems/ATT-019-projected-masked-mha/task.md) | 现有契约支持 L != S |
| C012 | Cross-Entropy Loss | [LOSS-014](../../curriculum/problems/LOSS-014-cross-entropy/task.md)、[PT-003](../../curriculum/problems/PT-003-masked-token-cross-entropy/task.md) | 基础 CE 与有效 token mean |
| C013 | Flash Attention | [ATT-015](../../curriculum/problems/ATT-015-online-exact-attention/task.md) | CPU 分块 online exact 数学，不代表 GPU Flash kernel |
| C014 | AUC Score | [LOSS-010](../../curriculum/problems/LOSS-010-auc-with-ties/task.md) | 同分半赢 |
| C015 | Contrastive Loss | [LOSS-017](../../curriculum/problems/LOSS-017-pairwise-margin-contrastive/task.md)、[LOSS-006](../../curriculum/problems/LOSS-006-symmetric-infonce/task.md) | 新增 pairwise margin；InfoNCE 为明确另一个变体 |
| C016 | KL散度 | [LOSS-004](../../curriculum/problems/LOSS-004-masked-forward-kl/task.md) | KL(teacher\|\|student)，T=1 为普通 categorical forward KL |
| C017 | LayerNorm | [NNL-006](../../curriculum/problems/NNL-006-last-dimension-layernorm/task.md) | 最后维总体方差 |
| C018 | MQA | [ATT-020](../../curriculum/problems/ATT-020-gqa-incremental-cache/task.md)、[ATT-006](../../curriculum/problems/ATT-006-grouped-query-attention/task.md) | Hkv=1 为 MQA，现有 ATT-020 public 已覆盖该形状；ATT-005 仍为 contract |
| C019 | RMSNorm | [NNL-008](../../curriculum/problems/NNL-008-rmsnorm/task.md) | 均方根归一化 |
| C020 | Adam Optimizer | [OPT-004](../../curriculum/problems/OPT-004-adam/task.md) | Adam，不以 AdamW 替代 |
| C021 | BatchNorm | [NNL-016](../../curriculum/problems/NNL-016-batchnorm-state/task.md) | 训练与推理统计状态 |
| C022 | Beam Search Decoding | [ATT-022](../../curriculum/problems/ATT-022-beam-search-eos/task.md) | EOS 与候选 |
| C023 | Dropout | [NNL-017](../../curriculum/problems/NNL-017-inverted-dropout/task.md) | 训练/推理与反向 |
| C024 | K-Means | [TML-004](../../curriculum/problems/TML-004-lloyd-kmeans/task.md)、[TML-009](../../curriculum/problems/TML-009-kmeans-plus-plus/task.md) | Lloyd，++ 为扩展 |
| C025 | Linear Layer Backward | [NNL-018](../../curriculum/problems/NNL-018-linear-manual-backward/task.md)、[NNL-001](../../curriculum/problems/NNL-001-linear/task.md) | 新增手算 VJP，forward autograd 为准备 |
| C026 | SGD with Momentum | [OPT-002](../../curriculum/problems/OPT-002-momentum/task.md) | 带状态 momentum |
| C027 | Vit Transformer Block | [VLM-015](../../curriculum/problems/VLM-015-vit-layernorm-encoder/task.md)、[VLM-001](../../curriculum/problems/VLM-001-patch-linear-projection/task.md) | 新增 LN/GELU 双向 block，patch 为准备 |
| C028 | SwiGLU MLP | [NNL-005](../../curriculum/problems/NNL-005-swiglu-ffn/task.md) | 含三组投影的完整 FFN |
| C029 | Embedding Layer | [NNL-002](../../curriculum/problems/NNL-002-embedding/task.md) | 参数化 embedding |
| C030 | 余弦相似度 | [TNS-018](../../curriculum/problems/TNS-018-broadcast-cosine-similarity/task.md)、[TML-008](../../curriculum/problems/TML-008-knn-and-cosine/task.md) | 新增相似度输出，KNN 为应用 |
| C031 | 正弦位置编码 | [ATT-001](../../curriculum/problems/ATT-001-sinusoidal-position-encoding/task.md) | 激活既有 planned 节点，offset 与奇数维 |
| C032 | ReLU | [NNL-019](../../curriculum/problems/NNL-019-stable-elementwise-activations/task.md) | manual_relu 独立接口 |
| C033 | SwiGLU Activation | [NNL-019](../../curriculum/problems/NNL-019-stable-elementwise-activations/task.md) | swiglu_activation 独立接口，无线性投影 |
| C034 | Sigmoid | [NNL-019](../../curriculum/problems/NNL-019-stable-elementwise-activations/task.md) | stable_sigmoid，有限梯度与零点 |
| C035 | BPE | [TOK-001](../../curriculum/problems/TOK-001-deterministic-bpe/task.md) | 确定性训练与编码 |
| C036 | Top-k / Top-p Sampling | [ATT-011](../../curriculum/problems/ATT-011-ordered-sampling/task.md) | temperature -> top-k -> top-p |
| C037 | GPT-2 Transformer Block | [ATT-024](../../curriculum/problems/ATT-024-gpt2-layernorm-decoder/task.md) | 新增 LN/tanh-GELU/causal cache，不带 RoPE |
| C038 | MoE层 | [NNL-014](../../curriculum/problems/NNL-014-top2-moe-dispatch/task.md) | Top-2 dispatch/combine |
| C039 | LoRA 低秩适配线性层 | [INF-013](../../curriculum/problems/INF-013-lora-functional-merge/task.md) | functional merge 一致性 |
| C040 | KL 惩罚 | [PT-023](../../curriculum/problems/PT-023-grpo-response-mean-kl/task.md) | beta*k3 采样惩罚；不是全分布精确 KL，图片未提供 |

## 八股：160 / 160

题卡全文在 [公共知识库](../../curriculum/interviews/knowledge.yaml)，机器映射在 [覆盖清单](../../curriculum/interviews/question_collection_20260908.json)。下表不是第二份业务题库。

| 原编号 | 原主题 / 子问题 | 练习题卡 | 覆盖与合并 |
| --- | --- | --- | --- |
| T001 | 请对比Adam和AdamW优化器，解释权重衰减解耦的含义，以及为什么AdamW在大模型训练中更受青睐。 | EGT-QB-001 | Adam/AdamW更新式、耦合L2与解耦衰减、主流选择动机及参数组边界。 |
| T002 | 请解释混合精度训练的原理，为什么需要FP16前向和FP32权重？Loss Scaling的作用是什么？ | EGT-QB-002 | AMP原理、FP16/BF16与FP32状态、主权重、loss scaling和unscale顺序；纠正必须FP16前向的前提。 |
| T003 | 什么是梯度检查点（Activation Checkpointing）？它如何用计算换显存？内存复杂度是如何从O(L)降到O(√L)的？ | EGT-QB-003 | 保存边界与重算机制、A(L/k+k)推导√L、时间代价与RNG一致性。 |
| T004 | 请解释Flash Attention的原理，它如何通过分块计算和IO感知设计将显存从O(N²)降到O(N)并提升速度？ | EGT-QB-004 | FlashAttention tiling、在线softmax、线性辅助存储、精确注意力及实际HBM IO界；与T062合并。 |
| T005 | 为什么大模型训练需要学习率warmup？Cosine Decay调度策略的原理是什么？大模型训练中的实践经验有哪些？ | EGT-QB-005 | warmup稳定性动机、分段cosine公式、token/更新步预算、恢复与实践调参。 |
| T006 | 训练大模型时显存不足，有哪些系统性的解决方案？请从量化、梯度累积、混合精度、ZeRO、模型并行等角度综合分析。 | EGT-QB-006 | 完整训练显存账本、量化/累积/AMP/ZeRO/模型并行/重算/offload按瓶颈选择；与T016合并。 |
| T007 | 请详细介绍ZeRO优化器的三个级别（ZeRO-1/2/3），每个级别分别分片了什么内容？与普通数据并行有什么区别？ | EGT-QB-007 | ZeRO-1/2/3各分片对象、与DDP差异、内存式与all-gather/reduce-scatter时序。 |
| T008 | 请对比张量并行、流水线并行和数据并行三种分布式训练策略的原理、通信开销和适用场景。 | EGT-QB-008 | DP/TP/PP原理、通信类型与频率、拓扑、适用场景、3D并行与bubble。 |
| T009 | 什么是Gradient Clipping？为什么要对梯度做范数裁剪？max_norm的值如何选择？ | EGT-QB-009 | 全局范数裁剪公式和例子、max_norm选择、AMP/累积/分片顺序及限制。 |
| T010 | 大模型预训练的数据配比有什么经验和原则？代码、数学、网页、书籍等不同来源的数据比例如何选择？ | EGT-QB-010 | 代码/数学/网页/书籍配比、token统计、质量与重复曝光、代理优化及同预算分域验证。 |
| T011 | 请解释KV Cache的原理，为什么自回归推理可以缓存Key和Value？显存占用如何计算？PagedAttention做了什么改进？ | EGT-QB-011 | 因果KV可复用原因、Query无需历史缓存、字节公式及GQA头数、分页和失效边界。 |
| T012 | 请介绍vLLM的核心创新，包括PagedAttention的虚拟内存管理、Continuous Batching机制，以及它如何提升推理吞吐量。 | EGT-QB-012 | vLLM分页块表/共享/写时复制、continuous batching、吞吐与TTFT/TPOT/SLO权衡。 |
| T013 | 大模型预训练的完整流程是怎样的？从 0 预训练一个模型要做哪些事？ | EGT-QB-013 | 从零预训练的数据治理、tokenizer、架构预算、loss/mask、精度并行、监控恢复评测交付闭环。 |
| T014 | SFT（监督微调）的原理、流程和损失函数是什么？为什么只在 response 上算 loss？ | EGT-QB-014 | SFT原理流程和条件CE、response-only动机及非必然性、多轮mask、shift/packing/全mask边界。 |
| T015 | 为什么 SFT 之后模型通用能力会下降（灾难性遗忘）？如何缓解？ | EGT-QB-015 | SFT后遗忘机制、模板或评测造成的假性退化、学习率/replay/PEFT/早停及双域回归。 |
| T016 | 大模型训练的显存由哪几部分组成？各占多少？如何估算？ | EGT-QB-006 | 权重、梯度、主权重、Adam矩、激活、workspace/通信/allocator逐项估算和16P条件；并入T006。 |
| T017 | 预训练 / SFT / RLHF 三阶段分别解决什么问题？ | EGT-QB-017 | 预训练/SFT/对齐不同目标及数据；同时区分经典RLHF内部SFT/RM/PPO三阶段。 |
| T018 | 继续预训练（Continue Pre-training）怎么做？要注意什么（如何避免灾难性遗忘）？ | EGT-QB-015 | CPT领域语言建模流程、tokenizer兼容、与SFT区别、通用replay及遗忘和领域收益验证；并入T015。 |
| T019 | 大模型训练的 checkpoint 怎么管理？断点续训和故障恢复怎么做？ | EGT-QB-019 | 训练checkpoint完整状态、分片原子提交、校验保留、断点恢复和变拓扑重分片边界。 |
| T020 | 如何处理长文本训练？长上下文窗口怎么扩展、位置编码怎么外推？ | EGT-QB-020 | 长文本训练、位置外推、真实长依赖数据、内存与算力方案、长短任务及位置分桶评测。 |
| T021 | 大模型训练中如何监控和调试？关注哪些指标？loss 异常升降如何分析？ | EGT-QB-021 | 训练/验证loss、梯度、scaler、吞吐等监控；loss异常升高和下降的竞争解释及排查顺序。 |
| T022 | 微调时 batch size、学习率、epoch 怎么设？如何防止过拟合？ | EGT-QB-022 | micro/effective batch、token预算、学习率扫描、epoch曝光、过拟合和按簇拆分/早停。 |
| T023 | RAG 和微调有什么区别？什么场景选哪个？什么场景适合用 SFT？ | EGT-QB-023 | RAG与参数微调的差异、时效证据和行为适配场景、SFT适用条件、组合及oracle检索诊断。 |
| T024 | 请详细介绍RLHF的完整三阶段流程，包括每个阶段的目标、数据需求和关键设计选择。 | EGT-QB-017 | 经典RLHF三阶段目标、示范/偏好/rollout数据、RM训练及actor/critic/ref/old边界；并入T017。 |
| T025 | 请详细解释PPO算法的原理，包括clip目标函数的设计动机、ratio约束机制，以及与TRPO的区别。 | EGT-QB-025 | PPO clip公式及正负优势分段、ratio非硬约束、总loss、与TRPO信赖域差别。 |
| T026 | 请推导DPO（Direct Preference Optimization）的损失函数，解释它如何从RLHF目标重新参数化得到。 | EGT-QB-026 | KL正则最优策略、奖励重参数化、Z抵消、BT偏好到DPO损失推导及token实现。 |
| T027 | 请对比DPO和PPO两种对齐方法，从奖励模型需求、训练稳定性、效果差异和适用场景等方面分析。 | EGT-QB-027 | DPO/PPO显式RM与critic需求、离线/在线数据、稳定性和效果边界、场景取舍；含GRPO。 |
| T028 | 请介绍GRPO（Group Relative Policy Optimization）算法的原理，它在DeepSeek-R1中是如何使用的？为什么不需要Critic网络？ | EGT-QB-028 | GRPO组优势、无critic基线、PPO式目标、R1/R1-Zero应用和多阶段路线。 |
| T029 | 奖励模型（Reward Model）是如何训练的？请解释Bradley-Terry偏好模型和损失函数的设计。 | EGT-QB-029 | RM训练、Bradley–Terry损失、平移不可识别、偏好数据与评测及critic职责区别。 |
| T030 | KL散度惩罚在RLHF中起什么作用？为什么需要防止策略偏离参考模型？β系数如何选择？ | EGT-QB-030 | RLHF的KL方向、reference约束目的、采样估计、beta与奖励/长度尺度选择及限制。 |
| T031 | 什么是奖励黑客（Reward Hacking）问题？它是如何产生的？有哪些解决方案？ | EGT-QB-031 | reward hacking成因、具体漏洞例子、独立检测、修复奖励/数据及回归验证闭环。 |
| T032 | GRPO为什么会出现reward崩溃？没有Critic网络带来了哪些稳定性问题？如何缓解？ | EGT-QB-028 | GRPO奖励崩溃的组方差/探索/信用分配/长度/陈旧rollout因素、有效组指标和缓解；不认定无critic必崩溃。 |
| T033 | 为什么SFT冷启动对RLHF如此重要？为什么不能直接从预训练模型开始做RL训练？ | EGT-QB-033 | SFT冷启动收益、直接基座RL的可行条件、成功组率例子和R1-Zero反例；纠正不能直接RL。 |
| T034 | 为什么 SFT 之后还需要 RLHF / 对齐？RLHF 的优缺点是什么？ | EGT-QB-034 | SFT后偏好对齐的额外信号、收益和代价、alignment tax、无需继续RL的条件及独立评测。 |
| T035 | RLHF 和 RLAIF 的区别是什么？ | EGT-QB-035 | RLHF/RLAIF反馈来源区别、与PPO/DPO正交、Constitutional AI流程、人机标签偏差及校准。 |
| T036 | PPO 的 loss 由哪几部分组成？Actor 和 Critic 分别是什么？ | EGT-QB-025 | PPO actor/value/entropy及可选KL总loss、Actor/Critic分工和detach边界；并入T025。 |
| T037 | PPO 中的 GAE / 优势函数估计是怎么做的？ | EGT-QB-037 | GAE/优势函数、TD残差倒序递推、gamma/lambda偏差方差、return target及终止/截断mask。 |
| T038 | 强化学习 On-policy 和 Off-policy 的区别？Policy-based 和 Value-based 的区别？ | EGT-QB-038 | On/off-policy与policy/value-based两个分类轴、PPO/Q-learning/actor-critic例子及覆盖/复用限制。 |
| T039 | 为什么 RL 训练不稳定？怎么稳定 PPO 训练？训崩了 / 学歪了怎么处理？ | EGT-QB-039 | RL非平稳/奖励噪声/critic/数据陈旧等不稳定原因、PPO不变量诊断、稳定化及训崩回滚。 |
| T040 | DPO 训练需要什么格式的数据？DPO 有哪些变种 / 改进算法（SimPO / IPO / KTO / ORPO）？ | EGT-QB-040 | DPO成对数据与多轮契约；SimPO/IPO/KTO/ORPO的参考模型、标签结构、长度和目标差异。 |
| T041 | DPO 和 GRPO 的区别是什么？如何在 PPO / DPO / GRPO 之间选择？ | EGT-QB-027 | DPO与GRPO离线/在线及组采样成本区别，PPO/DPO/GRPO反馈形态、模型需求和场景选择；并入T027。 |
| T042 | GRPO 的后续改进有哪些？DAPO 和 GSPO 各解决了 GRPO 的什么问题？ | EGT-QB-042 | DAPO四项技术、GSPO长度归一化序列ratio与clip、长回答/MoE稳定性及公平预算边界。 |
| T043 | 奖励模型坍缩 / 过优化问题如何解决？为什么有了 Reward Model 还需要 Critic？ | EGT-QB-029 | RM坍缩和代理过优化的区分及缓解；RM终局偏好评分与Critic前缀期望回报的非等价性。 |
| T044 | RL 训练中的训推不一致（train-inference mismatch）问题是什么？怎么解决？ | EGT-QB-044 | 训推权重/数值/kernel/模板/采样分布不一致、真实行为logprob、同步和校正支持条件。 |
| T045 | RLVR 训练能否认为是一种 SFT？本质区别是什么？ | EGT-QB-045 | RLVR与SFT数据和梯度本质区别、正负优势、可验证奖励限制、拒绝采样SFT关系。 |
| T046 | GPT 和 BERT 的架构有什么区别？各自适用于什么场景？ | EGT-QB-046 | GPT因果decoder与BERT双向encoder的mask、目标和任务场景；与T050/T051架构比较合并。 |
| T047 | 详细介绍 Transformer 架构的核心组件：Multi-Head Attention、FFN、残差连接与层归一化 | EGT-QB-047 | Transformer的MHA/FFN/残差/Norm组件、逐shape数据流和职责。 |
| T048 | 注意力机制中为什么要除以 根号下dk​​？请从数学角度推导 | EGT-QB-048 | 独立零均值单位方差假设下点积方差dk、sqrt(dk)缩放、softmax Jacobian和假设边界。 |
| T049 | Pre-LN 和 Post-LN 有什么区别？为什么现代大模型普遍使用 Pre-LN？ | EGT-QB-049 | Pre-LN/Post-LN公式及Jacobian、初始化梯度/warmup动机、final norm和非普适优势。 |
| T050 | 为什么大语言模型普遍采用 Decoder-only 架构？ | EGT-QB-046 | Decoder-only统一训练/参数共享/生成cache与工程理由，以及任务和架构比较的边界；并入T046。 |
| T051 | Prefix Decoder、Causal Decoder 和 Encoder-Decoder 三种架构有什么区别？ | EGT-QB-046 | Prefix Decoder、Causal Decoder、Encoder-Decoder输入/目标可见性与cross-attention四token例子；并入T046。 |
| T052 | LayerNorm 和 BatchNorm 有什么区别？为什么 Transformer 使用 LayerNorm？ | EGT-QB-052 | LN/BN归约轴、train/eval统计、Transformer自回归/变长与padding适配；含RMS对照。 |
| T053 | 什么是大语言模型的涌现能力？如何理解这种现象？ | EGT-QB-053 | 涌现操作定义、连续能力经离散指标产生门槛的p^k例子、主源不同观点和验证设计。 |
| T054 | 多头注意力机制的作用是什么？为什么要使用多个注意力头？ | EGT-QB-047 | 多头不同Q/K/V子空间的作用、固定总维度取舍、头冗余和不能固定解释头语义；并入T047。 |
| T055 | 大语言模型的训练目标是什么？因果语言模型和 Next Token Prediction 的关系是什么？ | EGT-QB-055 | 序列概率链式分解、因果LM与NTP关系、teacher forcing、并行训练/逐步生成及目标局限。 |
| T056 | RMSNorm 的原理是什么？为什么比 LayerNorm 更适合大模型？ | EGT-QB-052 | RMSNorm公式、取消均值中心化、计算及平移不变性区别、为何常用于大模型及性能边界；并入T052。 |
| T057 | 对比 Sinusoidal、RoPE 和 ALiBi 三种位置编码的原理与外推能力 | EGT-QB-057 | Sinusoidal/RoPE/ALiBi注入位置、公式和外推能力边界；含RoPE完整推导。 |
| T058 | 请解释GQA（Grouped-Query Attention）分组查询注意力的原理，它如何减少KV头数来节省显存？与MHA和MQA对比如何？ | EGT-QB-058 | GQA头映射及KV缓存缩减，与MHA/MQA端点、质量/速度及物理复制风险。 |
| T059 | 请详细解释DeepSeek-V2提出的MLA（Multi-head Latent Attention）多头潜在注意力机制，其低秩KV压缩原理及与MHA的推理速度对比。 | EGT-QB-059 | DeepSeek-V2 MLA低秩联合KV、上投影吸收、解耦RoPE、与MHA/GQA/MQA及推理速度公平比较。 |
| T060 | 请解释RoPE（旋转位置编码）的数学原理，包括旋转矩阵的构造、相对位置性质的推导及其长度外推能力。 | EGT-QB-057 | RoPE二维旋转矩阵、R(m)^T R(n)=R(n-m)相对位置推导、布局/offset和长度外推限制；并入T057。 |
| T061 | 请详细解释MoE（混合专家模型）的原理，包括稀疏激活机制、Top-K路由、负载均衡Loss，以及DeepSeek-MoE的改进。 | EGT-QB-061 | MoE稀疏Top-K dispatch/combine、负载均衡loss、capacity及DeepSeek细粒度/共享专家。 |
| T062 | 请详细解释FlashAttention v1/v2的原理，包括分块tiling策略、在线softmax算法，以及IO复杂度如何从O(N²)优化到O(N)。 | EGT-QB-004 | FlashAttention v1/v2 tiling和在线softmax、v2工作划分、HBM IO的M相关界；纠正无条件O(N)IO前提，并入T004。 |
| T063 | 请详细解释Mamba（选择性状态空间模型）的原理，包括SSM基础、选择性机制如何实现，以及与Transformer在效率和能力上的对比。 | EGT-QB-063 | Mamba连续SSM与离散递推、输入相关B/C/Delta选择、parallel scan、复杂度和有限状态能力取舍。 |
| T064 | 请解释投机采样（Speculative Decoding）的工作原理，包括小模型起草、大模型验证的流程，接受率计算及加速效果分析。 | EGT-QB-064 | 投机草拟与目标验证、min(1,p/q)接受、max(p-q,0)拒绝残差、预期产出与速度/cache分析。 |
| T065 | 请梳理LLaMA系列模型的架构演进（LLaMA-1到LLaMA-3），分析RMSNorm、RoPE、GQA、SwiGLU等关键架构选择。 | EGT-QB-065 | LLaMA1到首发3共同骨干及按版本/尺寸演进、RMSNorm/RoPE/GQA/SwiGLU选择与预算。 |
| T066 | 请全面分析DeepSeek系列模型的架构创新，包括MLA+MoE组合、FP8训练、Loss-Free负载均衡等技术突破。 | EGT-QB-066 | DeepSeekMoE/V2/V3/R1创新归属、MLA+MoE、FP8混合精度、bias主均衡与补充序列aux loss。 |
| T067 | 请解释NTK-aware RoPE外推方法和YaRN，对比线性插值与NTK插值在长上下文扩展中的效果差异。 | EGT-QB-067 | PI均匀缩频、NTK-aware base公式、YaRN分频段及温度校正、长短效果与动态cache一致性。 |
| T068 | LoRA 的原理是什么？请详细解释低秩分解、参数量计算、初始化策略和推理时的合并 | EGT-QB-068 | LoRA低秩分解、参数量、零增量初始化及首步梯度、目标层、alpha/r和推理合并。 |
| T069 | 全参数微调和 LoRA 微调有什么区别？在显存、效果和适用场景上如何对比？ | EGT-QB-069 | 全参数与LoRA显存/状态/激活/效果/部署取舍及适用场景；并与其他PEFT比较。 |
| T070 | LoRA 的 rank 如何选择？过低或过高有什么影响？ | EGT-QB-070 | LoRA rank高低的容量和成本、alpha/r混杂、目标层分配、同预算扫描与过拟合诊断。 |
| T071 | P-tuning 的原理是什么？它和传统微调有什么区别？ | EGT-QB-071 | P-tuning连续输入提示及编码器、与传统全参微调差异、冻结/非冻结配置和v2区别。 |
| T072 | QLoRA 的原理是什么？NF4 量化和 Double Quantization 是怎么工作的？ | EGT-QB-072 | QLoRA冻结量化基座与LoRA反向、NF4码本、Double Quantization尺度及paged optimizer。 |
| T073 | Prefix Tuning 的工作原理是什么？它和 P-tuning 有什么区别？ | EGT-QB-071 | Prefix Tuning各层虚拟KV和重参数化，比较P-tuning v1输入提示及v2深提示、参数/缓存成本；并入T071。 |
| T074 | 对比 LoRA、Adapter、Prefix Tuning 和 P-tuning 这几种 PEFT 方法的优缺点和适用场景 | EGT-QB-069 | LoRA/Adapter/Prefix/P-tuning更新位置、可合并性、训练与推理成本、优势限制和场景；并入T069。 |
| T075 | LoRA 中为什么 B 初始化为零矩阵，A 用正态分布初始化？ | EGT-QB-068 | LoRA B零A随机的零增量与梯度推导、双零停滞、A不必唯一正态分布的实现澄清；并入T068。 |
| T076 | AdaLoRA 是什么？它如何自适应地调整不同层的秩？ | EGT-QB-076 | AdaLoRA PΛQ参数化、正交正则、重要性评分、全局预算调度及非均匀秩；不每步完整SVD。 |
| T077 | LoRA 应该加在哪些层？为什么 Q/V 最常见？alpha 与 rank 的比值怎么理解？ | EGT-QB-068 | LoRA Q/V动机、K/O/FFN目标模块与等预算消融、alpha/r的更新尺度及rank混杂；并入T068。 |
| T078 | 请详细介绍预训练数据的质量过滤流程，包括去重、质量评分、语言检测和有害内容过滤。 | EGT-QB-078 | 预训练数据质量流程中的解析/语言识别、精确与近重复、质量评分、有害/PII过滤及误杀审计。 |
| T079 | SFT数据构造有哪些最佳实践？如何在指令多样性和数据质量之间取得平衡？ | EGT-QB-079 | SFT数据覆盖矩阵、示范与合成来源、事实/格式验证、多样性质量取舍、去重及分桶评测。 |
| T080 | 如何构造高质量的多轮对话数据？请从上下文一致性、轮次设计和数据格式等方面详细说明。 | EGT-QB-079 | 多轮上下文依赖、纠错/澄清/约束轮次、messages角色/工具格式、模板mask、完整对话拆分与反事实一致性检查；并入T079。 |
| T081 | 预训练数据的配比策略是什么？不同领域（代码、数学、中文、英文）的数据应该如何配比？ | EGT-QB-010 | 跨区合并T010：预训练数据配比策略，代码/数学/中文/英文的质量、语言与领域覆盖、token采样比例、去重/重复暴露和等预算消融；A作者已确认完整承接。 |
| T082 | 请比较BPE、WordPiece和Unigram三种Tokenizer算法，以及在中文场景下的分词策略和词表大小选择。 | EGT-QB-082 | 三种训练与编码策略；中文规范化与词表大小；BPE 合并示例和 OOV 条件；训练/编码复杂度与输出成本 |
| T083 | 请详细介绍数据去重的方法，包括MinHash、SimHash、精确去重和N-gram去重。 | EGT-QB-083 | 规范化后精确哈希；MinHash/Jaccard/LSH；SimHash/Hamming；N-gram局部匹配与簇级划分 |
| T084 | 请介绍合成数据的主要方法，包括Self-Instruct、WizardLM进化指令、Magpie等，以及如何进行质量验证。 | EGT-QB-084 | 三种生成机制；可解性与正确性分层过滤；谱系、去重和数据污染；等预算下游消融 |
| T085 | 什么是预训练数据Packing？请解释序列拼接、跨序列注意力mask以及如何提升GPU利用率。 | EGT-QB-085 | 拼接与有效利用率；跨序列attention隔离；shifted loss/position边界；kernel支持与等价性验证 |
| T086 | 请解释困惑度（Perplexity/PPL）的定义、数学推导、实际意义和局限性。 | EGT-QB-086 | 概率分解到PPL推导；几何平均与实例；tokenizer/数据可比性；滑窗和有效token归约 |
| T087 | 请介绍主流LLM评测基准（MMLU、GSM8K、HumanEval、MATH、HellaSwag），说明各自测试的能力维度和评测方式。 | EGT-QB-087 | 五项能力与任务格式；各自计分与解析；采样/提示/工具预算；切片与污染限制 |
| T088 | 请解释LLM-as-a-Judge评估方法，包括MT-Bench的设计、position bias问题及其优劣势分析。 | EGT-QB-088 | MT-Bench两轮八类设计；评分量表与证据；位置/长度等偏差控制；人工校准和版本冻结 |
| T089 | 什么是大模型幻觉（Hallucination）？请分类解释factual和faithfulness幻觉的成因、检测方法和缓解策略。 | EGT-QB-089 | 事实性/忠实性参照系；数据、检索、推理成因；断言级证据核验；按瓶颈缓解与拒答 |
| T090 | 请对比ORM（结果奖励模型）和PRM（过程奖励模型），分析它们在数学推理等任务中的优劣。 | EGT-QB-090 | 整答与步骤监督；训练/搜索用途；聚合和标签成本；错误推导反例与公平评测 |
| T091 | 如何评估LLM的指令跟随能力？请介绍IFEval基准及多维度评估方法。 | EGT-QB-091 | IFEval可验证指令；instruction/prompt级口径；strict/loose与规则边界；语义/多轮等互补维度 |
| T092 | 什么是Benchmark数据污染（Data Contamination）问题？如何检测和应对？动态Benchmark有何优势？ | EGT-QB-092 | 污染通道与影响；多层检测与证据限制；簇/时间/来源隔离；动态benchmark优势与漂移 |
| T093 | 分析BLEU和ROUGE指标的局限性，为什么它们与人类判断相关性差？在什么场景下它们仍然适用？ | EGT-QB-093 | BLEU公式与BP；ROUGE-N/L及口径；实体/否定/改写反例；固定参考场景与互补指标 |
| T094 | Chatbot Arena 的评测原理是什么？ELO 评分机制是怎么算的？ | EGT-QB-094 | 匿名成对偏好流程；Elo公式与计算；BT全局估计与尺度；偏差、平局和不确定性 |
| T095 | pass@k 指标的含义和计算方法是什么？为什么用无偏估计？ | EGT-QB-095 | 至少一次成功定义；组合数推导与无偏前提；数值边界和逐题聚合；候选预算与实际选择器 |
| T096 | 准确率、召回率、F1 的含义与计算？数据不均衡有什么影响？loss 降但 F1 不涨如何排查？ | EGT-QB-096 | 混淆矩阵四指标；不均衡与macro/micro；loss-F1分离机制；验证阈值和标签排查 |
| T097 | Recall、MRR、Precision 等检索指标的含义？如何评价检索结果的好坏？ | EGT-QB-097 | 三个指标定义与示例；MRR对多证据的盲点；NDCG与分级标注；分阶段/语料/预算控制 |
| T098 | RAG 系统如何评测？若 Answer Relevance 偏低，如何区分检索质量与生成能力？ | EGT-QB-098 | 检索/组装/生成分层指标；oracle上下文替换；固定证据的模型消融；证据链与端到端验收 |
| T099 | Agent 的评测流程是怎样的？评价指标如何定义和获取？ | EGT-QB-099 | 环境初态/成功断言；trace与终态分离；成功、安全、成本指标；重复可靠性与可复位评测 |
| T100 | 多模态模型 / VLM 怎么评估效果与幻觉？怎么判断是 encoder 还是 LLM 推理的问题？ | EGT-QB-100 | 感知/推理/幻觉能力矩阵；POPE及断言核验；oracle文字对照；encoder/projector/预处理消融 |
| T101 | Reward Model 如何评估？reward hacking 的原因和解决方法？ | EGT-QB-101 | 偏好排序与切片；长度捷径和校准；优化强度下独立效用；reward hacking缓解 |
| T102 | 大模型评测体系怎么搭建？离在线效果差异如何解决、指标怎么对齐？ | EGT-QB-102 | 任务分层与版本冻结；质量/系统/安全指标；离在线差异重放；受控实验与反馈隔离 |
| T103 | 如何评估微调后模型的效果？和基座模型如何对比？如何做 train/test 去重？ | EGT-QB-103 | 公平基座与推理预算；train/test簇级去重；目标收益和通用回退；valid选型/test终验 |
| T104 | 请解释Scaling Law的核心内容，特别是Chinchilla法则中参数量与数据量的关系，以及compute-optimal训练策略。 | EGT-QB-104 | N/D损失幂律；C≈6ND与边际平衡推导；Chinchilla经验范围；训练最优与部署成本 |
| T105 | 什么是Chain-of-Thought（CoT）提示？它为什么有效？请同时介绍Zero-shot CoT和Self-Consistency方法。 | EGT-QB-105 | few-shot与zero-shot提示；多路径最终答案聚合；可能机制及非保证性；等预算验证与成本 |
| T106 | 请介绍DeepSeek-R1的技术路线，包括GRPO强化推理方法、从R1-Zero到R1的演进，以及其主要技术贡献。 | EGT-QB-106 | 固定原始版本与V3-Base；GRPO组相对优势；R1的四阶段链；推理样本蒸馏与贡献限制 |
| T107 | 请介绍多模态大模型的核心技术，包括CLIP的对比学习、LLaVA的两阶段训练方法，以及视觉编码器的选择。 | EGT-QB-149、EGT-QB-157、EGT-QB-159 | 综合题按核心技术分解：T149含CLIP双编码器、双向对比学习公式与zero-shot；T157含原始LLaVA两阶段、冻结策略、条件CE和视觉连接；T159含视觉encoder选择、预训练目标与视觉/语言参数和token预算。 |
| T108 | 请介绍Agent框架的核心设计，包括ReAct的思维-行动循环、工具调用机制，以及LangChain和LlamaIndex等框架。 | EGT-QB-135、EGT-QB-136、EGT-QB-145、EGT-QB-137 | 综合题映射：T135含Agent完整架构与LangChain/LlamaIndex定位；T136含ReAct决策-行动-观察循环；T137含工具schema、调用、宿主执行和结果回传；T145含LangChain/LangGraph和状态编排。 |
| T109 | 请介绍长上下文技术的核心方法，包括YaRN、LongRoPE等位置编码扩展方法，RAG与长上下文的对比，以及lost in the middle问题。 | EGT-QB-109 | RoPE长度适配问题；YaRN与LongRoPE差别；RAG和长窗口成本取舍；中间遗忘与位置消融 |
| T110 | 为什么强化学习在大模型上很难做？请从输出分布集中、奖励黑客和训练不稳定等角度分析。 | EGT-QB-110 | 动作空间、稀疏奖励与熵；reward hacking；陈旧rollout和数值动态；监控分流与干预 |
| T111 | 请介绍大模型安全对齐的核心方法，包括Constitutional AI、红队测试、越狱攻击和RLHF的局限性。 | EGT-QB-111 | 原则批评/修订与AI反馈；红队/越狱威胁类别；RLHF局限和执行边界；安全与误拒的双向评测 |
| T112 | 请详细介绍模型量化技术，包括PTQ与QAT的区别、INT8/INT4量化方法，以及GPTQ和AWQ算法的原理。 | EGT-QB-112 | INT8/INT4量化公式与粒度；PTQ/QAT训练语义；GPTQ二阶补偿/AWQ缩放；校准、kernel与质量性能 |
| T113 | 请详细解释KV Cache的显存占用计算公式，以及PagedAttention、GQA和MLA等优化方法如何减少KV Cache开销。 | EGT-QB-113 | 传统KV公式与单位；MHA/MQA/GQA头数；MLA潜变量加位置键；分页浪费与结构压缩区别 |
| T114 | 什么是Continuous Batching？它与静态批处理有什么区别？请解释Orca论文的核心思想及其对吞吐量的提升。 | EGT-QB-114 | 静态与迭代级生命周期；Orca选择性批处理；prefill/decode和KV预算；吞吐/延迟/公平性 |
| T115 | 请解释投机采样（Speculative Decoding）的原理，包括draft model生成、target model验证、接受条件和加速比分析。 | EGT-QB-064 | 跨区合并T064：draft多token起草、target并行验证、min(1,p/q)接受条件、拒绝后残差分布、分布保持与接受率/成本/加速比条件；A作者已确认完整承接。 |
| T116 | 请解释张量并行推理的原理，包括列并行和行并行的切分方式、通信原语和All-Reduce开销。 | EGT-QB-116 | 列并行shape；行并行部分和；attention与布局契约；All-Reduce开销和decode瓶颈 |
| T117 | 请对比权重量化和激活量化的挑战，并介绍混合精度策略在推理中的应用。 | EGT-QB-117 | 固定权重与动态激活；离群值与校准；等价缩放和混合精度；分层误差与工作负载 |
| T118 | 请详细解释vLLM中PagedAttention的工作原理，包括虚拟内存管理思想、碎片消除机制和对并发请求数的提升。 | EGT-QB-012 | 跨区合并T012：vLLM PagedAttention的逻辑/物理块映射、按需分配、引用计数/COW、外部碎片/块尾浪费与并发提升，并包含continuous batching关系；A作者已确认完整承接。 |
| T119 | 请对比LLM推理中Prefill和Decode两个阶段的计算特性差异，并解释分离部署和Chunked Prefill策略。 | EGT-QB-119 | 阶段算术强度与KV访问；分块prefill连续性；分离部署与KV传输；SLO/goodput和负载比例 |
| T120 | 请介绍知识蒸馏技术在大模型中的应用，包括Task-specific蒸馏、黑盒/白盒蒸馏方法，以及TinyBERT和MiniLM等代表性工作。 | EGT-QB-120 | 黑盒/白盒及任务特定；温度KL公式与梯度；TinyBERT和MiniLM机制；容量、词表与公平比较 |
| T121 | 请详细解释BPE（字节对编码）分词算法的原理，包括合并规则的学习过程和处理未登录词的机制。 | EGT-QB-082 | 区内合并T082：BPE训练统计相邻pair并按顺序合并，编码按merge ranks；给合并计数示例、字符级OOV与完整byte/byte-fallback条件，以及朴素训练O(KM)/编码O(n²)的实现前提。 |
| T122 | Flash Attention v1 / v2 / v3 各代的改进是什么？为什么一代比一代快？ | EGT-QB-122 | v1分块与显存/IO区别；在线softmax重标定；v2并行与分工；v3硬件特性与比较边界 |
| T123 | vLLM 和 SGLang 的核心机制与区别？PagedAttention 与 RadixAttention 分别解决什么？ | EGT-QB-123 | vLLM原始分页机制；SGLang结构化运行时与radix；分配/计算两类收益；版本化公平比较 |
| T124 | AllReduce 与 Ring-AllReduce 的原理？Parameter Server 架构与 AllReduce 架构的区别？ | EGT-QB-124 | AllReduce语义与全局平均；reduce-scatter/all-gather；Ring通信成本；PS同步异步与热点 |
| T125 | Megatron 张量并行的行/列切分是怎么做的？3D 并行（DP + TP + PP）如何组合？ | EGT-QB-125 | Megatron行列互补切分；DP/TP/PP三维职责；32GPU分组与global batch；拓扑、气泡和checkpoint |
| T126 | FSDP 的原理是什么？它和 ZeRO 是什么关系？ | EGT-QB-126 | all-gather/reshard/reduce-scatter；ZeRO三个阶段对应；常驻与峰值显存；粒度、版本和恢复 |
| T127 | 序列并行（Sequence Parallel）的原理？它和张量并行（Tensor Parallel）的关系？ | EGT-QB-127 | TP中的复制激活；沿S分片与collective衔接；SP与context parallel区别；随机性、mask和显存核算 |
| T128 | 专家并行（Expert Parallel）的原理？MoE 训练和推理有哪些挑战？ | EGT-QB-128 | router/dispatch/expert/combine；all-to-all与逆置换；容量和负载不均；训练/推理小batch与拓扑 |
| T129 | MLA（Multi-head Latent Attention）的原理？和 MQA / GQA 有什么区别？ | EGT-QB-059 | 跨区合并T059：MLA联合低秩KV、投影吸收、解耦RoPE及潜变量缓存，与MQA/GQA共享头方式的差别和推理收益条件；A作者已确认完整承接。 |
| T130 | DeepSeek MoE 的架构是什么？细粒度专家和共享专家分别起什么作用？ | EGT-QB-130 | 原始版本与细粒度拆分；共享专家/专门专家职责；稀疏输出表达；等预算质量和系统代价 |
| T131 | Prefix Caching 的原理是什么？它如何降低首 token 延迟（TTFT）？ | EGT-QB-131 | 因果前缀不变性；最长前缀与缓存键；共享/回收/隔离；TTFT收益及TPOT边界 |
| T132 | CUDA Kernel 有哪些优化方法？算子融合（Kernel Fusion）的原理和例子？ | EGT-QB-132 | profile与roofline；bias/GELU融合访存账本；tiling/访存/并行方法；寄存器代价和验证 |
| T133 | 分布式训练的通信优化有哪些方法？NVLink 和 RDMA 的作用是什么？ | EGT-QB-133 | 通信trace与瓶颈分类；分桶/重叠/层次collective；NVLink/RDMA/GPUDirect区别；收敛与端到端收益 |
| T134 | 流水线并行的 bubble 是什么？1F1B 和 zero-bubble 调度如何优化它？ | EGT-QB-134 | 依赖与理想bubble估计；GPipe/1F1B激活生命周期；dX/dW拆分填空；资源、同步与公平比较 |
| T135 | 一个完整的 Agent 智能体架构一般包括哪些部分？ | EGT-QB-135 | 输入到动作/观察/验证的数据流；状态、记忆与预算；ReAct和三类框架定位；trace、终态与可靠性 |
| T136 | ReAct 范式是什么？Thought / Action / Observation 的循环逻辑与优缺点？ | EGT-QB-136 | Thought/Action/Observation职责；依观察更新决策；适应性收益与成本；重复检测和停止验证 |
| T137 | Function Call 的流程是怎样的？模型如何知道该调用哪个工具？ | EGT-QB-137 | 工具schema与模型选择；调用解析/授权/执行；call ID结果回传；选择可靠性和语义限制 |
| T138 | Function Call 返回的 JSON 不标准、工具超时或返回空、模型捏造参数，分别怎么处理？ | EGT-QB-138 | JSON/schema可恢复错误；超时的不确定副作用；空结果语义；参数实体校验与预算 |
| T139 | Function Calling、MCP、Tool Use、Skill 这几个概念是什么关系？ | EGT-QB-139 | 能力/接口/协议/资源包四层；MCP角色及tools/resources/prompts；Skill按需加载；组合实例与权限 |
| T140 | 怎么设计 Agent 的记忆系统？短期与长期记忆怎么存、怎么管理上下文、怎么做记忆衰减？ | EGT-QB-140 | 短期状态与模型上下文；长期记忆类型和来源；写入/冲突/权限生命周期；相关度与时间衰减 |
| T141 | 多 Agent 协作有哪些常见模式？什么时候用单 Agent、什么时候用多 Agent？上下文怎么传递共享？ | EGT-QB-141 | 常见协作拓扑；单/多选择与关键路径；上下文/产物契约；共享状态冲突和相关错误 |
| T142 | Agent 的多步任务规划与分解如何实现？怎么保证拆解步骤合理、用哪种 Prompt 策略？ | EGT-QB-142 | 目标与成功断言；输入/产物/依赖拆分；计划执行和局部重规划；预算、权限与进度证据 |
| T143 | 为什么 Agent 经常出现幻觉或乱调工具？怎么缓解？RAG 生成阶段如何设边界？ | EGT-QB-143 | 证据/指令/先验错误来源；参数来源与宿主校验；RAG断言及引用边界；无证据、冲突和注入回归 |
| T144 | Agent 在任务执行失败时，怎么做错误重试和反思？具体实现逻辑是什么？ | EGT-QB-144 | 失败类型到动作分流；幂等与跨层预算；证据驱动反思；经验验证和停止 |
| T145 | LangChain 和 LangGraph 分别提供什么功能？区别和各自优势是什么？状态快照机制怎么实现？ | EGT-QB-145 | LangChain/LangGraph层次；图状态和检查点；checkpointer/store与后端；恢复时外部副作用 |
| T146 | 如何构造 Agent 的 SFT 训练数据？为什么用强化学习做 Agent 对齐？ | EGT-QB-146 | 真实交互轨迹与消息格式；assistant监督和失败数据；SFT分布偏移/RL终态目标；环境、信用和独立评测 |
| T147 | 工程级 Coding Agent 在处理项目上下文、生成代码时有哪些核心挑战？上下文等于记忆吗？ | EGT-QB-147 | 相关上下文与调用契约；跨模块/环境/已有修改；上下文与版本化记忆；执行测试与diff验证 |
| T148 | Agent 和 Workflow 有什么区别？什么时候用哪个？ | EGT-QB-148 | 控制路径归属；任务条件与选型；确定流程中的有限Agent分支；成本、异常和验收 |
| T149 | 介绍一下 CLIP 的原理和结构？zero-shot 能力是如何实现的？ | EGT-QB-149 | 双编码器与投影归一化；温度/双向InfoNCE公式；类别文本原型与zero-shot；架构选择和细粒度限制 |
| T150 | ViT 一般怎么预训练？如何优化 CLIP 提取细粒度特征？ | EGT-QB-150 | ViT多种预训练目标；全局/局部特征差异；分辨率与局部对齐方法；数据标签一致及消融 |
| T151 | CLIP 训练中一个 batch 混入了相同图片（正样本被当负样本），怎么解决？ | EGT-QB-151 | 对角线假设及冲突；图像/语义簇采样；多正例公式或mask；跨卡ID和双向一致 |
| T152 | 为什么 CLIP 的嵌入效果不好？BGE/E5 在 MTEB 上大幅领先 CLIP 的原因是什么？ | EGT-QB-152 | 质疑未限定的排行榜命题；MTEB文本任务范围；CLIP/BGE/E5训练目标；输入协议与分任务比较 |
| T153 | 多模态大模型的主流架构有哪些？大致结构是什么？连接器如何设计？ | EGT-QB-153 | 双塔检索与生成VLM区别；直接projector；query压缩与cross-attention；连接器shape/梯度/信息瓶颈 |
| T154 | BLIP2 的结构是什么？两阶段怎么训练的？有哪些损失？ | EGT-QB-154 | 冻结视觉与可学习query；ITC/ITM/ITG及mask；第二阶段模块/投影/梯度；decoder与encoder-decoder目标 |
| T155 | Qwen-VL 的训练流程是怎样的？三个阶段各有什么作用？相比 LLaVA、DeepSeek-VL 有什么区别？ | EGT-QB-155 | Qwen-VL两次预训练；对话SFT与监督mask；LLaVA两阶段对照；DeepSeek-VL混合视觉和冻结例外 |
| T156 | 多模态模型如何将文本和图像映射到同一向量空间？会遇到什么问题（模态鸿沟）？不在同一空间时如何对齐？ | EGT-QB-156 | 共享空间的相似度语义；模态鸿沟的信息/统计原因；projector/query/cross-attention条件对齐；任务与反事实评测 |
| T157 | LLaVA 的损失函数是什么？数据怎样清洗？Adapter / 连接器的作用是什么？ | EGT-QB-157 | 视觉encoder→projector→LLM；两阶段冻结与作用；assistant条件CE/shift；原始数据来源与工程清洗 |
| T158 | 多模态大模型幻觉的原因是什么？如何缓解？ | EGT-QB-158 | 多层成因；对象到关系的评测；数据/感知/生成干预；反事实及拒答权衡 |
| T159 | 多模态中了解哪些视觉编码器？视觉和文本编码器的参数量有什么配比逻辑？ | EGT-QB-159 | 视觉骨干与预训练路线；双塔text encoder/生成LLM区别；参数、分辨率与token账本；瓶颈诊断和配比消融 |
| T160 | Video-LLaMA 等视频多模态模型的结构是什么？多模态检索方案有哪些？ | EGT-QB-160 | 逐帧视觉到video Q-Former；ImageBind/audio Q-Former；全局/分段/多路检索；时序、同步与指标 |
