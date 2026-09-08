# AI 算法手撕专项：40 项落地与使用入口

用户 2026-09-08 整理资料已按现有 Catalog 和知识库内化。不是新增 40 个重复基础题：21 个已有 planned 节点补齐为可执行练习，18 个缺口/进阶契约使用新 ID，AdamW 复用既有 OPT-005 并强化恢复测试与追问。

新题默认中文，使用现有刷题/答题流程；知识库可搜索 AI01–AI40 或技术名。每题有明确接口、公开测试、分级提示和四层追问。数学定义以题目固定约定为准，不将社区题单当成公司考频。

## 对照表

| 资料编号 | 主题 | 可执行题目 | 处理方式 | 知识卡 |
|---|---|---|---|---|
| AI01 | 稳定交叉熵与有效 token 归约 | [PT-003](../../curriculum/problems/PT-003-masked-token-cross-entropy/task.md) | 已规划节点落地 | `COD-AI-001` |
| AI02 | 多头注意力与复合 mask | [ATT-019](../../curriculum/problems/ATT-019-projected-masked-mha/task.md) | 新增进阶/缺口节点 | `COD-AI-002` |
| AI03 | GQA 与 KV cache：增量解码一致性 | [ATT-020](../../curriculum/problems/ATT-020-gqa-incremental-cache/task.md) | 新增进阶/缺口节点 | `COD-AI-003` |
| AI04 | RoPE：旋转布局与位置偏移 | [ATT-021](../../curriculum/problems/ATT-021-rope-position-offsets/task.md) | 新增进阶/缺口节点 | `COD-AI-004` |
| AI05 | LayerNorm 与 RMSNorm | [NNL-006](../../curriculum/problems/NNL-006-last-dimension-layernorm/task.md)、[NNL-008](../../curriculum/problems/NNL-008-rmsnorm/task.md) | 已规划节点落地 | `COD-AI-005` |
| AI06 | LoRA 线性层与合并一致性 | [INF-013](../../curriculum/problems/INF-013-lora-functional-merge/task.md) | 已规划节点落地 | `COD-AI-006` |
| AI07 | temperature、top-k、top-p 的顺序与边界 | [ATT-011](../../curriculum/problems/ATT-011-ordered-sampling/task.md) | 已规划节点落地 | `COD-AI-007` |
| AI08 | DPO loss：先对齐回答 token，再比较相对偏好 | [PT-022](../../curriculum/problems/PT-022-shifted-completion-dpo/task.md) | 新增进阶/缺口节点 | `COD-AI-008` |
| AI09 | GRPO：组内优势、ratio 与 clipping | [PT-023](../../curriculum/problems/PT-023-grpo-response-mean-kl/task.md) | 新增进阶/缺口节点 | `COD-AI-009` |
| AI10 | 带 mask 的 token KL 蒸馏 | [LOSS-004](../../curriculum/problems/LOSS-004-masked-forward-kl/task.md) | 已规划节点落地 | `COD-AI-010` |
| AI11 | InfoNCE 与图文双向对比学习 | [LOSS-006](../../curriculum/problems/LOSS-006-symmetric-infonce/task.md) | 已规划节点落地 | `COD-AI-011` |
| AI12 | Packing：attention 隔离与监督隔离是两件事 | [PT-024](../../curriculum/problems/PT-024-packing-mask-isolation/task.md) | 新增进阶/缺口节点 | `COD-AI-012` |
| AI13 | K-means：确定初始化与空簇策略 | [TML-004](../../curriculum/problems/TML-004-lloyd-kmeans/task.md) | 已规划节点落地 | `COD-AI-013` |
| AI14 | ROC-AUC：同分不能按输入顺序算输赢 | [LOSS-010](../../curriculum/problems/LOSS-010-auc-with-ties/task.md) | 已规划节点落地 | `COD-AI-014` |
| AI15 | 可变长度序列的梯度累积 | [TNS-014](../../curriculum/problems/TNS-014-token-weighted-accumulation/task.md) | 已规划节点落地 | `COD-AI-015` |
| AI16 | 流式精确 attention：保存统计量，不保存完整分数矩阵 | [ATT-015](../../curriculum/problems/ATT-015-online-exact-attention/task.md) | 已规划节点落地 | `COD-AI-016` |
| AI17 | MoE Top-2：dispatch、combine 与梯度路径 | [NNL-014](../../curriculum/problems/NNL-014-top2-moe-dispatch/task.md) | 已规划节点落地 | `COD-AI-017` |
| AI18 | SwiGLU FFN：形状、门控与等参数预算 | [NNL-005](../../curriculum/problems/NNL-005-swiglu-ffn/task.md) | 已规划节点落地 | `COD-AI-018` |
| AI19 | 带确定性 tie-break 的最小 BPE | [TOK-001](../../curriculum/problems/TOK-001-deterministic-bpe/task.md) | 已规划节点落地 | `COD-AI-019` |
| AI20 | AdamW 单步更新与恢复状态 | [OPT-005](../../curriculum/problems/OPT-005-adamw/task.md) | 复用并深化 | `COD-AI-020` |
| AI21 | Softmax 前向与反向：不构造 Jacobian | [LOSS-016](../../curriculum/problems/LOSS-016-softmax-manual-backward/task.md) | 新增进阶/缺口节点 | `COD-AI-021` |
| AI22 | NumPy 手写两层 MLP 的完整反向传播 | [TML-006](../../curriculum/problems/TML-006-numpy-mlp-backprop/task.md) | 新增进阶/缺口节点 | `COD-AI-022` |
| AI23 | 逻辑回归：稳定 BCE 与一个完整训练 step | [TML-001](../../curriculum/problems/TML-001-logistic-regression-step/task.md) | 已规划节点落地 | `COD-AI-023` |
| AI24 | BatchNorm：训练与推理两套统计量 | [NNL-016](../../curriculum/problems/NNL-016-batchnorm-state/task.md) | 新增进阶/缺口节点 | `COD-AI-024` |
| AI25 | 二维卷积：先写对，再考虑 im2col | [NNL-009](../../curriculum/problems/NNL-009-conv2d-cross-correlation/task.md) | 已规划节点落地 | `COD-AI-025` |
| AI26 | IoU 与 NMS：坐标、同分和阈值都要写清 | [CV-002](../../curriculum/problems/CV-002-deterministic-nms/task.md) | 已规划节点落地 | `COD-AI-026` |
| AI27 | PCA：训练集拟合与测试集变换 | [TML-007](../../curriculum/problems/TML-007-pca-fit-transform/task.md) | 新增进阶/缺口节点 | `COD-AI-027` |
| AI28 | KNN 分类与余弦近邻检索 | [TML-008](../../curriculum/problems/TML-008-knn-and-cosine/task.md) | 新增进阶/缺口节点 | `COD-AI-028` |
| AI29 | Beam Search：候选分数、EOS 与缓存重排 | [ATT-022](../../curriculum/problems/ATT-022-beam-search-eos/task.md) | 新增进阶/缺口节点 | `COD-AI-029` |
| AI30 | PPO loss：策略、价值、熵分别实现 | [PT-009](../../curriculum/problems/PT-009-ppo-loss-components/task.md) | 已规划节点落地 | `COD-AI-030` |
| AI31 | GAE：终止、截断与序列边界 | [PT-010](../../curriculum/problems/PT-010-gae-boundaries/task.md) | 已规划节点落地 | `COD-AI-031` |
| AI32 | Dropout 的前向、反向与训练模式 | [NNL-017](../../curriculum/problems/NNL-017-inverted-dropout/task.md) | 新增进阶/缺口节点 | `COD-AI-032` |
| AI33 | 按通道 INT8 量化与反量化 | [INF-008](../../curriculum/problems/INF-008-channel-int8-quantization/task.md) | 已规划节点落地 | `COD-AI-033` |
| AI34 | GAUC：先分组，再说明权重口径 | [REC-007](../../curriculum/problems/REC-007-group-weighted-auc/task.md) | 新增进阶/缺口节点 | `COD-AI-034` |
| AI35 | NDCG@K：排序指标的 gain 与 tie 策略 | [REC-008](../../curriculum/problems/REC-008-ndcg-tie-contract/task.md) | 新增进阶/缺口节点 | `COD-AI-035` |
| AI36 | 完整 Decoder Block：把组件真正接起来 | [ATT-008](../../curriculum/problems/ATT-008-pre-norm-decoder-cache/task.md) | 已规划节点落地 | `COD-AI-036` |
| AI37 | K-means++ 初始化 | [TML-009](../../curriculum/problems/TML-009-kmeans-plus-plus/task.md) | 新增进阶/缺口节点 | `COD-AI-037` |
| AI38 | DIN 局部激活与兴趣聚合 | [REC-009](../../curriculum/problems/REC-009-din-local-activation/task.md) | 新增进阶/缺口节点 | `COD-AI-038` |
| AI39 | ViT Patch Embedding 与卷积等价性 | [VLM-001](../../curriculum/problems/VLM-001-patch-linear-projection/task.md) | 已规划节点落地 | `COD-AI-039` |
| AI40 | 最小标量自动微分引擎 | [TNS-017](../../curriculum/problems/TNS-017-scalar-autodiff-dag/task.md) | 新增进阶/缺口节点 | `COD-AI-040` |

