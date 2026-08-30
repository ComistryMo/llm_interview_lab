# 大模型后训练与 Agent 面试来源审计

> 审计日期：2026-08-30（UTC）。本页只登记公开网页的事实性摘要、题型信号和链接，**不复制面经原文、答案、付费内容或雇主内部资料**。页面会更新或下线；日期是页面显示的发布日期/岗位发布日期，无法确认时明确标注“未显示”。

## 如何使用

- **A（高）**：官方招聘页、官方技术文档、同行评议/原始论文。可用于定义能力边界和核验公式；不是面试题保证。
- **B（中）**：个人面试实录（牛客、CSDN、掘金等），有日期/轮次/题目。只能作为题型频率信号，答案须回到 A 类来源核验。
- **C（低-中）**：聚合题库、教辅或无日期转载。用于扩展变式，不作为事实或公司流程证据。
- 版权：官方页面采用“链接+短摘要”；CSDN/Juejin 的 CC BY-SA 或未知许可页面只做改写并保留署名链接，不复制段落。题面、starter、测试和 rubric 由本项目 clean-room 重写。

## 官方岗位与技术来源（A）

| 来源（日期） | 页面可核验的能力信号 | 适合内化的题型/技能 |
|---|---|---|
| [上海 AI Lab：大模型训练算法工程师](https://www.shlab.org.cn/joinus/detail/7615234376275773734?mode=social)（2026-08-13） | CPT/SFT/RLHF/DPO 全流程；数据清洗、偏好数据和配比；Megatron-LM、veRL、LLaMA-Factory；loss/梯度异常监控；7B+ 微调、DP/TP/PP、实验与 badcase | SFT mask/配比、DPO/偏好数据、分布式显存、训练排障 |
| [上海 AI Lab：智能体算法工程师/青年研究员](https://www.shlab.org.cn/joinus/detail/7553291568346728758?mode=social)（2026-08-27） | 轨迹、tool-call、environment、多轮/code/security/science 数据；规划、长上下文、function calling、验证、自反思/错误恢复；BrowseComp、SWE-Bench、Security Bench、DeepResearch 评测；vLLM/Ray/Docker | Agent trajectory、工具协议、可靠性/回归评测、RLAIF/合成数据 |
| [百度校招岗位列表](https://talent.baidu.com/jobs/list?recommendCode=IS96J8&recruitType=GRADUATE)（岗位 2026-07-21） | J101017 智能体：规划、复杂推理、动态决策、意图、多步工具、长短记忆、多 Agent、自进化和效果/效率/成本评测；J100728 大模型：预训练+SFT/RLHF、RL/RAG/CoT、数据策略 | Agent 系统设计、离线/在线指标、SFT/RLHF 选择题 |
| [字节：大模型算法专家—国际化搜索内容安全](https://jobs.bytedance.com/experienced/position/7636705823246305589/detail)（页面当前） | 预训练、SFT、RLHF/DPO/PPO/GRPO、Reward/Preference Model、安全、推理、Agent、RAG | 全链路后训练、安全 reward、RAG/Agent 情景题 |
| [字节：多模态应用算法实习生（即梦 AI）](https://jobs.bytedance.com/campus/position/7673846473887025413/detail)（页面当前） | GRPO/OPD 后训练、reward modeling、多候选采样/路由；视频生成质量、时序稳定、推理效率评测 | 多模态 reward、视频采样与评测、路由/成本 |
| [字节：AI Agent 算法专家—国际化电商](https://jobs.bytedance.com/experienced/m/position/detail/7649590610229954821/detail)（页面当前） | 规划调度、工具使用、多模态交互、DeepResearch；关注 Codex/OpenClaw/Hermes/ClaudeCode 类 Agent | 规划器、工具编排、研究型 Agent 评测 |
| [字节：AI Agent Harness—TRAE](https://jobs.bytedance.com/experienced/position/7578857581408061701/detail)（页面当前） | Tool-Calling、多轮规划/执行、上下文检索与编排 | schema、上下文压缩、失败重试和熔断 |
| [字节：AIGC 后训练算法专家—智能创作](https://jobs.bytedance.com/experienced/position/7393308002855422246/detail)（页面当前） | GRPO/PPO/DPO；判别式/生成式 reward model | 算法目标比较、RM 设计 |
| [字节：语音/多模态大模型—Speech/Omni/Agent](https://jobs.bytedance.com/experienced/position/7654893302257551669/detail)（页面当前） | Agent 系统、复杂推理/规划、多 Agent、反馈学习对齐 | 多模态 Agent、反馈学习、端到端延迟 |
| [阿里：算法工程师—大模型评测](https://campus-talent.alibaba.com/campus/position/199907620028)（2026-08-06） | Transformer/LLM 基础；评测或 SFT/RLHF/DPO；训练与推理 | 评测设计、SFT/DPO 取舍、推理诊断 |
| [阿里：算法工程师—强化学习](https://campus-talent.alibaba.com/campus/position/199903180013)（2026-03-22） | Reward Model、PPO/DPO/GRPO/MBRL 与训练系统 | RL 目标、采样、分布式工程 |
| [阿里：AI Agent 优化工程师—训练/数据/评测](https://campus-talent.alibaba.com/campus/position/199903500011)（2026-03-19） | data-centric 质量、后训练数据、评测闭环 | 数据筛选、指标回归、实验设计 |
| [阿里：MaaS 多模态 AI 搜索](https://campus-talent.alibaba.com/campus/position/199907720111)（2026-07-30） | 多模态搜索问答、SFT/偏好优化/RLHF-DPO-GRPO | 多模态检索、偏好数据、GRPO |
| [阿里：医疗 AI 基础模型与智能体](https://campus-talent.alibaba.com/campus/position/199907820099)（2026-07-30） | 多模态 Agent、多步推理/工具/反思与垂直评测 | 工具可靠性、领域安全评测 |
| [腾讯：Senior Researcher, Multi-Modality](https://careers.tencent.com/jobdesc.html?postId=2078016971789746176)（页面当前） | SFT、RLHF/RLAIF、reward model、偏好对齐以提升能力/可靠性 | RLAIF 与 RLHF、RM 训练 |
| [腾讯：混元后训练算法工程师—RM](https://careers.tencent.com/jobdesc.html?postId=2046923451989651456)（页面当前） | Transformer、alignment、RLHF/RM、SFT/Self-Instruct 数据合成 | RM/偏好数据、合成数据质量 |
| [腾讯：后训练算法岗位](https://careers.tencent.com/jobdesc.html?postId=2072330936011374592)（页面当前） | PPO/GRPO/DPO；veRL、ROLL、AReal 分布式 RL 框架 | 框架选型、rollout/训练解耦 |
| [腾讯：后训练算法岗位（RLVR）](https://careers.tencent.com/jobdesc.html?postId=2092149663925977088)（页面当前） | SFT/RLHF/PPO/GRPO/RLVR、Verifier/Reward Model | 可验证奖励、过程/结果奖励 |
| [阿里官方：LLM 微调实践](https://www.alibabacloud.com/help/en/pai/llm-fine-tuning-experience)（更新 2026-07-15） | SFT/DPO 阶段、chosen/rejected 三元组、beta、LoRA/QLoRA、数据质量与超参 | DPO 公式、数据契约、显存与超参排障 |
| [滴滴：客服 Agent 后训练算法](https://talent.didiglobal.com/social/p/62068)（页面近 2026-08-26 更新） | 客服 Agent 底层模型设计/训练；数据流、SFT、DPO、GRPO、CPT | 场景化后训练闭环、数据流和线上指标 |
| [滴滴：大模型专家算法工程师](https://talent.didiglobal.com/social/p/59461)（页面当前） | 奖励信号建模、PPO/DPO/GRPO，OpenRLHF/veRL | RM/奖励建模与 RL 框架工程 |
| [滴滴：Post-Training 框架研发专家](https://talent.didiglobal.com/social/p/55737)（页面近 2026-08-24 更新） | RM/PPO/DPO/GRPO；OpenRLHF、verl 框架开发 | 分布式 RL 框架、rollout/训练接口 |
| [MiniMax：M2.1 Agent 模型后训练经验](https://www.minimax.io/news/post-training-experience-and-insights-for-agent-models)（2026-01-22） | GitHub PR/Commit → 可运行 Docker → F2P/P2P 的可验证数据；多脚手架 SFT/RL；Agent-as-Verifier；Forge 将 Agent、Gateway/Data Pool、rollout 和训练解耦；过程/时延/reward-to-go 复合奖励 | Agentic 数据合成、Verifier、长轨迹 credit、异步调度与 off-policy、脚手架泛化 |
| [Moonshot：Kimi-Researcher 端到端 Agentic RL](https://moonshotai.github.io/Kimi-Researcher/)（2025-06-20） | tool-centric 与 hard-search 合成数据、GT/Pass@N 过滤；REINFORCE 与 strict on-policy；负样本控制防 entropy collapse；format/correctness reward 与 gamma 衰减；context management、全异步/turn-level partial rollout、MCP sandbox | 动态环境、长轨迹数据与信用分配、训练稳定、rollout 长尾和工具故障 |
| [美团：Agent 评测漫谈](https://tech.meituan.com/2026/08/07/Agent-Evaluation.html)（2026-08-07） | 图灵评测团队两年实践；评测体系与长程 Agent 变化 | 评测分层、LLM judge 偏差、长期记忆/任务回归（官方科普，A） |
| [美团：VitaBench 2.0 长期动态 Agent 基准](https://tech.meituan.com/2026/06/29/LongCat-VitaBench-2.0.html)（2026-06-29） | 56 拟真用户、819 任务、>2000 动态偏好、66 工具；平均 2093 交互/1580 天；比较全历史、Agentic Memory、RAG Memory 与主动提问 | 偏好漂移、记忆更新/召回、长期个性化评测（官方指标需注明自报） |
| [美团：LongCat-Flash-Thinking-2601 多环境 RL](https://tech.meituan.com/2026/01/20/LongCat-Flash-Thinking-2601.html)（2026-01-20） | 随机工具环境自动合成与 OOD 泛化；DORA 异步多环境 RL；注入 API 失败/异常/缺失并课程学习 | 噪声鲁棒、重试/熔断、curriculum、Agent benchmark（官方，A） |
| [美团：LoHoSearch 搜索 Agent 基准](https://tech.meituan.com/2026/07/24/LongCat-LoHoSearch.html)（2026-07-24） | 知识图谱自动出题（762 万实体/2.65 亿边、544 人工核验题、11 领域）；按搜索空间与结构复杂度控难度 | benchmark 构造、难度/污染控制、长程搜索评测（官方，A） |
| [字节：Agent 算法工程师—AI Platform](https://jobs.bytedance.com/experienced/m/position/detail/7599598898747656453)（页面当前） | 工具、上下文管理、编排等 Agent 架构优化；Agentic RL 等任务后训练 | Agent harness 与模型协同优化、上下文/工具/训练闭环 |

## 原始论文与官方框架（A，答案核验锚点）

| 来源 | 关键事实（改写） | 面试能力 |
|---|---|---|
| [InstructGPT](https://arxiv.org/abs/2203.02155)（2022-03-04） | SFT → 人类偏好比较训练 RM → PPO；KL 约束和人类偏好改善对齐 | 能解释三阶段数据流、RM 与 PPO 的接口 |
| [DPO](https://arxiv.org/abs/2305.18290)（2023-05-29） | 将最优策略关系化为偏好分类损失；训练时不显式拟合 RM/在线 rollout | 推导 log-ratio、reference、beta、长度偏差 |
| [DeepSeekMath/GRPO](https://arxiv.org/abs/2402.03300)（2024-02-05） | 同一 prompt 采样一组回答，以组均值/方差构造相对优势，省去独立 critic | group size、零方差、clip/KL、credit assignment |
| [DeepSeek-R1](https://arxiv.org/abs/2501.12948)（2025-01-22） | R1-Zero 直接 RL；R1 采用冷启动和多阶段推理 RL/监督数据 | SFT 与 reasoning RL 的边界、可验证奖励 |
| [Constitutional AI](https://arxiv.org/abs/2212.08073)（2022-12-15） / [RLAIF 对比](https://arxiv.org/abs/2309.00267) | AI 依据原则批评/修订并生成偏好，再做 RL；在部分设置中可接近 RLHF | RLAIF 数据闭环、偏差/安全风险 |
| [DAPO](https://arxiv.org/abs/2503.14476)（2025-03-18） / [verl recipe](https://verl.readthedocs.io/en/latest/algo/dapo.html)（2025-06-19） | 解耦上下 clip、Clip-Higher、动态采样等，针对长 CoT 稳定与样本效率 | GRPO 变体、熵坍塌、全 0/全 1 reward prompt 处理 |
| [GSPO](https://arxiv.org/abs/2507.18071) / [Qwen 官方说明](https://qwenlm.github.io/blog/gspo/)（2025-07-24/27） | 以序列似然计算 importance ratio，序列级 clip/reward/update，改善 MoE RL 稳定性 | token vs sequence ratio、MoE 训练稳定与效率 |
| [MiniMax-M1/CISPO](https://arxiv.org/abs/2506.13585)（2025-06-17） / [NVIDIA CISPO 文档](https://docs.nvidia.com/nemo/rl/latest/guides/cispo.html) | 直接裁剪 detached importance 权重而非 PPO 式目标，保留所有 token 的 logπ 梯度 | off-policy/stale rollout、梯度保留与方差权衡 |
| [Kimi K2 技术报告](https://arxiv.org/html/2507.20534v1)（2025-07-28） | Agentic SFT 数据综合覆盖 tool/domain、agent/task、rubric、trajectory、过滤与真实执行；RLVR + self-critique rubric reward；预算控制/PTX/温度衰减；colocated 训推切换 | RLVR、近 RLAIF 的自评奖励、Agent 数据、rollout/engine switching（页面标 CC BY-NC-ND，仅摘要） |
| [GLM-4.5 技术报告](https://arxiv.org/abs/2508.06471)（2025-08-08） | expert-model iteration 与 RL 的综合 post-training；Agent/Reasoning/Coding 和 TAU/SWE 等评测 | 多阶段后训练、Agent benchmark 与评测边界 |
| [AgentBench](https://arxiv.org/abs/2308.03688) / [Agent 评测综述](https://arxiv.org/html/2507.21504) | 多环境、任务完成和交互能力的系统评测 | success/tool accuracy/成本/鲁棒性指标 |
| [Hugging Face TRL](https://huggingface.co/docs/trl/en/index)（官方文档） | SFT、DPO、GRPO、PPO、RM 的训练器和数据契约 | API 与实现边界；不要把 Trainer 当作算法解释 |
| [verl](https://github.com/verl-project/verl) / [文档](https://verl.readthedocs.io/) | ByteDance Seed 发起；PPO/GRPO，FSDP/Megatron 与 vLLM/SGLang，控制/计算解耦 | rollout 版本、异步/分布式故障排查 |
| [vLLM](https://docs.vllm.ai/en/latest/) | PagedAttention、连续批处理、chunked prefill、prefix cache、CUDA graphs | KV/cache、吞吐/延迟、显存分析 |
| [DeepSpeed ZeRO](https://www.deepspeed.ai/tutorials/zero/) | Stage 1 分片优化器，Stage 2 再分片梯度，Stage 3 再分片参数 | 显存估算、通信/吞吐权衡 |
| [OpenRLHF 官方仓库](https://github.com/OpenRLHF/OpenRLHF) / [论文](https://arxiv.org/abs/2405.11143)（Apache-2.0） | Ray+vLLM+ZeRO-3；统一 Agent token-in/token-out；PPO/DPO/GRPO/RLOO；跨 70B+ 模型调度 | RLHF 组件布局、hybrid engine、权重同步与 batch 参数 |
| [阿里 ROLL](https://github.com/alibaba/ROLL) / [官方文档](https://alibaba.github.io/ROLL/)（Apache-2.0） | PPO/GRPO、多任务与多轮 Agent；Megatron-Core、SGLang、vLLM 加速 | 分布式 RL、并行 worker/rollout scheduler、框架选型 |
| [腾讯 UniRL](https://github.com/Tencent-Hunyuan/UniRL)（开源仓库） | 统一多模态 RL loop：生成→打分→优势→策略更新→权重同步 | VLM/LLM 共用后训练接口与数据契约 |
| [蚂蚁 AReaL](https://github.com/areal-project/AReaL) / [论文](https://arxiv.org/abs/2505.24298)（2025-05-30） | 全异步生成/训练解耦，控制数据陈旧度并用 staleness-enhanced PPO；报告同卡最高 2.57× 加速 | 异步 RL、off-policy/staleness、吞吐与稳定权衡 |

## 公开面经题型证据（B/C）

以下均为个人自报或聚合页面；题目已改写为关键词，不代表对应公司的固定题库。

| 来源（日期/可信度） | 反复出现的问题（摘要） | 能力标签 / 版权处理 |
|---|---|---|
| [牛客：字节大模型算法岗面经-04](https://www.nowcoder.com/discuss/922308546966847488)（页面 2026-04-14，B） | GRPO 与 DPO/PPO 及变体；PPO 数据、RM、loss；DPO 公式、PPO+DPO、multi-round/ablation；RL 数据过滤、LoRA 显存、KV cache；Agent 分层路由、延迟/chunk、手写 Transformer/FLOPs | 后训练公式、实验设计、推理优化；牛客用户内容，仅摘要+链接 |
| [牛客：字节大模型算法实习一面](https://www.nowcoder.com/feed/main/detail/a8c7e2e30eed4b669b33ac4182b6d75d)（日期未显示，B） | 意图/多意图漂移、RAG 意图识别；3B 质量但避免实时推理；vLLM 优势；Qwen judge 消融/交付指标；DPO 正反馈来源；无 reference、rollout reward=0 排障 | 意图路由、评测、RL 排障；不复制原文 |
| [牛客：腾讯混元大模型面经](https://www.nowcoder.com/feed/main/detail/56dd98494551469b9c069d4fe149e080)（日期未显示，B） | Qwen/DeepSeek、MoE/Dense；LoRA/全参；ZeRO-1/2/3 与 72B 显存；SFT/RLHF；RL loss、GRPO；数据清洗/配比；括号、子串、零钱、概率/反传 | 模型基础、分布式、手撕；个人内容摘要 |
| [牛客：阿里大模型算法岗面经-01](https://www.nowcoder.com/discuss/923309531445071872)（2026-07-17 等，B） | SFT 过滤/采样；GRPO 目标/奖励/cheating；Attention/KV/GQA/MLA/vLLM/FlashAttention；rand7→rand10、浮点、子串；小模型+RL、视频视觉 token、stale policy、自演化错误、多目标 reward | reward 设计、系统诊断、手撕；用户内容摘要 |
| [牛客：RLHF 八股总结](https://www.nowcoder.com/feed/main/detail/20e8f456d0c5418cad2b46b39c0d0f61)（2025-12-04，C） | RLHF vs SFT；SFT/RM/PPO 三阶段；RM loss；PPO/KL；reward hacking；DPO vs PPO | 仅作检查清单；答案回链 InstructGPT/DPO；不照抄 |
| [牛客：字节大模型算法岗面经-03](https://www.nowcoder.com/discuss/921960727672299520)（2026-04-23 至 05-02，B） | GRPO/DAPO/GSPO；CoT 数据构造/过滤；advantage/组大小；loss 降但 F1 不升；最大 1 矩阵、队列 | 新近 RL 变体、数据和指标诊断、手撕 |
| [牛客：腾讯 WXG 暑期实习面经](https://www.nowcoder.com/feed/main/detail/d3c8e5962e1b43aab21aa5af52423b56)（轮次/时长明确，B） | AdamW、SQL、大数据敏感词；GRPO/PPO/RM、MDP、bf16/fp16/fp32、LoRA/量化；手写 PPO、SFT 参数/GPU 利用率、链表 | 优化器、数值精度、算法推导和手撕；摘要 |
| [牛客：字节面经-01](https://www.nowcoder.com/discuss/922309082860507136?urlSource=home-api)（含 2026-08-07/07-20，B） | 视频/视觉幻觉及后训练/RAG/规则；Agent trajectory 与语料；GRPO clipping；DPO/GRPO 框架问题；最长有效括号、岛屿 DFS/BFS | 多模态、Agent、手撕；摘要 |
| [牛客：Minimax 大模型算法面经](https://www.nowcoder.com/feed/main/detail/0380bd3ab1ba40f48865eeff2d15d746)（页面 05-06，年份未显示，B） | RAG→Agent、长对话 Attention 局限、SFT/RLHF/DPO/GRPO；规划/工具调度/fallback；Agent 评测规划 vs 幻觉；Qwen 微调 loss；三工具高频延迟；LoRA 推理 adapter | Agent 设计、延迟/评测、LoRA；用户内容摘要 |
| [牛客：蚂蚁金服一二面](https://www.nowcoder.com/feed/main/detail/c1f9b7cec4eb4d1ea27f86416daa89f0)（2025-11-05，B） | PPO/DPO；verl batch 参数关系；reward/critic；GRPO/DAPO/GSPO；beam 树；蒸馏清洗；FlashAttention/vLLM 训推一致性；GPTQ/QAT/W8A16；PPO+GAE；GRPO KL/DAPO 去 KL；K 链表 | RL 框架参数、GAE、量化与手撕；用户内容摘要 |
| [牛客：月之暗面 AI Agent 开发岗一面](https://www.nowcoder.com/discuss/922643334898647040?sourceSSR=%E5%85%B6%E4%BB%96)（标注 2026-07-21，B/C） | Agent 四层（规划/执行/schema/状态记忆/观测评测）；上下文预算与压缩；长短记忆按需注入；progressive tool disclosure；RAG 召回/rerank；幻觉、权限、重试/审批；手撕链表 | 系统设计与可靠性；页面含完整答案，严格只记主题并遵守用户内容版权 |
| [CSDN：百度文心一言 Agent 面经](https://blog.csdn.net/2401_84033492/article/details/146127035)（更新 2026-08-05，B） | Transformer/位置编码；预训练/后训练/推理；RLHF/PPO/DPO；长上下文；Agent 组件；数据清洗/比例、幻觉、工具调用；股票 DP、tokenizer | Agent 深挖、数据、手撕；页面 CC BY-SA，保留链接并改写 |
| [CSDN：Agent 项目拷打实录](https://blog.csdn.net/Python_cocola/article/details/160830767)（更新 2026-08-26，B） | 多 Agent vs 单 Agent；记忆压缩、多模态记忆；RAG 混合召回/rerank；GRPO/PPO/DPO、credit assignment；reward hacking；异步/流式/小模型路由/cache/vLLM；MCP/JSON tool、重试/熔断；回文子串 | 系统设计与故障恢复；CC BY-SA，仅摘要 |
| [掘金：大模型训练岗面经](https://juejin.cn/post/7648887289629179958)（2026-06-08，B） | NaN/梯度尖峰、数据 shard/ZeRO/lr；DP/TP/PP；SFT 数据质量/过拟合；RAG/Agent/eval；VLM 三阶段 | 训练排障、并行和多模态；改写+链接 |
| [GitHub AgentGuide 12-company cases](https://github.com/adongwanai/AgentGuide/blob/main/docs/04-interview/12-company-interview-cases.md)（C） | RLHF/SFT；CoT/ToT/GoT；多 Agent、规划/工具/记忆/RAG/评测；LoRA/QLoRA；vLLM/KV；MoE 负载；MHA/3Sum | 仅聚合题型，不当作原始证据；检查仓库许可证后再引用 |
| [Datawhale hello-agents 面试总结](https://github.com/datawhalechina/hello-agents/blob/main/Extra-Chapter/Extra01-%E9%9D%A2%E8%AF%95%E9%97%AE%E9%A2%98%E6%80%BB%E7%BB%93.md)（基于 2025 秋招，C/B） | reward hacking；DPO vs PPO/RLHF；offline 高 reward→online 谄媚；GRPO、GSPO/DAPO；token/sequence credit；RLAIF 风险 | 题型清单；技术答案回链论文；不复制 |
| [learn-cs336 面经汇总](https://github.com/bcefghj/learn-cs336/blob/main/interview/06-%E9%9D%A2%E7%BB%8F%E6%B1%87%E6%80%BB.md)（C/B） | DeepSeek-R1 vs SFT/RLHF、cold start/GRPO；Decoder-only；LoRA；DPO 数据源；RAG/embedding/手撕 LCA | 基础与推理 RL；聚合内容摘要 |

## 题型到本项目资产的映射

当前已有 `PT-001/002/006/014/015`（SFT label/logprob、DPO、GRPO）和 `AGT-001/002/006/009`（tool schema/registry/loop/trajectory）。面经证据建议转为以下**原创** oral/coding/system 变式：

1. **RLHF/PPO**：ratio/clipping、GAE/value、KL 与 entropy；排障 reward=0、NaN、熵坍塌、stale rollout。
2. **Reward Model / RLAIF**：pairwise loss、校准、AI 原则/合成偏好、偏差与安全；process vs outcome reward、multi-objective 聚合。
3. **DPO/GRPO 变式**：reference 梯度泄漏、长度偏置/SimPO、group size/零方差、token-level credit、DAPO/GSPO 概念对比。
4. **Agent 系统**：规划→schema/权限→记忆/RAG→执行→重试/熔断→观测；MCP 与 JSON function calling；单/多 Agent 取舍。
5. **评测与交付**：task success、tool-call accuracy、recall@K、LLM judge 偏差、延迟/成本、灰度和回归；离线指标与线上收益不一致的诊断。
6. **训练/推理工程**：ZeRO/FSDP/TP/PP 显存与通信；vLLM PagedAttention/continuous batching/prefix cache；视频采样/视觉幻觉。
7. **手撕簇**：PyTorch SFT shift-right、MHA/causal mask、PPO/AdamW；岛屿、子串/括号、链表/区间、rand7→rand10、股票 DP、tokenizer、SQL。

### 版权与证据边界

面经是未验证的用户生成证据，不应写入固定 Catalog 作为“官方题目”。固定题的题面、starter、测试、提示和 rubric 必须独立创作；`sources` 字段优先引用上面的 A 类论文/官方文档。若引用 CC BY-SA 页面，只保留事实性短摘要、作者/站点和 URL，并遵守署名与相同许可；许可证不明或付费页面不抓取、不转载。

## 追加核验（2026-08-30）

以下三份中文团队技术报告补充了“推理模型 + Agentic RL”链路，均为 A 类原始论文/官方报告；只保留事实性摘要，不复制正文、表格或代码。

| 来源（日期） | 可核验事实 | 可转化的原创面试题 | 可信度/版权 |
|---|---|---|---|
| [Qwen3 Technical Report](https://arxiv.org/html/2505.09388v1)（2025-05-14） | 四段后训练：Long-CoT cold start、Reasoning RL（3,995 query-verifier pairs，GRPO）、thinking-mode fusion SFT、general RL；三类奖励（规则、带参考答案的模型评分、无参考答案 RM）；Agent RL 在真实环境执行多轮工具；off/on-policy 蒸馏与 thinking budget。 | 为什么要 query/response 双重过滤？off-policy 与 on-policy 蒸馏怎样影响探索？三类 reward 何时选用？如何做 thinking-mode 模板/预算一致性和 BFCL/LiveCodeBench 评测？ | A；arXiv 页面允许链接与事实改写，避免逐字引文。 |
| [Seed-Thinking-v1.5](https://arxiv.org/html/2504.13914v2)（2025-04-10；v2 2025-04-22）及 [官方技术公告](https://seed.bytedance.com/en/blog/bytedance-s-latest-thinking-model-seed-thinking-v1-5-technical-details-disclosed)（2025-04-14） | 将可验证/不可验证数据、双轨奖励（verifier 与偏好比较）、VAPO/DAPO 和 streaming partial-trajectory rollout 结合；训练采用 TP/EP/CP+FSDP，报告异步迭代与故障恢复。 | 规则 verifier 与偏好 RM 如何融合？为何长链 RL 易崩、如何做 entropy/数据分布控制？异步 partial rollout 的 stale policy、优先级队列和恢复如何设计？ | A；论文/官方公告只做摘要，性能数字需保留实验条件。 |
| [Qwen3-Coder-Next Technical Report](https://arxiv.org/pdf/2603.00729)（2026-03-03） | 80B 总参数、3B 激活；通过大规模可执行 coding task 合成、可复现环境、mid-training+RL 学习工具调用与故障恢复；在 SWE-Bench/Terminal-Bench 等 Agent benchmark 评估。 | 如何构建可复现执行环境和防止测试泄漏？环境反馈如何转成 process/outcome reward？长程代码 Agent 的失败恢复、工具权限、轨迹回放与成本指标怎么测？ | A；arXiv 仅链接+事实摘要，禁止复制代码/测试。 |

这三份报告与面经的交叉信号可归纳为：**数据可验证性 → 轨迹/工具环境 → 奖励与信用分配 → 异步训练稳定性 → 任务成功、成本和回归评测**。项目新增题目应沿这条链路独立设计，并把公司/个人面经仅作为题型线索。

### 面经增量（检索日 2026-08-30）

| 来源（日期/层级） | 题型信号（改写） | 内化边界 |
|---|---|---|
| [牛客：拼多多 AI Agent 两轮技术面经](https://www.nowcoder.com/discuss/919634965879324672)（页面标 2026-08-16，B/C） | SFT 流程与 PPO/DPO/GRPO 取舍；Agent/RAG/多模态项目追问；手撕中等题。页面含完整答案，具体经历无法独立验证。 | 只记主题和问题类别，不复制答案；将可信度标为个人自报/聚合。 |
| [牛客：阿里大模型算法岗面经-03](https://www.nowcoder.com/discuss/923310078462005248)（2026-03-18–03-26，B） | NCCL timeout 与底层调试；RL+MoE 路由被 reward 带偏；CUDA fusion/warp specialization；Agent/RAG 与视频后训练 GRPO；MHA/LRU 手撕。 | 适合设计训练排障、MoE reward、Agent 评测和 coding 变式；不称为阿里固定题库。 |
| [掘金：GRPO 训练数据能直接复用 SFT 吗？](https://juejin.cn/post/7658185170866044962)（2026-07-04，C/教辅案例） | “数据同源但不同用”问题：GRPO 需可验证性、合适难度分布、Prompt/轨迹格式；过度 SFT 可能压缩探索。 | 作为概念讨论线索，答案回链 GRPO/Qwen3 等 A 类来源；文章含场景化叙述，不能视为真实面试记录。 |
| [CSDN：2026 最新字节大模型岗面经汇总](https://blog.csdn.net/qq_45717425/article/details/160315245)（2026-04-19，C/聚合） | PPO 数据/RM/Critic/GAE/reference；DPO/GRPO 数据格式、正负样本不对称、收敛排障；vLLM/SGLang/KV cache/量化；Multi-Agent 通信、A2A 递归和 LLM judge。 | 只作题型交叉验证，CC BY-SA/转载风险高；不复制题库原文或答案。 |

### 官方招聘增量（检索日 2026-08-30）

| 来源（日期/层级） | 岗位能力信号 | 面试准备映射 |
|---|---|---|
| [华为云算法创新 Lab 校园招聘](https://www.huaweicloud.com/lab/algorithm/campus_recruitment.html)（页面 ©2026，A） | AI 算子、训练、推理、应用、集群和多模态多个方向；明确 FlashDecoding/PagedAttention/MoE、AllReduce/AllGather、AscendC/Triton/TileLang/CUDA、Nsight/Perfetto；训练岗含 MTP/Eagle3、量化蒸馏、Megatron/DeepSpeed、SFT/RLHF/DPO；推理岗含 PTQ/QAT、KV 压缩、Prefill/Decode 分离、continuous batching/chunked prefill、vLLM/SGLang/TGI/TensorRT-LLM；应用岗含 K8s/Volcano/KubeRay、AB/LLMOps。 | 训练/推理/Agent 岗共用底层题：显存与通信估算、PagedAttention、PD 分离、量化和性能剖析；算子岗增加 CUDA/AscendC kernel、profiling 与数值正确性。JD 是需求证据，不是面经。 |
| [智谱 GLM 团队后训练算法校招](https://zhipu-ai.jobs.feishu.cn/zhipucampus/m/position/detail/7539833581066586378)（2026 届，A）与[代码大模型算法岗](https://zhipu-ai.jobs.feishu.cn/zhipucampus/m/position/detail/7539835713145358633)（A） | Coding/PPT/Search Agent 场景；SFT/RL 后训练、数据合成和工程化；代码、前端与 Coding Agent 能力。 | 设计可执行代码环境、Agent 轨迹过滤、SFT→RL 课程和 SWE/工具调用评测题。动态飞书页面需上线前复核字段。 |
| [淘天 AI Agent 后训练专家](https://talent.taotian.com/off-campus/position-detail?positionId=100002760001)（页面当前，A） | 构建阿里企业级 Agent 平台后训练技术体系；覆盖训练、数据和评测闭环。 | 准备 data-centric 质量、轨迹/工具数据、自动评测、线上成本与回归门禁。 |
| [腾讯混元 Agent 后训练算法工程师（Red Team）](https://careers.tencent.com/jobdesc.html?postId=2079104781984645120)（页面更新约 2026-08-26，A） | Agent 后训练数据质量、评测、对抗性/红队挑战和工具链。 | 设计安全/越权/提示注入测试集，区分模型能力退化与工具/环境故障；JD 不代表真实面试流程。 |
| [DeepSeek 招聘首页](https://talent.deepseek.com/)（动态列表，A） | 当前列表含 Agent Harness、深度学习研发、预训练数据、AI 搜索等岗位。 | 将 Harness 视为模型与环境之间的约束/验证/恢复层，准备上下文、工具权限、回放和可观测性题；动态列表不提供具体题目证据。 |

### 中国团队技术报告增量

| 来源（日期/层级） | 可核验事实 | 原创题目映射与边界 |
|---|---|---|
| [智谱 GLM-5 技术报告页面](https://www.zhipuai.cn/zh/research/153)（2026-02-21，A） | 基础训练→长上下文 Agent mid-training→串行 RL（reasoning→Agent→general）并用跨阶段在线蒸馏缓解遗忘；SFT 涵盖通用/推理/代码-Agent，交错/保留/轮级思考；执行环境轨迹中的错误页面保留但 loss mask；Reasoning RL 以 GRPO+IcePop 缓解训练-推理不匹配，区分训练/推理模型，报告全 on-policy、group/batch=32；异步 Agent RL、拒绝采样与 mask 修正；评测覆盖 BrowseComp、τ²-Bench、MCP-Atlas、Tool-Decathlon、Vending-Bench、CC-Bench-V2、SWE-rebench；支持 vLLM-Ascend/SGLang、RadixCache、PD、MTP。 | 可设计“串行 RL 如何防遗忘”“IcePop/训推一致性与 stale 轨迹”“局部错误 mask 与拒绝采样”“长程 Agent benchmark 去污染/链式回归”题。官方页面含自报指标，保留实验条件，仅链接+事实改写。 |

| [InternLM2-20B-Reward 官方模型卡](https://huggingface.co/internlm/internlm2-20b-reward)（2024-03-26，A） | 基于 InternLM2-Chat SFT，使用超过 240 万条人工与 AI 合成偏好样本（中英对话、写作、编码、数学、安全）；发布 1.8B/7B/20B 奖励模型用于规模研究；用于 InternLM2-Chat 的 PPO，并提供分数/比较/排序及 Best-of-N 接口与 RewardBench 分项。 | 设计人机混合偏好校准、RM 尺寸/覆盖取舍、Best-of-N 与 RL 的成本效果、RewardBench 分桶诊断题。模型卡示例代码和权重不复制，许可字段需按页面复核。 |

| [Kimi K2.5 技术报告](https://arxiv.org/html/2602.02276v1)（2026-02-02，A；CC BY-NC-ND） | 文本/视觉联合后训练；报告 zero-vision SFT（人工视觉轨迹可能伤害泛化）和联合 RL。提出 Parallel-Agent RL/Agent Swarm：子 Agent 冻结、其轨迹不纳入优化，仅更新 orchestrator，以降低长程 credit-assignment 歧义与训练不稳定；通过并行分解缩短执行时间，并报告 BrowseComp、WideSearch、OSWorld 等评测。 | 只做链接+事实改写，不复制受限许可下的正文、表格或提示；可出“并行 Agent 信用分配/冻结子策略/跨模态 RL”原创题。 |

### 评测基础设施增量

| 来源 | 面试能力点 | 证据/版权 |
|---|---|---|
| [OpenCompass 官方仓库](https://github.com/open-compass/opencompass) | 统一模型/数据适配、批量评测、可复现配置与多维能力报告；可追问 benchmark 污染、分桶和回归。 | A，开源仓库；固定 commit 后引用接口，不复制代码。 |
| [ModelScope EvalScope Agent Evaluation](https://evalscope.readthedocs.io/en/latest/user_guides/agent/index.html) 与 [General Function Calling 指标](https://evalscope.readthedocs.io/en/v1.3.0/get_started/supported_dataset/agent.html) | Native AgentLoop/External Agent Bridge、多轮工具执行、trace 回放；`schema_accuracy`、`tool_call_f1`、成功工具调用等指标。 | A，官方文档；版本滚动，记录检索日期。 |
| [BFCL 官方排行榜](https://gorilla.cs.berkeley.edu/leaderboard.html) / [v3 方法说明](https://gorilla.cs.berkeley.edu/blogs/13_bfcl_v3_multi_turn.html) | 从单次函数调用扩展到多轮、多步及整体 Agentic 评估；可追问 AST/执行正确性与 schema 正确性的差别。 | A，官方项目；只改写方法摘要。 |
| [τ²-Bench](https://arxiv.org/pdf/2506.07982) | 双控制环境中 Agent 与模拟用户共同改变共享状态，检验策略遵循、工具调用和多轮可靠性。 | A，原始论文；不复制数据/提示。 |
| [AgentCompass](https://arxiv.org/html/2607.13705v1) | 把评测抽象为 `benchmark × harness × environment`，支持独立评测 Agent 模型、Harness 和环境，强调可复现与解耦。 | A，2026 原始论文；公式和文字自行表述。 |

### 推理、评测与训练框架面经/JD 增量

子检索（2026-08-30）补充了以下来源；均只登记链接和改写后的能力信号。官方 JD/文档是需求或定义证据，个人面经只是题型线索。

| 来源（日期/层级） | 关键题型或能力信号 | 可信度/版权 |
|---|---|---|
| [字节：推理基础设施](https://jobs.bytedance.com/experienced/position/7595090762887350581/detail)、[执行引擎](https://jobs.bytedance.com/experienced/position/7657866035837323525/detail)、[AI 基建评测](https://jobs.bytedance.com/experienced/position/7639702207530830085/detail)（页面当前，A） | P/D 解耦、KV/cache、调度/算子、服务压测与评测基础设施。 | 官方 JD；只作需求信号，动态日期需复核。 |
| [阿里：Agentic RL 训练基础设施](https://campus-talent.alibaba.com/campus/position/199907740110)（2026-07-30，A） | Agent rollout/训练编排、分布式并行、可观测性和效率。 | 官方 JD；不等同于面试题。 |
| [腾讯：推理性能岗位](https://careers.tencent.com/jobdesc.html?postId=2072330940650270720)（2026-07-09，A）与[LLM/VLM 评测岗位](https://careers.tencent.com/jobdesc.html?postId=2068897969461178368)（2026-06-29，A） | 推理性能指标、P/D/调度、模型与 Agent 评测回归。 | 官方 JD；动态字段按检索日记录。 |
| [华为 MindIE/昇腾技术生态](https://www.huawei.com/cn/huaweitech/publication/202503/new-ecology-of-ascend-computing-power)（2025-03，A） | NPU 推理栈、算子与多硬件适配；可追问 profiling、量化和算子正确性。 | 官方技术文章；链接+事实改写。 |
| [牛客：AI Infra vLLM/SGLang/GPU 面经](https://www.nowcoder.com/feed/main/detail/ebeea95fa44a4eceb1c2890022a6bb2e)（页面 03-03，年份未显示，B） | Paged/Radix、KV、GPU/Triton、调度和手撕。 | 候选人内容；只作题型观察。 |
| [牛客：腾讯 CDG 推理面经](https://www.nowcoder.com/feed/main/detail/6bbfaca62dc64d45851f3ea6c48ff168)（页面 07-28，年份未显示，B） | Prefill/decode、QKV、decode/profiling、TCP 与矩阵题。 | 候选人内容；日期年份需复核。 |
| [牛客：百度评测面经](https://www.nowcoder.com/feed/main/detail/cd8e446a6ec14edfa53cf4c7b6864c4d)（页面 08-27，年份未显示，B） | Golden set、judge 校准、Agent 幻觉、分层文档评测和字符串手撕。 | 候选人内容；不外推公司流程。 |
| [牛客：DeepSeek Agent 评测/trace](https://www.nowcoder.com/discuss/913902338543259648)（2026-08-03，B） | 轨迹回放、步骤/结果/效率指标、失败归因与发布门禁。 | 候选人内容；摘要化使用。 |
| [vLLM 指标与 benchmark 文档](https://docs.vllm.ai/en/stable/design/metrics/) / [性能配置](https://docs.vllm.ai/en/stable/configuration/optimization/) | TTFT、ITL/TPOT、吞吐、p95/p99、warmup 与负载设计。 | A，官方文档；版本滚动。 |
| [SGLang RadixAttention 说明](https://www.lmsys.org/blog/2024-01-17-sglang/) 与 [TensorRT-LLM benchmark 指南](https://nvidia.github.io/TensorRT-LLM/performance/performance-tuning-guide/benchmarking-default-performance.html) | 前缀树缓存、连续批处理、引擎 benchmark 控制变量与硬件指标。 | A，官方项目/厂商文档；不复制示例代码。 |
| [EvalScope 压测文档](https://evalscope.readthedocs.io/en/latest/user_guides/stress_test/quick_start.html) | 并发压测、TTFT/TPOT/E2E/QPS、流式与非流式对比。 | A，官方文档；按版本复核参数。 |

交叉面经信号可压缩为一条排障链：**请求生命周期（prefill→decode→完成/取消）→ KV/缓存与调度 → GPU/NPU 算子与并行 → TTFT/TPOT/p95/QPS → trace/Golden Set/judge → A/B 与 release gate**。这条链路可作为原创系统设计题的评分 rubric，不应复制任何单帖题面。

### 推理/评测增补（2026-08-30 检索）

| 来源（日期/层级） | 题型或岗位信号（事实改写） | 可信度/使用边界 |
|---|---|---|
| [百度校园招聘总页](https://talent.baidu.com/jobs/list?recommendCode=IS3TJS)（检索 2026-08-30，A） | AI 测试岗 J101055：Agent 编排、全维度质量度量、故障注入；智能体算法 J101017：效果、效率、资源成本联合指标；底层软硬件 J100720：训推加速、KV、并发与容错。 | 官方 JD；岗位编号和动态字段上线前复核，不当作真实面题。 |
| [蔚来推理框架校招](https://nio.jobs.feishu.cn/campus/position/7671143673355323689/detail)、[模型评测工程师](https://nio.jobs.feishu.cn/campus/m/position/7661853665926662442/detail)、[高级推理框架](https://nio.jobs.feishu.cn/index/m/position/7665938485554972991/detail)（检索 2026-08-29/30，A） | vLLM/SGLang、CUDA/Triton/NCCL、speculative decoding；评测岗位还要求 FSDP/DeepSpeed/Megatron、Nsight/Perf/Triton/ASan。 | 官方 JD；用于推导推理与评测能力矩阵。 |
| [滴滴模型推理优化](https://talent.didiglobal.com/social/p/65045)、[资深推理引擎](https://talent.didiglobal.com/social/p/65440)（后者页面标 2026-08-03，A） | TensorRT/ONNXRuntime 与 vLLM/SGLang/TRT-LLM；动态负载、通信、显存和 GPU 资源调度。 | 官方 JD；不外推面试流程。 |
| [携程大模型一面](https://www.nowcoder.com/discuss/868214571696152576)（页面日期年份不显，B） | ZeRO/FSDP、PPO/DPO/GRPO、LoRA 的组合追问。 | 候选人自述；仅提炼主题。 |
| [联想大模型一面](https://www.nowcoder.com/discuss/872219056412098560)（页面日期年份不显，B） | GQA/MQA/KV、FlashAttention、ZeRO/FSDP、BF16 等基础与工程权衡。 | 候选人自述；勿视为联想固定题库。 |
| [Agent 评测可观测性问答](https://www.nowcoder.com/discuss/916878230575906816)（页面日期年份不显，B） | Outcome/trajectory 指标、judge 校准、trace 字段、线上指标、A/B 与回滚。 | 候选人自述；可转化为原创评测系统题。 |
| [美团 Agent 面经整理](https://www.nowcoder.com/discuss/881209147377664000)（页面标 2026-08-19，B） | 离线集、沙箱、线上 A/B、trace 与 badcase 闭环。 | 聚合面经；只作交叉信号。 |
| [拼多多 Agent 二面摘要](https://www.nowcoder.com/discuss/865245240389599232)（日期不显，B-/C） | 追问 Agent trace 字段及失败归因。 | 摘要/匿名内容，可信度较低。 |
| [阶跃星辰企业面经页](https://www.nowcoder.com/enterprise/26710/interview)（页面显示 03-30 至 02-05，年份未明，B） | 工具调用训练、reward/数据配比、ReAct 的 plan/observation/action、TRL/verl 调参与 RLVR/GRPO；另有序列并行、RDMA/DMA、LRU、GAE/MC-TD、GSPO、BF16/FP16、GPU 死锁。 | 企业聚合页/候选人自述；问题需改写，日期不可当作年份。 |
| [中兴企业面经页](https://www.nowcoder.com/enterprise/664/interview)（页面标 2026-08-10，B） | GRPO/PPO/GSPO/DAPO、无 critic 的 advantage、Slime/VeRL、PagedAttention/RadixAttention、Agent memory/loop/停止、MCP/Skill 安全、AWQ/GPTQ 与 LoRA rank。 | 企业聚合页；仅作题型线索。 |
| [推理加速工程师面试官回忆](https://www.nowcoder.com/discuss/660152974450188288)（2024-09-02，B+） | shared-memory bank conflict、CUDA stream 中 H2D/kernel/D2H 调度、寄存器超限、encoder/decoder、iter-level schedule、vLLM 调度改进、weight-only 量化权衡及链表反转。 | 作者自称面试官，可信度相对高；题面仍需原创化。 |

这些增补强化了一个可考核的端到端能力闭环：**训练目标/奖励 → 轨迹与工具环境 → rollout 与推理调度 → 指标/trace → A/B、故障注入和回滚**。其中官方 JD 用来定义能力范围，面经只用于发现可能的追问方向。

### 面经核验补充（同日检索）

| 来源 | 改写后的问题/能力点 | 可信度与版权边界 |
|---|---|---|
| [百度大模型后训练实习二面](https://www.nowcoder.com/discuss/864605093486682112)（2026-03-20，B+） | GRPO 数据流、KL 公式与平滑、softmax 数值稳定、`πθ`/旧策略/rollout 策略及大 batch 下的 off-policy 缓解；TRL/VeRL 使用；手写 PyTorch/Transformers 的 Qwen2 SFT。 | 候选人逐题自述且日期明确；只保留主题，手撕题和答案须重新设计。 |
| [阿里大模型算法岗-01](https://www.nowcoder.com/discuss/923309531445071872)（2026-07-17/16，B） | SFT 筛选、GRPO 目标/奖励作弊与质量判定、PPO/DPO 对比；GQA/MLA/vLLM/FlashAttention、推理慢排查；均匀采样/浮点取整/滑窗字符串等编码题。 | 多候选人聚合页，日期清晰但非官方题库；仅作交叉题型信号。 |
| [淘天 Agent 社招一面](https://www.nowcoder.com/discuss/909920471301226496)（2026-07-22，B/C） | DPO 后继续 GRPO 的条件：过度尖锐会造成组内奖励方差低、探索不足；任务路由、RAG 与 Agent 评测/回归。 | 页面含较长“完整答案”，版权/转载风险高；只抽象问题并回链原文。 |

### 评测工具版本化线索

| 官方文档 | 可核验能力点 | 原创题目方向 |
|---|---|---|
| [EvalScope General Function Calling](https://evalscope.readthedocs.io/en/v1.3.0/get_started/supported_dataset/agent.html) | 工具调用成功率、schema 准确率、tool-call F1 等可分离指标。 | 设计“调用正确但参数错误”与“最终成功但轨迹冗余”的分桶指标。 |
| [EvalScope MCP-Atlas](https://evalscope.readthedocs.io/en/v1.10.0/benchmarks/mcp_atlas.html) | 真实 MCP server、允许工具集合、ground-truth trajectory 与 judge 结合。 | 如何隔离模型能力、工具权限和环境故障；如何防止轨迹泄漏。 |
| [EvalScope JobBench](https://evalscope.readthedocs.io/en/v1.11.0/benchmarks/job_bench.html) | 职业/长程任务 benchmark，强调多步完成而非单轮答案。 | 长程任务的过程奖励、预算、超时、重试与最终成功联合评分。 |
| [EvalScope judge 参数](https://evalscope.readthedocs.io/en/v1.3.0/get_started/parameters.html) 与[压力测试](https://evalscope.readthedocs.io/en/latest/user_guides/stress_test/quick_start.html) | auto/LLM/rule 裁判策略；TTFT/TPOT 等在线吞吐指标。 | judge 校准、成本上限、离线分数与线上延迟回归门禁。 |
| [OpenCompass 仓库](https://github.com/open-compass/opencompass) | GenericLLMEvaluator、MATHVerify、CascadeEvaluator 等可组合评测器。 | 设计可复现配置、题目污染检测和级联裁判失败回退。 |

### 训练/推理基础设施 JD 增补

| 官方岗位 | 能力信号（事实改写） | 使用边界 |
|---|---|---|
| [字节 veRL 框架研发 A104002A](https://jobs.bytedance.com/experienced/position/7582538736475572485/detail) | 面向复杂 Agent/Compute-Use 的 veRL 训练框架、稳定性与性能，覆盖 vLLM/SGLang/TRT。 | 官方 JD（检索 2026-08-30）；动态岗位字段需复核。 |
| [字节豆包 RL Infra A182402A](https://jobs.bytedance.com/experienced/position/7530634694203984136/detail) | Ray Trainer、Rollout、Reward、Agent Loop 长轨迹及 vLLM/SGLang 集成。 | 官方 JD；可映射 rollout/learner 解耦题。 |
| [字节推理流量调度 A135599A](https://jobs.bytedance.com/experienced/position/7530885231660026130/detail) | 千亿 TPM 流量、vLLM/Triton 路由与容量调度。 | 官方 JD；指标量级不应脱离岗位原文泛化。 |
| [字节 GPU 稳定性 A243924](https://jobs.bytedance.com/experienced/position/7669627934847928581/detail) | GPU 故障检测、恢复、集群稳定性与训练/推理运维。 | 官方 JD；用于故障注入、重试和回滚题。 |
| [字节预训练/合成数据岗位](https://jobs.bytedance.com/experienced/position/7625854547667536181/detail) | Agent 交互模拟、RM/LLM judge 自动评估、合成数据质量。 | 官方 JD；用来构造数据质量与 judge 校准题。 |
| [阿里 AI 应用算法](https://campus-talent.alibaba.com/campus/position/199907740040) | Rubric、自动+人工评测、Agent/RAG/Memory 任务闭环。 | 官方 JD；检索 2026-08-30，日期需上线前复核。 |

### 云平台评测文档增补

| 文档 | 可核验事实 | 原创题目方向 |
|---|---|---|
| [腾讯云 TI-ONE 模型评测简介](https://cloud.tencent.com/document/product/851/117032)（更新 2026-06-22） | 人工/自动效果评测、开源或自定义集与指标、训练 checkpoint 体验、固定并发/容量探测性能评测。 | 设计 checkpoint 回归、容量曲线和效果-性能联合门禁。 |
| [TI-ONE 自动评测裁判流程](https://cloud.tencent.com/document/product/851/123251)（更新 2026-06-04） | 前处理→裁判模型→后处理的 judge pipeline。 | 裁判模型漂移、评分校准和异常样本重试。 |
| [腾讯云 Agent 应用评测](https://cloud.tencent.com/document/product/1759/104208)（更新 2026-01-20） | Agent 基准/对比评测入口。 | 模型、Harness、工具环境三者如何分层对比。 |
| [腾讯云 Trace 可观测性](https://intl.cloud.tencent.com/document/product/614/82356)（更新 2026-08-17） | 可按状态、错误、延迟过滤 Agent Trace。 | 从 trace 字段定位工具错误、超时和模型退化。 |

[昇腾推理服务监控指标说明](https://www.hiascend.com/developer/techArticles/20250327-1)（2025-03-27，A）可作为 NPU 侧的指标对照：请求成功/失败/运行/等待/换出/抢占状态，prompt 与 generation 吞吐，KV cache/prefix 命中率，以及 TTFT、TPOT、E2E；[DeepSeek 多机部署指南](https://www.hiascend.com/dev/forum/thread-0237183374051498211-1-1.html)（2025-05-23，A/B）补充量化、DP/TP/SP/EP 和服务压测。两页均只记录指标定义和工程能力信号，不复制配置或代码。

[微软亚洲研究院 Agent Lightning](https://www.microsoft.com/en-us/research/articles/agent-lightning/)（2025-08-21，A）是训练/Agent 解耦的公开框架案例：将任意 Agent 轨迹统一成 MDP transition（state/action/reward），用分层信用分配把长轨迹拆成可复用的单轮 PPO/GRPO 样本；Server/Client 通过观测接口（如 OpenTelemetry）捕获数据，兼容 LangChain/AutoGen。该页面同时公开实习招聘信息，适合设计“轨迹切分、信用分配、零侵入接入和训练-部署偏差”题；只保留事实摘要。

### 上海 AI Lab 岗位增补

| 官方岗位（日期） | 能力信号 | 可信度/边界 |
|---|---|---|
| [基座模型算法工程师/青年研究员](https://www.shlab.org.cn/joinus/detail/7678663376582986027?mode=social)（2026-08-28，A） | 后训练、Agent 自我演化、合成数据与 Recursive Self-improvement；要求 LLM SFT/RL/Agentic RL、多机多卡，熟悉 veRL/Slime/vLLM/SGLang，理解数据→训练→评测闭环。 | 官方 JD；可作为岗位能力矩阵，不代表面试题。 |
| [智能体攻防算法工程师/研究员](https://www.shlab.org.cn/joinus/detail/7631220649969912106?jobFunction=&jobType=&keyword=&location=&mode=campus&subject=7619221867426433326)（2026-07-31，A） | 终端/电脑 Agent 全链路安全，Agentic SFT/RL，安全护栏、渗透测试、漏洞挖掘与多工具自动化攻防。 | 官方 JD；安全题需遵守授权环境与负责任披露边界。 |

### 推理基准口径增补

| 官方文档 | 关键信号（事实改写） | 面试映射 |
|---|---|---|
| [SGLang benchmark/profiling](https://docs.sglang.ai/developer_guide/benchmark_and_profiling.html) | 真实 HTTP 压测报告 TTFT、TPOT、ITL、吞吐；稳态建议请求数至少为最大并发的约 5 倍，离线单 batch 会产生偏差。 | 设计负载矩阵、稳态门槛和排队/缓存命中因果分析。 |
| [vLLM metrics](https://docs.vllm.ai/en/latest/design/metrics/) | 记录 E2E、prompt/generation tokens、TTFT、ITL/TPOT、running/swapped/waiting、队列/抢占以及 KV residency/reuse。 | 从指标定位 prefill/decode 瓶颈、抢占和缓存失效。 |
| [TensorRT-LLM build flags](https://nvidia.github.io/TensorRT-LLM/performance/performance-tuning-guide/useful-build-time-flags.html) | 比较 token/request throughput、平均 TTFT/ITL；GEMM 插件可能提高吞吐/ITL 但略损 TTFT，结果依赖负载与硬件。 | 避免单一平均值，解释吞吐-首 token 权衡。 |
| [SGLang EP](https://docs.sglang.ai/advanced_features/expert_parallelism.html)、[P/D 解耦](https://docs.sglang.ai/advanced_features/pd_disaggregation.html)、[量化](https://docs.sglang.ai/advanced_features/quantization.html) | EP/all-to-all、prefill/decode 不同 TP、staging buffer 与量化后质量回退验证。 | MoE 通信、P/D 配置与质量-性能回归题。 |

字节官方 Agent 评测/框架岗位还可作为能力边界的交叉证据（均检索于 2026-08-30，页面未显式发布日期）：[A33616](https://jobs.bytedance.com/experienced/position/7636674147587000629/detail)（TRAE/扣子端到端评测、自动评测 Agent、benchmark）、[A114910](https://jobs.bytedance.com/experienced/position/7670787052867324213/detail)（工具调用/RAG/多轮/Coding 端到端评测）、[A13081A](https://jobs.bytedance.com/experienced/position/7594713568454838581/detail)（评测设计到稳定、可扩展、可观测执行系统）、[A148926](https://jobs.bytedance.com/experienced/position/7596960769942849845/detail)（Planning/Execution Agent 框架）和[A08900](https://jobs.bytedance.com/experienced/m/position/detail/7633829527450601781)（Trace 驱动评测与自迭代）。这些是岗位需求信号，不是面试题或公司固定题库。

[美团《Agent评测漫谈》](https://tech.meituan.com/2026/08/07/Agent-Evaluation.html)（2026-08-07，官方技术团队）进一步给出可落地的方法论：评测对象从 `Query→Answer` 扩展为“模型+系统+工具+流程”，至少覆盖结果、过程、效率和风险四层；长程任务可用 `(prompt, expected_behavior, trace)` 三元组描述；评测平台应支持全链路回放、Case/Rubric 管理、分层沙箱、AI judge、人机标准对齐、问题归因、历史回归和发布准入。该文公开内部两年实践，可信度 A；只做事实性改写，不复制其图表或长段落。

### 其他团队招聘与推理面经补充

| 来源 | 关键能力信号 | 可信度/版权 |
|---|---|---|
| [米哈游 27 届 LLM Post-train 算法研究员岗位页](https://www.nowcoder.com/feed/main/detail/1618900c0a9949f9bd5532b5b816db6d)（2026-08-20，B+，招聘转载） | SFT/RLHF/DPO、Reward Model、偏好与数据清洗、RLAIF、on-policy distillation、推理链压缩，面向游戏剧情/角色一致性。 | 岗位转载而非官网正文；只作能力信号，日期和字段需复核。 |
| [小米语言理解大模型算法岗位](https://xiaomi.jobs.f.mioffice.cn/toptalent/m/position/7646708297261533486/detail)（检索 2026-08-30，A） | SFT/DPO/偏好对齐、安全与数据高效后训，面向小米业务 Agent/RAG。 | 官方招聘页；动态字段需上线前复核。 |
| [小米 AICoding/Agents 岗位聚合页](https://campus.niuqizp.com/job-vmy5ZLzt5.html)（2026-03-11，C+） | 代码/工具轨迹、SFT、DPO/ORPO/RLHF/RLAIF、MCP、沙箱、SWE-bench 与 CI 场景。 | 非官方转载；只作搜索线索，勿当官方 JD。 |
| [CSDN：阿里面经—SGLang 推理框架](https://blog.csdn.net/2401_85343303/article/details/149425014)（页面推荐 2026-03-16，B） | Decode/Extend attention、RadixAttention、MHA/GQA/MLA、FusedMoE/FP8 GEMM、C++/AMX 后端、TTFT/TPOT/并发验证。 | CC BY-SA 页面；仅概述和链接，避免搬运答案。 |
| [阿里云开发者社区：推理部署面试宝典](https://developer.aliyun.com/article/1704743)（2026-01-08，C+） | KV 显存估算、连续批处理、投机解码、延迟-吞吐、TP/PP/EP。 | 二次整理且作者保留版权；仅作题型索引。 |
| [火山引擎：Agent 评测与优化（十五）](https://developer.volcengine.com/articles/7587308063208521769)（2025-12-23，B−） | 离线/在线/A-B/人工评测、任务/工具成功率、P95/P99、吞吐、资源/ROI、基准和持续监控。 | 社区面试精选；只作交叉信号。 |

### 千卡训练/机器人 Agent 岗位补充

| 来源 | 关键能力信号 | 可信度/边界 |
|---|---|---|
| [小鹏汽车 27 届机器人大模型训练推理框架工程师](https://xiaopeng.jobs.feishu.cn/campus/position/7666022611709544745/detail)（检索 2026-08-30，A−；[字段镜像](https://www.shushuqiuzhi.com/position/490804)，2026-07-24） | 千卡级 Pretrain/SFT/RL 通信、调度、容错；vLLM 推理与端云部署；DeepInsight 覆盖 LLM/VLM/WBC/VLA、自动报告、CI/CD；分布式 RL 的 Agent-环境并行。 | 官方页动态渲染，镜像仅用于核对字段；不复制 JD 原文。 |
| [字节 Seed 异构训练优化专家](https://jobs.bytedance.com/experienced/position/7647081071599536437/detail)（检索 2026-08-30，A） | FSDP/TorchTitan、分布式训练系统和异构硬件优化。 | 官方 JD；日期未显式，按检索日标记。 |

| [ByteDance Global E-commerce Conversational AI Tech Lead](https://joinbytedance.com/search/7642661686551169285)（岗位号 A233532A，检索 2026-08-30，A） | 以 post-training、harness、tools、memory、evaluation 构成自进化 Agent 闭环；覆盖大规模 SFT、DPO/IPO/KTO、online RLHF/RLAIF/RLVR、RM/偏好数据、长上下文/蒸馏/QAT；要求真实流量回放、LLM judge 人类一致性校准、失败分类、回归/安全/成本/延迟评测，以及 vLLM/TRT-LLM/MoE/speculative decoding/KV cache。 | 官方英文 JD；动态页面无发布日期，按检索日记录。适合作为端到端系统设计题能力边界，不是面试题库。 |

| [小米 MiMo 后训练 Agent 研究员](https://xiaomi.jobs.f.mioffice.cn/toptalent/m/position/7646707943723010314/detail)（检索 2026-08-30，A） | 小米 Post-training Agent Group，面向开放环境中的目标理解、自主规划与长程任务。 | 官方招聘页；动态字段需复核，不代表面试题。 |
| [蔚来大模型领域后训练算法工程师](https://nio.jobs.feishu.cn/index/m/position/7626329771405052187/detail)（检索 2026-08-30，A） | 车载人机交互后训练，优化多轮对话决策与任务规划 Agent，要求跟踪/复现 LLM Agentic RL。 | 官方招聘页；页面动态，岗位状态需复核。 |

| [GLM-5.2 官方技术发布](https://www.zhipuai.cn/zh/research/161)（2026-06-16，A） | 面向 1M 长程 Coding 的训练环境；Slime 支撑大规模 Agentic RL 与 OPD；改进 MTP 投机解码并适配国产芯片。 | 官方自报，性能数字需保留实验条件；只做事实改写。 |
| [GLM-5-Turbo 官方技术发布](https://www.zhipuai.cn/zh/research/155)（2026-03-15，A） | 用真实 OpenClaw 工作流做后训练，强化工具调用、复杂指令拆解、定时/持续任务和高吞吐长链路；公布 ZClawBench 与企业权限、审计、人工审批实践。 | 官方产品/技术页；不把宣传评价当独立基准。 |
| [GLM-5V-Turbo 官方技术发布](https://www.zhipuai.cn/zh/research/156)（2026-04-01，A） | 30+ 任务协同 RL（STEM、grounding、video、GUI Agent）；合成环境生成可验证 Agentic 数据，加入视觉反馈和多模态工具。 | 官方自报；可作多模态 Agent 训练与评测题线索。 |

### Agentic RL 框架论文增补

| 来源 | 可核验事实 | 原创题目方向 |
|---|---|---|
| [AgentGym-RL](https://arxiv.org/abs/2509.08755)（2025-09-10；ICLR 2026 Oral，A） | Fudan/ByteDance 团队提出模块化、多环境、多轮交互 RL 框架；ScalingInter-RL 逐步增加 interaction horizon，在探索/利用之间切换以降低长程崩溃。 | 设计 horizon curriculum、环境并行、跨任务泛化和稳定性指标。 |
| [AReaL-SEA：Self-Evolving Synthetic Data → Verifiable-Reward RL](https://arxiv.org/html/2601.22607v3)（2026-03-10，A） | 清华/蚂蚁团队的层级多 Agent 生成 tool-grounded 对话与逐样本可执行 verifier，闭环更新 prompts/workflow，再以 verifiable reward 做多轮 RL；显式处理用户模拟噪声。 | 设计可执行 verifier、数据自演化、用户模拟偏差与奖励校准。 |

| [Agent Lightning v1.0](https://arxiv.org/abs/2608.17528)（2026-08-18，A） | “Harnessed Agentic RL”范式：部署时 harness 持有环境循环，训练器只接收 LLM 请求/响应；论文强调 retokenization、样本合并、优势估计、loss 归一化和后端调度等实现细节，提供轻量可复现实验。 | 设计 harness/训练器边界、动作 mask、轨迹重组和稳定性排障题。 |

### Agent 评测方法论交叉核验

| 官方来源 | 关键方法（事实改写） | 可转化题目 |
|---|---|---|
| [Anthropic：Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)（2026-01-09，A） | 将 task/trial/grader/assertion/transcript/trajectory/outcome/eval harness 分层；多轮环境状态会累积错误，应运行多次 trial；最终 outcome 可能与 Agent 自述不一致，静态 benchmark 可能被 loophole 利用。 | 设计 outcome+trajectory 双层 grader、trial 数与置信区间、CI 门禁。 |
| [OpenAI：Evaluate agent workflows](https://developers.openai.com/api/docs/guides/agent-evals)（检索 2026-08-30，A） | 先用 trace grading 定位工具选择、handoff、安全与路由回归，再用 datasets/eval runs 做可重复 benchmark。 | 把线上 trace 转为离线回归集，并设置发布门禁与人工抽检。 |
| [OpenAI Cookbook：Agent improvement loop](https://developers.openai.com/cookbook/examples/agents_sdk/agent_improvement_loop)（2026-05-12，A） | 真实 trace 与人工/LLM 反馈进入评测排序，再驱动 prompt/工具/路由变更；harness 视为 instructions、tools、routing、output validation 的完整契约。 | 设计 badcase→排序→改动→复测的闭环及审批点。 |
| [Google Vertex Agent Evaluation](https://cloud.google.com/blog/products/ai-machine-learning/introducing-agent-evaluation-in-vertex-ai-gen-ai-evaluation-service)（2025-01-25，A） | 区分 final-response 与 trajectory；轨迹可按 exact/in-order/any-order 匹配并计算 precision/recall、single-tool-use；样本包含 prompt、参考/生成轨迹与 response。 | 处理允许多条正确路径的轨迹评分，避免把顺序差异误判为失败。 |

### 中国云厂商 AgentLoop / Trace 资料

| 官方文档 | 能力信号（事实改写） | 原创题目方向 |
|---|---|---|
| [阿里云 AgentLoop 评估概述](https://help.aliyun.com/zh/document_detail/3042179.html)（搜索显示 2026-08-20，A） | 评估器可带独立 Prompt、Skill、MCP 和结构化输出；任务绑定 Trace/日志/数据集与采样，覆盖输入输出、Tool Calls、推理轨迹，支持实时监控、离线回归和 BadCase 根因。 | 设计可版本化 judge、分数下钻、采样策略与 CI gate。 |
| [AgentLoop 核心概念](https://help.aliyun.com/zh/document_detail/3042001.html)（2026-06-18，A） | Trace 经 Pipeline 清洗为 Trajectory，再进入 Dataset/Experience 数据飞轮；字段含输入输出、推理、工具、检索、记忆、分支、耗时、token 与状态；Dataset 支持 schema/版本/实时或周更新和 CI 回归。 | 设计 Trace2Dataset、PII 脱敏、分层采样和版本回归显著性。 |
| [什么是 AgentLoop](https://help.aliyun.com/zh/document_detail/3033860.html)（2026-06-22，A） | 生产痛点分为质量、成本、变更风险和审计；采用 Agent-as-a-Judge 与 Trace2Dataset。 | 评估闭环的审计与成本控制。 |
| [阿里云 LLM Trace 字段规范](https://help.aliyun.com/zh/arms/application-monitoring/developer-reference/llm-trace-field-definition-description)（检索 2026-08-30，A） | 基于 OpenTelemetry GenAI 扩展，覆盖 session/user/framework 及 RETRIEVER/LLM/TOOL/AGENT span kind。 | 跨框架 Trace schema、敏感字段治理和采样率题。 |
| [火山 AgentKit 评测器](https://www.volcengine.com/docs/86681/2220906)、[评测集](https://www.volcengine.com/docs/86681/2220509)（2026-07-28，A−） | 评测器作为裁判，支持线上 Trace 回流和评测集版本化。 | 线上回流、版本隔离和回归门禁。 |