## 五条推荐路线

推荐顺序写入 Catalog quests，不要求把每一步都变成硬前置。新题的硬前置只保留已有可验证复测、能够真正达成的基础节点；尚无复测资产的相关题放在题面“推荐准备”中，不锁死后续练习：

- `ai_handwriting_transformer`：稳定梯度、损失、完整投影、归一化、RoPE、FFN、LoRA、AdamW、Decoder。
- `ai_handwriting_post_training`：回答对齐、PPO、GAE、GRPO 参考惩罚、KL 蒸馏和 token 归约。
- `ai_handwriting_inference`：GQA cache、位置、采样、beam、在线 attention、MoE、INT8。
- `ai_handwriting_ml_recs`：手写 BP、传统机器学习、AUC/GAUC/NDCG、DIN、自动微分。
- `ai_handwriting_vision`：卷积、Patch、BatchNorm、NMS、双向 InfoNCE。

NumPy 题在没有 PyTorch 时也可训练，须有 NumPy。源码安装可用 `pip install -e ".[numpy]"`；桌面依赖已经包含 NumPy。缺少 NumPy 时入口说明环境缺失，不把它标成标准库题。

## 面试使用方式

40 张技术卡记录定义、边界、追问与证据标准；17 张面经模式卡记录项目→原理→实现的观察。动态面试按已发生的回答逐问推进，岗位技能的追问描述同步深化；代码候选只能来自实际验证题目，不从链接臆造题号。

算法岗补齐既有“基础层 / 分词 / 生成”技能及 VLM 路线，解决相关题目没有任何适用面试候选的问题。没有新增 Role 或 Skill ID；技能覆盖率会按补齐后的要求计算，旧 Profile、作答和学习事件不迁移、不自动加分。产品岗不被强制加入算法专项。

数学与形状、实现/梯度、mask/状态边界、解释与自测分别取证。主观评估允许“不完整但核心逻辑合理”，不能冒充单测通过，也不改变 Mastery。困难体现在机制、反例与条件变化，不是强行追加生僻术语或扣分。

## 来源边界

原资料有 17 篇面经索引，不等于 17 名独立候选人。MJ05/MJ14 同作者；MJ11/MJ12/MJ13 保守按可能同作者合组；MJ15–MJ17 同作者，MJ16/MJ17 为同岗位续轮。未标明的年份不补全，“熊厂”不猜公司。自动驾驶案例不是通用算法岗标准。

本轮复核可读的示例：字节 MJ01、网易有道 MJ05。部分原页只能取得索引或正文获取不稳定，不能据此宣称全部来源核验通过。其余保留用户整理的摘要与日期口径，标明未完成独立全文复核。只保存链接和摘要，不复制付费/受限内容或第三方实现。

来源与声明统一位于 [知识库](../../curriculum/interviews/knowledge.yaml)，不维护另一份题库事实源。

## 验证与诚实限制

2026-09-08 本地验收：40 项参考实现全部通过，共 **226 个公开用例、63 个私有用例**；最终关联检查 **33 passed / 1 skipped**，另知识库领域检查通过。跳过的是 Windows 缺少符号链接创建权限的安全测试，不是题目验证。运行环境为 Python 3.11、NumPy 2.4.6、PyTorch 2.13.0 CPU。没有运行全量 pytest、CI 或 Windows/macOS 构建。

每个新题先运行真实公开测试和独立私有验证，再将 Catalog 标为 oracle，并记录内容 fingerprint。私有参考和报告仅位于 ignored 维护者 Workspace，不进入源码或运行资产。本轮只验证 CPU/NumPy/PyTorch 题目，不声称 GPU 性能或真实面试效果已经验证。

资料中的九组参考实现没有作为公开答案发布。D+2/D+7 当前提供重写/迁移方向，未提供新增的独立自动复测包；不会将提示中的方向标成已通过的 retention 证据。原有复测资产不变。
