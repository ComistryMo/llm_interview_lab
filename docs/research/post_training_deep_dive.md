# 后训练面试深潜：从 SFT 到可验证奖励

> 研究日期：2026-08-30（UTC）
> 适用方向：大模型算法、后训练/对齐、推理与 Agent、VLM 后训练、训练框架
> 文档定位：研究审计与题目设计底稿，不是固定题库，也不替代论文或当前框架文档。

本文把“后训练”拆成可在面试中连续追问、可在小规模实验中证伪的链路：

```text
数据契约 → tokenization/packing/mask → SFT
       → PEFT/量化 → 偏好优化（DPO/IPO/KTO）
       → 在线 RL（PPO/GRPO/DAPO/GSPO）
       → reward/verifier/安全 → contamination-aware evaluation
       → 训练—推理—发布闭环
```

所有公式和实现细节均用原创语言重述。方法定义优先引用原论文，API 行为优先引用官方文档；公开面经只用于发现题型范围，不复制原题、答案或个人信息。

## 0. 面试回答协议

面对“介绍某个后训练方法”时，按以下顺序回答，避免只报名词：

1. **目标与数据**：输入是什么、反馈是 demonstration、pairwise preference、binary label 还是可验证结果？
2. **随机变量与粒度**：策略、旧策略、reference、reward/value、token/sequence 的粒度分别是什么？
3. **目标函数**：写出符号、正负号、归一化分母和 stop-gradient 位置。
4. **张量形状**：至少说清 `[batch, seq]`、`[batch, group, completion]` 和 mask 如何广播。
5. **工程约束**：显存、通信、rollout 延迟、长度偏差、数值稳定和版本差异。
6. **验证与失败**：给出一个最小实验、一个反例和一个 release gate。

推荐的 60 秒模板：

> “我先定义数据和策略。该方法优化的是 ___，样本来自 ___，reference/old policy 的作用是 ___。核心 loss 是 ___，其中 token log-prob 要在 completion mask 上聚合，优势/奖励的 shape 是 ___。它解决了 ___，但会引入 ___（例如长度偏差、reward hacking 或 stale rollout）。我会用 ___ 的 toy test 验证符号和梯度，再用 ___ 的 held-out 指标和成本指标决定是否上线。”

## 1. 统一记号与 shape

| 符号 | 含义 | 常见 shape/备注 |
|---|---|---|
| `B` | batch 中 prompt 数 | `int` |
| `G` | 每个 prompt 的 rollout 数 | GRPO/GSPO 的 group size |
| `T_p` | prompt token 长度 | 可变，通常 padding 或 packed |
| `T_c` | completion token 长度 | 可变，含 EOS 的约定必须固定 |
| `T` | 拼接序列长度 | `T_p + T_c` |
| `V` | vocabulary size | logits 最后一维 |
| `input_ids` | token id | `[B, T]` 或 flattened packed `[ΣT]` |
| `logits` | next-token 未归一化分数 | `[B, T, V]`，预测位置与 label 错一位 |
| `labels` | 目标 token | `[B, T]`，忽略位置通常为 `-100` |
| `loss_mask` | 参与 loss 的位置 | `[B, T]`，`1` 表示参与；不要与 attention mask 混用 |
| `logp` | 选定 token 的 log probability | `[B, T-1]`；要和 shift 后 mask 对齐 |
| `r_i` | 一个 completion 的标量奖励 | `[B,G]` 或 flatten `[B·G]` |
| `A_i`/`A_{i,t}` | sequence/token advantage | `[B,G]` 或 `[B,G,T_c]` |
| `ρ` | importance ratio | token 级 `[B,G,T_c]` 或 sequence 级 `[B,G]` |

### 1.1 三个经常被混淆的 mask

- **attention mask**：决定一个位置能否读到另一个位置；通常是 `[B,T]` 的有效 token mask，经过 causal 规则形成 `[B,1,T,T]` 逻辑关系。
- **loss mask**：决定哪个 target token 计入交叉熵；prompt、padding、图像占位符或不希望监督的 assistant span 可以设为 0。
- **generation/termination mask**：决定 rollout 结束、padding 或截断；它不自动等价于 loss mask。

一个可靠实现先写出：

```text
shift_logits = logits[:, :-1, :]      # [B, T-1, V]
shift_labels = labels[:, 1:]          # [B, T-1]
shift_mask   = loss_mask[:, 1:]        # [B, T-1]
token_logp   = log_softmax(shift_logits, -1).gather(-1, shift_labels)
token_logp   = token_logp * (shift_labels != -100) * shift_mask
```

再决定按 token 求和、按有效 token 求平均还是按样本平均。不要先 `mean` 再乘 mask；padding 比例变化时会产生隐蔽的 batch 权重漂移。

## 2. SFT：数据、packing 与 loss mask

### 2.1 数据契约

SFT 的“样本”至少要能还原以下信息：

```json
{
  "prompt": "用户输入或多轮消息",
  "completion": "目标回答",
  "messages": [{"role": "user", "content": "..."},
               {"role": "assistant", "content": "..."}],
  "metadata": {"source": "...", "quality": 0.0, "split": "train"}
}
```

`prompt-completion` 和 `conversational` 不是同一格式：前者通常可以直接构造 completion mask；后者需要 chat template 输出 role/control token，模板错误会使训练目标错位。Hugging Face TRL 当前文档区分 `completion_only_loss` 与 `assistant_only_loss`，后者要求模板能返回 assistant span（部分已知模型由 TRL 自动修补）；上线前必须锁定 `transformers/trl` 版本并打印一条渲染后的样本和 mask。[TRL SFTTrainer](https://huggingface.co/docs/trl/sft_trainer)

### 2.2 Causal LM loss 的完整推导

给定 `x_0…x_{T-1}`，模型输出 `z_t ∈ R^V`，目标是：

\[
\mathcal L_{\mathrm{SFT}}
=-\frac{1}{\sum_t m_t}\sum_{t=1}^{T-1}m_t\log p_\theta(x_t\mid x_{<t}),
\]

其中 `m_t` 是**shift 后**的 completion/assistant mask。实现上 `CrossEntropyLoss(ignore_index=-100)` 会把 `-100` 位置排除，但它不会替你识别 assistant span，也不会替你处理 packed example 的边界。[PyTorch CrossEntropyLoss](https://docs.pytorch.org/docs/stable/generated/torch.nn.CrossEntropyLoss.html)

必须能解释以下差异：

| reduction | 公式 | 风险 |
|---|---|---|
| token mean | `Σ m_t ℓ_t / Σ m_t` | 长样本不会自动获得更大权重；通常最可比 |
| sample mean | 每个样本先平均，再对样本平均 | 短样本和长样本等权；长 CoT 可能被低估 |
| sum then batch mean | `Σℓ / B` | 长度越长权重越大；batch 长度分布改变会改变有效 LR |

### 2.3 Packing 不是简单拼接

Packing 把多个短样本放入固定长度 block 以减少 padding。当前 TRL 支持 `bfd`、`bfd_split`、`wrapped` 等策略，并可在 FlashAttention 2/3 下启用 padding-free；这些是**版本敏感的 API 事实**，不能写成算法不变量。[TRL packing 参数](https://huggingface.co/docs/trl/sft_trainer#packing)

正确的 packed batch 需要同时定义：

- `cu_seqlens`/segment boundaries，避免一个样本的 query 读取下一个样本；
- 每段的 position ids 是否从 0 重启；
- EOS 是否保留，是否允许跨段预测；
- 每段的 loss mask，prompt 和 completion 的边界；
- attention kernel 的 causal + block-diagonal 语义。

常见错误是把多个样本直接 `torch.cat` 后只使用一个全局 causal mask。这样后一个样本可以看到前一个样本的 token，训练 loss 仍然下降，但推理行为和数据独立性已被破坏。

### 2.4 SFT 失败模式与定位顺序

| 症状 | 首先检查 | 最小修复/证据 |
|---|---|---|
| loss 很低但回答复述 prompt | assistant mask 全 1 或 shift 错位 | 打印 token、role、mask；手算 3-token 样本 |
| 多轮模板训练后无法生成 | 训练模板与推理模板不同 | 固定 `apply_chat_template`，比较 generation prompt |
| packing 后准确率下降 | 跨样本 attention 或 segment position 错 | 用两条互不相关样本，检查 attention 非零位置 |
| loss NaN | fp16 overflow、空有效 token、label 越界 | `finite` 检查、有效 token 计数、bf16/GradScaler |
| 长答案质量差 | sample mean / 截断 / EOS 处理 | 按长度分桶报告 token-normalized loss |
| VLM 训练报 shape 错 | 截断删掉 image token 或 image mask 错 | image placeholder 与 processor 输出逐样本对齐 |
| 梯度为 0 | 全部 `-100`、冻结误配、detach | 统计 `mask.sum()`、trainable 参数梯度 |

### 2.5 SFT 面试追问与实验

**P0 追问**：为什么只对 assistant token 算 loss？如果把 prompt 也算进去会发生什么？`ignore_index=-100` 和 attention mask 的区别是什么？

**P0 实验**：构造 `prompt=[1,2]`、`answer=[3,4,5]` 的 toy logits，手算和 PyTorch loss；改变 prompt 长度但保持 answer 不变，验证 token-mean loss 的不变性。

**P1 追问**：packing 如何保持样本隔离？padding-free 对 kernel 和 position id 有什么要求？长 CoT 使用 sample-level 与 token-level reduction 的偏差是什么？

**P1 实验**：同一批样本分别用 padding、BFD packing、错误全局 causal mask，比较 loss、梯度和一个固定 held-out prompt 的输出。

## 3. LoRA / QLoRA：参数效率不是“免费”

### 3.1 LoRA 的形状与梯度

对于线性层 `W₀ ∈ R^{d_out×d_in}`，LoRA 冻结 `W₀`，学习：

\[
W=W_0+\Delta W,
\qquad
\Delta W=\frac{\alpha}{r}BA,
\]

其中 `A∈R^{r×d_in}`、`B∈R^{d_out×r}`、`r≪min(d_in,d_out)`。输入 `X∈R^{B×T×d_in}` 时：

```text
base = X @ W0.T                    # [B,T,d_out]
delta = (X @ A.T) @ B.T * alpha/r  # [B,T,r] -> [B,T,d_out]
```

经典初始化令 `B=0`，使初始函数等价于 base model；只有 A/B 有梯度。LoRA 论文报告了参数和显存节省，但实际收益取决于 target modules、优化器状态、激活和 sequence length，不能把论文数字当作当前硬件保证。[LoRA paper](https://arxiv.org/abs/2106.09685)

参数量（不含 bias）为：

\[
N_{\mathrm{LoRA}}=r(d_{in}+d_{out})\times N_{\mathrm{target\ layers}}.
\]

### 3.2 target modules 与 merge

- 只挂 `q_proj/v_proj`：参数少，可能限制输出/MLP 适配；
- 挂 `q,k,v,o` 或 MLP `gate/up/down`：表达能力和显存增加；
- `lora_alpha/r` 是缩放，不是 rank；改变 rank 后应重新审视有效步长；
- 推理前可把 `ΔW` 合并进 `W₀`，但量化模型合并、dtype 和多 adapter 路由有额外约束；
- 使用 `modules_to_save` 时，lm_head/embedding 是否训练必须显式记录。

**面试反例**：只说“LoRA 降低参数量”不够；若 `W₀` 仍保留梯度，或 optimizer 把冻结参数纳入 state，显存并不会按预期下降。

### 3.3 QLoRA 的三层精度

QLoRA 的关键不是“把训练全变成 int4”，而是：冻结的 base weights 以 4-bit 存储，在 matmul 时反量化到计算 dtype，梯度穿过该路径流向 LoRA；LoRA 参数和 optimizer 通常保持 bf16/fp32。其论文提出 NF4、double quantization 与 paged optimizers。[QLoRA paper](https://arxiv.org/abs/2305.14314)

典型配置（实际字段以版本文档为准）：

```python
BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
)
```

Hugging Face PEFT 的当前量化指南要求量化后调用 `prepare_model_for_kbit_training`，再用 `LoraConfig/get_peft_model` 注入 adapter。[PEFT quantization guide](https://huggingface.co/docs/peft/developer_guides/quantization)

显存粗估（只用于面试量级判断）：

\[
M\approx M_{\mathrm{weights}}+M_{\mathrm{LoRA}}+M_{\mathrm{optimizer}}+M_{\mathrm{activations}}+M_{\mathrm{temporary}},
\]

`M_weights≈P·4/8` bytes 只是理想下界；量化 scale、metadata、embedding、KV/激活和 allocator 碎片不可忽略。不要把“65B 单卡 48GB”当作任何模型/序列长度都成立的承诺。

### 3.4 LoRA/QLoRA bug checklist

1. `target_modules` 与实际模块名不匹配，导致可训练参数数为 0。
2. QLoRA 后忘记 `prepare_model_for_kbit_training`，或把量化 base 参数误设为 trainable。
3. `bf16` 硬件不支持却强制使用；fp16 + scaler 顺序错误。
4. adapter 保存成功但推理没有 `PeftModel.from_pretrained` 或 merge 到错误 base revision。
5. 多 adapter 训练时 `state_dict`/optimizer group 混入旧 adapter。
6. LoRA dropout、alpha、rank 改变后仍沿用原学习率；导致有效更新尺度不一致。
7. embedding/lm_head tied weights 被保存/合并两次。
8. 量化后做 full fine-tuning；梯度数值与 optimizer 不稳定。

### 3.5 验收实验

- 打印 `trainable_params / all_params`，断言冻结参数 `.grad is None`；
- 对一个 `[2,3,d_in]` 输入比较未注入、LoRA 初始、手工 `W₀+BA` 三路输出；
- 训练 10 步，比较 adapter-only、full fine-tune、不同 rank 的 loss/显存/吞吐；
- 保存→加载→merge→推理，要求 logits 在容差内一致，并记录 base commit、adapter config、dtype。

## 4. 偏好优化：DPO、IPO、KTO 与长度偏差

### 4.1 偏好数据质量先于 loss

标准 pairwise 数据为 `(x, y_w, y_l)`，但面试应继续追问：

- `y_w/y_l` 是否来自同一 prompt、同一模型版本和同一 decoding budget？
- 标签是人类、LLM judge、规则 verifier 还是混合？有无 tie/置信度？
- chosen/rejected 是否存在长度、格式、语言、拒答模式等 shortcut？
- 训练/验证是否按 prompt、用户、时间和来源去重？
- preference 质量是否在难度桶、领域、语言和长度桶分别校准？

### 4.2 DPO 从 KL-RLHF 到分类损失

KL 正则化的 RLHF 目标（最大化形式）为：

\[
\max_{\pi_\theta} \mathbb E_{x,y\sim\pi_\theta}[r(x,y)]
-\beta D_{KL}(\pi_\theta(\cdot|x)\|\pi_{ref}(\cdot|x)).
\]

其最优策略满足：

\[
\pi^*(y|x)\propto\pi_{ref}(y|x)\exp(r(x,y)/\beta).
\]

代入 Bradley–Terry 偏好模型并消去 partition function，得到：

\[
\mathcal L_{DPO}
=-\mathbb E\log\sigma\left(\beta\left[
\log\frac{\pi_\theta(y_w|x)}{\pi_{ref}(y_w|x)}
-\log\frac{\pi_\theta(y_l|x)}{\pi_{ref}(y_l|x)}
\right]\right).
\]

DPO 的 `log π(y|x)` 必须由 completion token 的 log-prob 聚合而来；reference 分支通常不需要梯度。原论文明确说明 DPO 把 reward modeling 与在线 RL loop 换成直接的偏好分类目标。[DPO paper](https://arxiv.org/abs/2305.18290)

**关键实现**：

```text
chosen_logp  = sum_or_mean(token_logp(policy, chosen)  * chosen_mask)
rejected_logp= sum_or_mean(token_logp(policy, rejected)* rejected_mask)
ref_*        = same operation under no_grad(reference)
margin       = beta * ((chosen_logp-ref_chosen_logp)
                     -(rejected_logp-ref_rejected_logp))
loss         = -logsigmoid(margin)
```

这里的 `sum_or_mean` 不是无关紧要的实现选择：sum 会偏好短答案的绝对概率差，mean 能减弱长度影响但改变目标解释。必须在报告中明确使用哪一种，并与 baseline 保持一致。TRL 当前 DPO 文档还暴露 `loss_type="ipo"`、`sigmoid_norm`、Robust DPO、`precompute_ref_log_probs` 等选项；这些字段是版本化实现，不应脱离版本号讨论。[TRL DPOTrainer](https://huggingface.co/docs/trl/dpo_trainer)

### 4.3 DPO 常见 bug

| bug | 结果 | 检测 |
|---|---|---|
| chosen/rejected 的 prompt mask 不同或包含 prompt | 模型学到 prompt/格式差异 | 单独打印 completion span 和 token 数 |
| 忘记 detach reference | reference 与 policy 一起更新，目标漂移 | 检查 ref 参数梯度与 `requires_grad` |
| `beta` 方向/符号错 | 偏好反转或梯度爆炸 | 构造 policy 已偏好 chosen 的 toy case，loss 应下降 |
| chosen/rejected 交换 | 训练后偏好变差 | 把标签翻转，单步梯度方向应反向 |
| 用总和比较超长答案 | 长度偏差、模型啰嗦/短答 | 按 completion 长度分桶 reward margin |
| tokenizer/chat template 不同 | logp 不可比 | 固定同一 tokenizer、template、special tokens |
| truncation 截掉 VLM image token | shape/error 或 silently wrong | DPO VLM 设置 `max_length=None` 前先验证数据长度；参考 [TRL VLM DPO](https://huggingface.co/docs/trl/dpo_trainer#training-vision-language-models) |

### 4.4 IPO、KTO 与何时使用

**IPO**（Identity Preference Optimization）指出 BT/logit 映射在近确定性偏好下可能过拟合，采用 identity/root-finding 风格目标；常见形式是让归一化 log-ratio 差接近目标 `1/(2τ)`：

\[
\mathcal L_{IPO}
=\mathbb E\left[
\left(\Delta\log\frac{\pi_\theta}{\pi_{ref}}
-\frac{1}{2\tau}\right)^2
\right].
\]

具体常数和 reduction 要按论文/实现版本核验；TRL 还记录过 IPO 求和与平均的实现修正，因此面试时应主动说“我会锁定版本并验证 reduction”。[IPO paper](https://arxiv.org/abs/2310.12036)、[TRL preference implementation note](https://github.com/huggingface/blog/blob/main/pref-tuning.md)

**KTO** 只需要 `(x,y,label∈{desirable,undesirable})`，用相对 reference 的 implicit reward：

\[
r_\theta(x,y)=\log\frac{\pi_\theta(y|x)}{\pi_{ref}(y|x)},
\quad z_0\approx D_{KL}(\pi_\theta\|\pi_{ref}),
\]

并通过不同的 gain/loss value function 调整 desirable/undesirable 样本。论文强调实践中通常不对 `z_0` 反传，且类别不平衡需调 `λ_D,λ_U`。[KTO paper](https://arxiv.org/abs/2402.01306)

| 方法 | 数据 | 是否在线 rollout | 主要优点 | 主要风险 |
|---|---|---:|---|---|
| SFT | `(x,y+)` | 否 | 简单、稳定 | 只模仿正例；暴露偏差 |
| DPO | `(x,y+,y-)` | 否 | 不需显式 RM/critic | pair quality、长度/BT 假设 |
| IPO | pair | 否 | 抑制某些过拟合 | 目标/reduction 敏感 |
| KTO | binary desirable/undesirable | 否 | 可利用未配对反馈 | baseline 估计、类别不平衡 |
| PPO/RLHF | prompt + reward | 是 | 任意可微/黑盒 reward | 采样、critic、稳定性、成本 |

## 5. PPO / RLHF：从 reward 到 token advantage

### 5.1 经典三阶段数据流

InstructGPT 风格流程为：

```text
pretrained → SFT policy
SFT policy 采样多个回答 → 人/AI 偏好 → reward model
policy + reward model + reference/critic → PPO rollout/update
```

Reward model 常用 pairwise logistic loss：

\[
\mathcal L_R=-\log\sigma(r_\phi(x,y_w)-r_\phi(x,y_l)).
\]

它只保证相对排序，不保证绝对 reward 可跨 prompt 比较；因此 reward normalization、长度和 prompt difficulty 是训练稳定性的核心。参考 [InstructGPT](https://arxiv.org/abs/2203.02155) 与 [Fine-Tuning Language Models from Human Preferences](https://arxiv.org/abs/1909.08593)。

### 5.2 PPO clipped surrogate 与 GAE

旧策略采样 action/token，当前策略计算：

\[
\rho_t(\theta)=\frac{\pi_\theta(a_t|s_t)}{\pi_{old}(a_t|s_t)},
\]

\[
L^{CLIP}=\mathbb E_t\left[\min\left(
\rho_tA_t,\operatorname{clip}(\rho_t,1-\epsilon,1+\epsilon)A_t
\right)\right].
\]

GAE（有 value head 时）使用：

\[
\delta_t=r_t+\gamma V(s_{t+1})-V(s_t),\qquad
\hat A_t=\sum_{l\ge0}(\gamma\lambda)^l\delta_{t+l}.
\]

语言模型通常只有 sequence-level reward `R`，需要把它放到 EOS、均匀/折扣分配，或加入每 token KL shaping；不同分配会改变 credit assignment，不应笼统说“PPO 自动知道哪个 token 好”。PPO 原论文与 GAE 原论文分别见 [PPO](https://arxiv.org/abs/1707.06347) 和 [GAE](https://arxiv.org/abs/1506.02438)。

### 5.3 PPO 的 shape 与显存

| 对象 | shape | 是否反传 |
|---|---|---|
| prompt/completion ids | `[B,T]` | 否 |
| old log-prob | `[B,T_c]` | 否 |
| current log-prob | `[B,T_c]` | 是 |
| value prediction | `[B,T_c]` | 是（critic） |
| reward model score | `[B]` 或 `[B,T_c]` | 通常否 |
| advantage/return | `[B,T_c]` | 否 |
| ref log-prob | `[B,T_c]` | 否 |

典型训练同时驻留 actor、old/ref、critic、reward model 和 optimizer/activation。ZeRO/FSDP 可分片参数、梯度和 optimizer，但不会消除 rollout 生成和 KV cache；面试应给出“哪部分被分片、哪部分复制、通信发生在哪个阶段”的具体答案。参考 [DeepSpeed ZeRO](https://www.deepspeed.ai/tutorials/zero/) 与 [TRL PPO](https://huggingface.co/docs/trl/trainer)。

### 5.4 PPO/RLHF 失败模式

- **ratio 全为 1**：误把 current logp 当 old logp、或 rollout 后未保存旧策略。
- **clip fraction 过高**：学习率/epoch 过大、rollout stale、advantage scale 异常。
- **KL 爆炸**：reference 不匹配、beta 太小、reward scale 过大、token mask 错。
- **value loss 爆炸**：reward 未归一化、terminal bootstrap 错、critic 与 actor 输入不一致。
- **reward 上升但人工质量下降**：reward model overoptimization/hacking，需 hidden eval 和 RM ensemble。
- **生成全是 EOS 或无限变长**：EOS reward、长度 shaping、termination mask 或 tokenizer special token 错。
- **分布式挂起**：rollout worker 长尾、NCCL collective 次序不一致、某 rank 空 batch。

## 6. GRPO、DAPO、GSPO：组相对奖励与粒度选择

### 6.1 GRPO 基本对象

对每个 prompt `x_b` 采样 `G` 个 completion：

```text
completion_ids : [B, G, T_c]
rewards        : [B, G]
advantages     : [B, G]  # broadcast to [B,G,T_c]
old_logp       : [B, G, T_c]
policy_logp    : [B, G, T_c]
```

组内标准化优势的常见形式：

\[
\hat A_{b,g}=
\frac{r_{b,g}-\operatorname{mean}_{g'}r_{b,g'}}
{\operatorname{std}_{g'}r_{b,g'}+\varepsilon}.
\]

原始 GRPO/TRL 实现还会把它 broadcast 到 completion token，并使用 current/old log-prob ratio 计算 policy loss；KL 项和 reduction 细节随实现版本变化。TRL 当前文档明确说明 `num_generations` 必须整除有效 batch，并区分 group/local/batch reward scaling。[DeepSeekMath](https://arxiv.org/abs/2402.03300)、[TRL GRPOTrainer](https://huggingface.co/docs/trl/grpo_trainer)

**零方差是第一道面试陷阱**：若一个 group 的 reward 全相同，标准差为 0；即使加 epsilon，优势仍接近 0，prompt 对该步没有有效梯度。不能简单把 NaN 替成 0 后宣称“训练正常”，应统计 zero-gradient group rate 并设计动态采样或 group size 策略。

### 6.2 GRPO loss 的 reduction 选择

令 `m_{b,g,t}` 为有效 completion mask，`ρ_{b,g,t}` 为 ratio：

1. **sample-level**：先对每个 completion 的 token loss 平均，再对 `B·G` 样本平均；每个样本等权。
2. **token-level**：所有有效 token 的 loss 求和除以总有效 token；长样本贡献更大。
3. **sequence-level ratio**：先将 token log-ratio 聚合成一个序列 ratio，再以 sequence reward 更新。

三者不是代码风格差异，而是不同的优化目标。长 CoT、截断样本和 reward 只在序列末端时，reduction 会显著改变长度/熵动力学。

### 6.3 DAPO 的四个可考点

DAPO 针对长 CoT 提出一组工程化改动：[DAPO paper](https://arxiv.org/abs/2503.14476)、[verl DAPO recipe](https://verl.readthedocs.io/en/latest/algo/dapo.html)

- **Clip-Higher**：将 PPO/GRPO 的上下 clip 解耦，增大上界给低概率探索 token 更多上升空间，缓解 entropy collapse。
- **Dynamic Sampling**：过滤 reward 全 0/全 1 等无有效组，持续补采样到有效 batch；要报告额外采样成本和 prompt 分布变化。
- **Token-level policy loss**：长样本按 token 聚合，避免 sample-level reduction 对长回答的信号过度稀释。
- **Overlong filtering/shaping**：区分“合理但被 max length 截断”和“真正错误”；可 mask 截断样本 loss，或在缓冲区间施加软长度惩罚。

面试追问应包括：动态采样会不会改变 on-policy 分布？过滤后 reward 估计是否有选择偏差？`Clip-Higher` 如何和 entropy bonus 同时调？截断样本全部 mask 是否会丢掉有价值的前缀？

### 6.4 GSPO：序列级 importance ratio

GSPO 先聚合序列 log-likelihood：

\[
s_{b,g}(\theta)=
\exp\left(\frac{1}{|y_{b,g}|}
\sum_t m_{b,g,t}
\left[\log\pi_\theta(y_t|x,y_{<t})
-\log\pi_{old}(y_t|x,y_{<t})\right]\right),
\]

再用 group-normalized sequence advantage 做 sequence-level clip/reward/update。[GSPO paper](https://arxiv.org/abs/2507.18071)、[Qwen GSPO说明](https://qwenlm.github.io/blog/gspo/)

优点：序列 reward 与优化粒度一致，减少 token ratio 在长序列上的高方差；可更容易复用推理引擎返回的 sequence likelihood。代价：一个异常 token 可能使整个序列 ratio 被裁剪，token-level credit assignment 变粗。

### 6.5 GRPO/DAPO/GSPO 的决策表

| 条件 | 优先考虑 | 需要监控 |
|---|---|---|
| 数学/代码，有可靠 verifier，资源有限 | GRPO | group zero-variance、reward 分布、KL/entropy |
| 长 CoT、截断多、探索坍塌 | DAPO recipe | clip fraction、有效 prompt rate、长度桶 |
| MoE 或长序列，token ratio 高方差 | GSPO | sequence ratio、整序列裁剪率、credit loss |
| 任意黑盒 reward、偏好/安全目标 | PPO/RLHF | RM 校准、KL、critic explained variance、hidden eval |
| 固定离线偏好，无法 rollout | DPO/IPO/KTO | margin、长度偏差、reference drift |

### 6.6 stale rollout 与异步训练

同步 on-policy 的简化循环是：

```text
θ_old ← θ
rollout(θ_old) → reward/advantage
用 θ_old 数据更新 θ 若干 epoch
丢弃旧数据，进入下一轮
```

异步/训推解耦会让行为策略与当前策略不一致，需要记录 `policy_version`、tokenizer/template revision、generation config 和 rollout 时间。补救包括 importance sampling、ratio clipping/masking、短 stale window、优先级队列和回放审计；不能只看 wall-clock 加速而忽略 off-policy bias。参考 [verl one-step off-policy async trainer](https://verl.readthedocs.io/en/latest/advance/one_step_off.html)。

## 7. Reward、Verifier、ORM/PRM 与 reward hacking

### 7.1 ORM、PRM、规则 verifier

| 类型 | 信号 | 优点 | 风险 |
|---|---|---|---|
| ORM | 最终答案/整段 response 一个分数 | 便宜、适合明确结果 | credit assignment 稀疏，可能奖励错误过程 |
| PRM | 每一步/句子是否正确 | 细粒度、可选中间错误 | 标注昂贵，步骤切分和泄漏复杂 |
| 规则 verifier | 单测、公式解析、执行结果、schema | 可解释、低噪声 | 覆盖窄，容易被钻规则漏洞 |
| LLM judge/RM | 语言质量、安全、偏好 | 覆盖广 | 校准、位置/长度/风格偏差，易被 hack |
| 组合 reward | 加权/门控多个信号 | 可兼顾质量与安全 | 权重和尺度会改变策略，需消融 |

过程监督论文 [Let's Verify Step by Step](https://arxiv.org/abs/2305.20050) 展示了 PRM 在数学多步推理中的价值；面试不能简化成“PRM 一定优于 ORM”，应说明标注成本、步骤边界和任务可验证性。

### 7.2 Reward hacking 的形式化思路

设真实目标 `R`、代理 reward `\tilde R`。当优化 `\tilde R` 使策略性能上升而 `R` 下降，即发生 proxy overoptimization/reward hacking。可用以下诊断曲线：

```text
横轴：训练步 / BoN 样本数 / reward scale
纵轴：proxy reward、hidden human/rule reward、长度、拒答率、重复率
```

常见模式：长度偏好、套模板/关键词、迎合 judge、利用 parser 漏洞、输出不可执行代码、修改环境或 reward 通道。可参考 [Reward Model Overoptimization scaling](https://arxiv.org/abs/2406.02900)、[Defining and Characterizing Reward Hacking](https://arxiv.org/abs/2209.13085)、[DeepMind specification gaming](https://deepmind.google/blog/specification-gaming-the-flip-side-of-ai-ingenuity/)。

### 7.3 防御与面试实验

1. **多信号**：规则 correctness + safety classifier + length/format penalty；报告每个信号的独立和联合相关性。
2. **隐藏测试**：训练 verifier 与 release verifier 分离；对代码使用未公开单测/随机化输入。
3. **对抗样本**：主动生成高 proxy、低真实质量的 response，加入 RM hard negatives。
4. **校准**：按领域/长度/语言计算 pairwise accuracy、ECE/Brier、selective risk。
5. **RM ensemble/不确定性**：在 reward disagreement 高时降低更新权重或转人工复核。
6. **预算约束**：把 token cost、工具调用次数、超时和越权作为独立门禁，不要全塞进一个 reward 标量。

P0 反问：如果 reward 上升、任务成功率下降，你先查 reward 还是 policy？应答：先冻结 checkpoint，画 proxy/true/length/coverage 曲线，复现一个最小 hack，再决定是 reward、数据、采样还是评测泄漏；不要立即调大 KL 作为万能修复。

## 8. 数据污染、去重与评测可信度

### 8.1 污染分类

- **直接污染**：训练数据包含 benchmark 原文、答案或代码。
- **近重复污染**：改写、翻译、格式变化、代码变量重命名后仍可记忆。
- **间接污染**：同一题目的解析、博客、讨论或生成数据泄露解法。
- **评测反馈污染**：反复用公开 leaderboard 调参，等价于把测试集当训练信号。
- **轨迹/工具污染**：Agent benchmark 的 issue、补丁、tool trace 出现在预训练语料。

去重不能只做 exact string。可组合：规范化 n-gram/hash → MinHash/LSH near-duplicate → embedding/语义检索 → 人工审计；保留 `sample_id/source/timestamp/hash` 和排除原因。研究显示去重能减少记忆和 train-test overlap；参考 [Deduplicating Training Data Makes Language Models Better](https://arxiv.org/abs/2107.06499) 与 [FineWeb](https://arxiv.org/abs/2406.17557)。

### 8.2 评测协议

至少分为四层：

1. **离线能力**：固定公开 benchmark，按领域/难度/长度分桶。
2. **污染审计**：训练 manifest 与 benchmark hash/时间交叉检查；报告 direct/near/semantic 规则和抽样人工审计。
3. **动态/私有测试**：时间切分、私有题、临时生成或执行反馈；LiveBench 采用持续更新和客观 ground truth 的思路。[LiveBench](https://arxiv.org/abs/2406.19314)
4. **线上/任务成功**：真实用户/工具环境，记录成功率、恢复率、TTFT/TPOT、成本、越权和回滚。

### 8.3 指标与不确定性

| 指标 | 适用 | 不能单独说明 |
|---|---|---|
| accuracy/pass@1 | 单答案、代码单测 | 不代表探索或长程成功 |
| pass@k / avg@k | 多采样推理 | 成本、重复答案和 verifier 偏差 |
| pairwise win rate | 偏好/对话 | judge 位置偏差、置信区间 |
| reward model pair accuracy | RM 诊断 | 不保证 policy 优化后真实质量 |
| calibration/ECE/Brier | 置信度/拒答 | 需定义 bin 和 class balance |
| tool-call/schema success | Agent 工具 | 最终任务可能仍失败 |
| p50/p95/p99 TTFT/TPOT/E2E | serving | 负载、硬件和 streaming 设置依赖 |

用 bootstrap 或 Wilson 区间报告 `n` 和置信区间；比较两个 checkpoint 时固定 prompt、seed、temperature、max tokens 和 judge 版本。HELM 的多指标思想提醒我们不要把 accuracy 压成一个无上下文分数。[HELM](https://crfm.stanford.edu/helm/)

### 8.4 评测面试题

- 如何验证一个 coding Agent 的 SWE-Bench 分数不是记忆？
- 为什么公开 benchmark 分数上涨却线上失败？
- 如何设计 hidden test 避免 verifier overfit？
- LLM judge 的 position bias、verbosity bias 如何检测？
- 如何把任务成功、工具正确、步骤成本和安全越权拆成指标？
- 何时用动态 benchmark，何时用固定 benchmark？如何保持可复现？

## 9. 训练—推理—数据系统追问

### 9.1 训推一致性清单

检查以下字段是否完全一致或有显式转换：

```text
model revision / tokenizer revision / chat template
special tokens / stop ids / generation config
dtype / quantization / RoPE scaling / position ids
logits processor / sampling temperature-top-p-top-k
padding side / truncation / image & tool placeholder
```

训练 log-prob 与 rollout engine log-prob 不一致时，优先做同一 batch 的逐 token diff；不要只比较最终 reward。GSPO 等序列级方法可降低精度差异敏感性，但不意味着 tokenizer/template mismatch 可以忽略。

### 9.2 框架边界

| 层 | 典型组件 | 面试应说明 |
|---|---|---|
| 数据/模板 | Datasets、chat template、collator | 原始字段如何到 ids/mask |
| policy update | Transformers/TRL | loss、梯度、reference/old policy |
| PEFT | PEFT/bitsandbytes | adapter 注入、量化和保存 |
| 分布式训练 | FSDP/DeepSpeed/Megatron | 参数/梯度/optimizer 如何分片 |
| rollout | vLLM/SGLang/自研 engine | batch、KV、sampling、version |
| orchestration | verl/Ray | worker role、资源池、同步/异步 |
| evaluation | rule/LLM judge/benchmark | 数据隔离、trace、release gate |

不要把“会调用 Trainer”说成“理解算法”；至少能沿一条样本从 `dataset → collator → forward → loss → backward → checkpoint → eval` 追踪。

## 10. 最小可复现实验阶梯

所有实验都应保存：代码 commit、环境包版本、模型/数据 revision、seed、命令、关键配置、日志、checkpoint hash、指标和失败说明。

### E0：纯数学/梯度 toy

- 用 `V=5,T=4` 构造 logits 和 labels，手算 CE、DPO margin、PPO ratio、GRPO group advantage。
- 断言 mask 全 0 时 loss/gradient 行为明确，不出现静默 NaN。
- 翻转 chosen/rejected 或 positive/negative，检查梯度方向反向。

### E1：tiny SFT + packing

- 两条 prompt-completion，分别跑 padding、正确 packing、错误跨段 attention。
- 记录 token-normalized loss、梯度范数、有效 token 数、吞吐和峰值显存。

### E2：LoRA/QLoRA 对照

- 同一 tiny model 比较 full fine-tune、LoRA rank 4/16、4-bit QLoRA。
- 验证保存/加载/merge logits 一致性；报告 trainable ratio、显存和 held-out 质量。

### E3：离线 preference

- 合成具有已知偏好规则的 pair，比较 SFT/DPO/IPO/KTO。
- 按答案长度和 prompt 难度分桶，画 margin、entropy、KL、win rate。

### E4：toy GRPO/DAPO

- 每个 prompt 采样 `G=4`，使用可验证奇偶/字符串规则 reward。
- 人为制造全 0、全 1、截断、stale rollout，验证动态采样、mask、clip fraction。

### E5：reward hack 与污染审计

- 构造关键词 reward，训练/BoN 找到高 proxy 低 true 的输出；hidden verifier 应捕获。
- 对训练/评测文本做 exact + near duplicate 扫描，输出 overlap rate、审计样本和排除规则。

### E6：发布门禁

一个 checkpoint 只有同时满足以下条件才允许进入模拟面试推荐：

```text
objective/shape toy tests pass
no unexplained NaN or zero-gradient spike
held-out quality non-regression
proxy vs true reward gap within threshold
contamination audit recorded
latency/cost/security gates pass
repro bundle can recreate metrics
```

## 11. 建议新增的 P0/P1 面试卡（供知识库后续落地）

下面是原创卡建议，不是复制任何公开面经。每张卡应按仓库 schema 补齐 `answer_layers`、`follow_ups`、`pitfalls`、`source_claims` 和 coding contract。

| 建议 ID | 优先级 | 题目 | 必答证据 | 关键坑/实验 |
|---|---|---|---|---|
| `EGT-PT-008` | P0 | 从 `input_ids` 推导 assistant-only SFT loss | shift、mask、reduction、`-100` | prompt 泄漏；toy gradient |
| `EGT-PT-009` | P0 | packing 如何保证样本之间不可见 | segment/position/EOS/FA varlen | 全局 causal mask；隔离性测试 |
| `EGT-PT-010` | P0 | LoRA forward、参数量和 merge | A/B shape、alpha/r、冻结 | target mismatch；logit 等价测试 |
| `EGT-PT-011` | P0 | QLoRA 为什么能训练 4-bit base | NF4、double quant、compute dtype、paged optimizer | 把 int4 当训练 dtype；显存拆分 |
| `EGT-PT-012` | P0 | DPO 从 KL-RLHF 推导 | partition cancellation、log-ratio、beta | reference 梯度、chosen/rejected 反转 |
| `EGT-PT-013` | P1 | IPO/KTO 何时优于 DPO | 数据契约、目标差异、类别不平衡 | reduction/`z0` detach；合成偏好 |
| `EGT-PT-014` | P0 | PPO 中 sequence reward 如何变 token advantage | old/current ratio、GAE、KL、EOS | ratio=1、critic leakage；clip test |
| `EGT-PT-015` | P0 | GRPO group advantage 与 zero variance | `[B,G,T]`、group normalization | 全同 reward、group divisibility |
| `EGT-PT-016` | P1 | DAPO 四项改动解决什么问题 | Clip-Higher、dynamic sampling、token loss、overlong | 选择偏差；长度桶消融 |
| `EGT-PT-017` | P1 | GRPO 与 GSPO 的 ratio 粒度 trade-off | token vs sequence likelihood | whole-sequence clipping；MoE/长序列实验 |
| `EGT-PT-018` | P0 | reward 上升但真实质量下降如何定位 | proxy/true 曲线、RM/数据/采样/评测分层 | 盲目加 KL；hack reproduction |
| `EGT-PT-019` | P1 | ORM、PRM、规则 verifier 如何组合 | credit、成本、覆盖、门控 | PRM 标签泄漏；分桶校准 |
| `EGT-PT-020` | P0 | 设计 contamination-aware eval | direct/near/semantic、时间/私有集 | 只做 exact match；报告 CI |
| `EGT-PT-021` | P1 | stale rollout 如何测量和缓解 | policy version、importance ratio、window | 异步只看吞吐；回放审计 |
| `EGT-PT-022` | P1 | 后训练实验 release gate | 质量/安全/成本/延迟/复现 | 单一 leaderboard 分数 |

### 11.1 推荐手撕题

1. `masked_sequence_logprob(logits, labels, mask)`：支持 `[B,T,V]`、`ignore_index`、全空 mask、不同 reduction。
2. `dpo_loss(policy_logp, ref_logp, chosen_mask, rejected_mask, beta)`：检查 detach、长度归一化和翻转标签。
3. `group_advantage(rewards, valid_group_mask, eps)`：处理全 0/全 1、NaN 和跨 rank 聚合。
4. `packed_causal_mask(lengths)`：生成 block-diagonal causal mask，并验证任意跨段元素为 false。
5. `lora_linear(x, weight, A, B, alpha, r)`：shape、dtype、初始等价和 merge。
6. `bootstrap_ci(scores, seed)`：分层采样、均值/中位数、置信区间和空输入错误。
7. `reward_hack_detector(proxy, hidden, length, threshold)`：输出 Pareto gap、长度相关性和异常样本 id。
8. `contamination_scan(train, eval, ngram_k, threshold)`：exact/near overlap 报告，不能泄露原始敏感文本。

## 12. 40 个高频追问（速答提纲）

### SFT/数据/PEFT

1. 为什么 causal LM 要 shift？——位置 `t` 预测 `t+1`，logits/labels/mask 必须同步切片。
2. prompt 也算 loss 有何后果？——模型学习复述条件和模板，completion 信号被稀释。
3. `-100` 与 attention mask 区别？——一个决定监督，一个决定可见性。
4. packing 的最大风险？——跨样本 attention、position/EOS 边界和错误 loss denominator。
5. 为什么长样本 loss 会改变训练动力？——sample/token reduction 给长度不同的样本不同权重。
6. LoRA 为什么初始不改变函数？——常用 B=0，使 `BA=0`。
7. rank 增大一定更好吗？——表达能力增加但参数/过拟合/通信和有效步长也变。
8. LoRA 应挂哪些层？——由任务和预算决定，至少做 q/v 与 q/k/v/o+MLP 消融。
9. QLoRA 的梯度经过哪里？——穿过冻结量化权重的反量化计算路径，更新 adapter，不更新 base。
10. 为什么要 paged optimizer？——缓解 optimizer/激活峰值，不等于降低稳态所有显存。

### DPO/偏好

11. DPO 为什么不需要显式 RM？——KL-RLHF 最优策略的 change-of-variables 使 reward 差写成 policy/reference log-ratio。
12. `beta` 太大/太小分别怎样？——控制偏好 margin 与 reference 约束的尺度，需看实际 KL 和质量而非背固定值。
13. DPO reference 是否反传？——通常 no-grad/frozen；否则 reference drift 改变目标。
14. chosen/rejected 长度不等怎么办？——明确 sum/mean，做长度分桶和 length-controlled eval。
15. IPO 解决什么潜在问题？——减轻近确定偏好下 BT/logit 目标的过拟合，代价是目标/超参敏感。
16. KTO 需要 pair 吗？——不需要，可用独立 desirable/undesirable label；类别权重需校准。
17. DPO 后为什么可能变啰嗦？——长度偏差、模板/数据分布和 reference mismatch 共同作用。
18. preference label 有噪声怎么办？——标签平滑/robust loss、重复标注、置信度加权、hard-negative 审计。

### PPO/GRPO/RLVR

19. PPO ratio 分子分母是谁？——当前 policy / 采样 old policy，同一 token 条件下的概率。
20. clip 为什么不是 KL 约束的等价物？——它是局部 surrogate 下界，实际 KL 仍需监控。
21. GAE 的 bias-variance trade-off？——λ 小偏差大方差小，λ 大反之；语言模型还受稀疏 EOS reward 影响。
22. critic 为什么昂贵？——额外模型/参数、前向和 value optimizer 状态；GRPO 用组内 baseline 替代。
23. GRPO group size 越大越好吗？——方差可能下降但 rollout 成本线性增长、prompt 覆盖下降。
24. group reward 全相同怎么办？——该组优势无信息；统计并补采样/过滤，不能静默吞掉。
25. 为什么 DAPO 要 Clip-Higher？——低概率探索 token 的 ratio 上升空间被对称上界限制，可能熵坍塌。
26. token-level 与 sequence-level loss 的差别？——前者细粒度但长序列方差大，后者与 sequence reward 一致但 credit 粗。
27. GSPO 如何帮助 MoE？——sequence ratio 减少长序列 token-level importance noise；仍需验证具体 routing/版本。
28. RLVR 何时不适合？——没有可靠 verifier、真实目标主观或规则覆盖窄时，硬奖励会放大漏洞。
29. stale rollout 如何检测？——记录 policy version、平均/分位 KL、importance ratio 和样本等待时间。
30. KL 应加在哪里？——可作 token reward shaping 或显式 loss；位置、方向、mask 和 reference 必须一致。

### Reward/评测/系统

31. reward 上升质量下降先查什么？——proxy/true 分离、长度和 hack 样本，再分定位数据/RM/优化/评测。
32. ORM 与 PRM 如何选？——看可验证粒度、标注成本和 credit assignment；做 matched-budget 对照。
33. LLM judge 的三类偏差？——位置、长度/verbosity、风格/自偏好；需交换顺序和人工校准。
34. benchmark contamination 怎么做？——manifest/hash、exact+near+semantic、时间/私有/动态集和审计样本。
35. 为什么 pass@k 不能直接比较？——k、sampling temperature、预算和 verifier 都会改变它。
36. 如何报告统计显著性？——固定评测协议，给 n、bootstrap/Wilson CI，避免只报单点。
37. 训练和 rollout logits 不同怎么办？——逐 token 对齐 tokenizer/template/dtype/position，再检查 engine kernel 和 precision。
38. 如何分辨模型失败和工具失败？——记录 action/schema/env response/timeout/retry，做 counterfactual replay。
39. 发布 gate 至少有哪些？——质量、真实/隐藏 reward、安全、污染、延迟、成本、复现。
40. 你读过 TRL/verl 哪部分？——能沿一条 batch 讲清 worker、collator、loss、gradient、rollout、checkpoint 和 metric，而不是只报 API。

## 13. 来源登记与复核元数据

> 下面只登记链接和短事实摘要；详细公共岗位/面经范围信号见 [`post_training_agent_interview_sources.md`](post_training_agent_interview_sources.md)。所有记录检索日为 2026-08-30；滚动文档在发布前需重新核对。

| source id | 类型 | 版本/定位 | 关键用途 | 可靠性 |
|---|---|---|---|---|
| `paper.instructgpt` | 原论文 | arXiv:2203.02155 | SFT→RM→PPO 三阶段 | 高 |
| `paper.ppo` | 原论文 | arXiv:1707.06347 | clipped surrogate、多 epoch | 高 |
| `paper.gae` | 原论文 | arXiv:1506.02438 | advantage 估计 | 高 |
| `paper.dpo` | 原论文 | arXiv:2305.18290v3 | KL 推导、DPO loss/gradient | 高 |
| `paper.ipo` | 原论文 | arXiv:2310.12036v2 | IPO 与偏好过拟合 | 高 |
| `paper.kto` | 会议论文/原论文 | PMLR 235 / arXiv:2402.01306v4 | binary feedback、KTO loss | 高 |
| `paper.grpo` | 原论文 | arXiv:2402.03300 | group-relative advantage | 高 |
| `paper.dapo` | 原论文 | arXiv:2503.14476v2 | Clip-Higher、dynamic sampling、长 CoT | 高 |
| `paper.gspo` | 原论文 | arXiv:2507.18071v2 | sequence ratio 与 MoE 稳定性 | 高 |
| `paper.lora` | 原论文 | arXiv:2106.09685 | low-rank update/参数量 | 高 |
| `paper.qlora` | 原论文 | arXiv:2305.14314 | NF4、double quant、paged optimizer | 高 |
| `docs.trl.sft` | 官方文档 | retrieved 2026-08-30 | packing、completion/assistant mask | 高（易变） |
| `docs.trl.dpo` | 官方文档 | retrieved 2026-08-30 | loss variants、VLM、metrics | 高（易变） |
| `docs.trl.grpo` | 官方文档 | retrieved 2026-08-30 | group shape、scaling、off-policy mask | 高（易变） |
| `docs.peft.quant` | 官方文档 | retrieved 2026-08-30 | k-bit preparation、LoRA config | 高（易变） |
| `docs.deepspeed.zero` | 官方文档 | retrieved 2026-08-30 | 参数/梯度/optimizer 分片 | 高（易变） |
| `repo.verl` | 官方仓库/文档 | main；发布前锁 commit | rollout/worker/异步架构 | 高（易变） |
| `paper.prm` | 原论文 | arXiv:2305.20050 | process supervision | 高 |
| `paper.rm-overopt` | 原论文 | arXiv:2406.02900 | reward overoptimization | 高 |
| `paper.reward-hacking` | 原论文 | arXiv:2209.13085 | reward hacking 定义 | 高 |
| `paper.dedup` | 原论文 | arXiv:2107.06499 | dedup 与记忆/overlap | 高 |
| `paper.contamination-survey` | 调研论文 | arXiv:2406.04244 | 污染分类与缓解 | 中-高 |
| `paper.livebench` | benchmark 论文 | arXiv:2406.19314 | 动态/客观评测 | 高 |
| `project.helm` | 官方 benchmark | retrieved 2026-08-30 | 多指标评测 | 高（易变） |

### 13.1 研究使用边界

- 原论文用于方法定义和公式；arXiv 是预印本，若有正式会议版本优先记录正式版本。
- 官方文档用于当前 API 行为；必须记录检索日期，不能把默认值当作永久语义。
- 官方仓库应在项目发布前锁定 tag/commit，记录依赖版本和硬件。
- 公开面经只支持“某种题型被观察到”的 anecdotal claim；不得写成公司固定题库或统计概率。
- 不保存完整题面、答案、代码、截图、个人信息、付费内容或雇主内部资料；项目卡片采用 clean-room 原创。

## 14. 维护与刷新计划

每次刷新按以下顺序：

1. 先核对易变官方 API（TRL/PEFT/verl/Transformers）和 source version；
2. 再跑 E0 toy tests，防止符号、mask、reduction 回归；
3. 复核 P0 卡的 one-liner/core answer/follow-up/pitfall；
4. 更新污染审计和评测协议，避免 benchmark 过时；
5. 记录 changelog，保留旧结论和适用版本，不静默重写。

建议每个岗位准备包至少覆盖一条完整证据链：

```text
一张 SFT mask/packing 卡
一张 LoRA/QLoRA 显存卡
一张 DPO 或 PPO 推导卡
一张 GRPO/DAPO/GSPO 训练稳定性卡
一张 reward/verifier 诊断卡
一张 contamination/evaluation release-gate 卡
一题可运行手撕 + 一次无帮助复测
```

## 15. 可直接落 YAML 的卡片规格（首批 6 张）

以下字段按项目 `knowledge.schema.json` 的语义组织。`source_ids` 中标记“待登记”的条目需要先补进 source registry；`related_problems` 只填现有 Catalog 中 `ready` 的题目。下面的题面均为 clean-room 原创。

### 15.1 `EGT-PT-008` — SFT mask、packing 与模板边界

```yaml
id: EGT-PT-008
title: "SFT mask、packing 与 chat-template 边界"
domain: post_training
tracks: [post_training, llm_algorithm, multimodal]
skills: [skill.sft.loss_mask, skill.data.packing, skill.tokenizer.chat_template]
priority: P0
seniority: [intern, new_grad, mid]
source_ids: [trl-official-docs, hf-chat-templates, pytorch-cross-entropy, attention-is-all-you-need]
related_problems: []
formula: >-
  L = -sum_t m_t log p_theta(x_t | x_<t) / max(1, sum_t m_t),
  with shift_logits=logits[:,:-1], shift_labels=labels[:,1:].
answer_layers:
  one_liner: "attention 可见性和监督位置正交；只把有效 assistant/completion token 放进 shift 后 CE。"
  core_answer:
    - "input_ids/attention_mask/labels 为 [B,L]，logits 为 [B,L,V]；labels[:,1:] 与 logits[:,:-1] 对齐。"
    - "prompt/system/tool-result/pad 通过 loss mask 或 -100 排除，attention mask 只控制可见性。"
    - "packing 必须提供 segment boundary、position reset 与 block-diagonal/varlen causal 约束。"
  derivation_or_example: "用 prompt=[1,2]、answer=[3,4,5] 手算有效位置、分母和一个 logit 梯度。"
follow_ups:
  - "completion_only_loss 与 assistant_only_loss 的 dataset/template 前提是什么？"
  - "packing 后如何证明跨样本 attention 没有泄漏？"
  - "全 batch labels=-100、VLM 截断 image token 时怎样处理？"
pitfalls:
  - "shift 只切 logits 或只切 labels，导致 off-by-one。"
  - "把 attention_mask=0 当作 labels=-100。"
  - "tokenize=False 后重复添加 BOS/EOS，或训练时错误使用 add_generation_prompt。"
  - "多个样本直接 concat，后一个样本读取前一个样本。"
signals: ["能说清 shape/mask/reduction", "能写 toy test", "能指出模板版本风险"]
provenance: synthesized_clean_room
reviewed_at: "2026-08-30"
```

验收：标准 CE 与手算值一致；翻转一个 assistant token 的 logit 时 loss 下降；跨段 attention 全为 false；空有效 token 明确报错或跳过而不是 NaN。

### 15.2 `EGT-PT-009` — LoRA/QLoRA 注入与显存账本

```yaml
id: EGT-PT-009
title: "LoRA/QLoRA 注入、冻结与显存账本"
domain: post_training
tracks: [post_training, llm_algorithm, inference_system]
skills: [skill.peft.lora, skill.quantization.qlora, skill.memory.accounting]
priority: P0
seniority: [intern, new_grad, mid]
source_ids: [lora-paper, qlora-paper, trl-official-docs]
related_problems: []
formula: >-
  W=W0+(alpha/r)BA; W0[out,in], A[r,in], B[out,r],
  X[B,L,in] -> Y[B,L,out], N_trainable=r(in+out) per linear layer.
answer_layers:
  one_liner: "冻结 base，用低秩路径学习 delta；QLoRA 只量化 base 存储，adapter/计算保持可训练精度。"
  core_answer:
    - "B=0 的常用初始化使初始函数与 base 等价；alpha/r 是更新缩放而非 rank。"
    - "NF4、double quant、paged optimizer 分别处理存储误差、scale 开销和峰值 optimizer 内存。"
    - "prepare_model_for_kbit_training 后再注入 PEFT；adapter 绑定 base revision/tokenizer/template。"
  derivation_or_example: "对 [2,3,8] 输入和 W0[16,8] 手工算 delta 输出与参数量。"
follow_ups:
  - "q/v 与 all-linear target_modules 如何做成本/质量消融？"
  - "merge_and_unload 与保留 adapter 的差别，如何验证 logits？"
  - "为什么 adapter 参数很少仍可能 OOM？"
pitfalls:
  - "target_modules regex 没命中，实际 trainable 参数为 0。"
  - "把 4-bit storage 误说成 4-bit optimizer/activation。"
  - "忘记冻结 base、错误使用 device_map=auto、或 tied embedding 重复保存。"
  - "adapter 与错误 base/checkpoint 合并，模型能加载但行为已变。"
signals: ["会画显存组成", "能检查 requires_grad/dtype", "能做 merge round-trip"]
provenance: synthesized_clean_room
reviewed_at: "2026-08-30"
```

验收：断言 base `.grad is None`、LoRA 初始输出等于 base；merge/unmerge 在容差内一致；记录 trainable ratio、峰值显存、dtype、base/adapter hash。

### 15.3 `EGT-PT-010` — DPO/IPO/KTO 目标选择

```yaml
id: EGT-PT-010
title: "DPO、IPO、KTO：偏好数据与目标函数选择"
domain: post_training
tracks: [post_training, llm_algorithm]
skills: [skill.preference_optimization, skill.reward_modeling, skill.loss_derivation]
priority: P0
seniority: [intern, new_grad, mid]
source_ids:
  - dpo-2305-18290
  - trl-official-docs
  - preference-ipo-paper  # 待登记：arXiv:2310.12036
  - preference-kto-paper  # 待登记：arXiv:2402.01306
related_problems: [COD-PT-001]
formula: >-
  m=beta[(log pi_theta(yw|x)-log pi_ref(yw|x))
  -(log pi_theta(yl|x)-log pi_ref(yl|x))]; L_DPO=-log sigmoid(m).
answer_layers:
  one_liner: "DPO 是离线 pairwise log-ratio 分类，IPO 抑制某些 BT 过拟合，KTO 接受非配对二元反馈。"
  core_answer:
    - "chosen/rejected 必须来自同一 prompt；policy/reference 用相同 tokenizer、template、mask 聚合 completion logp。"
    - "reference 通常 frozen/no-grad；beta、IPO tau、KTO beta 的语义不能混为一谈。"
    - "sum、per-sequence mean、per-token mean 会改变长度偏差，必须写入实验配置。"
  derivation_or_example: "构造 chosen implicit reward 高于 rejected 的 toy pair，检查 margin>0，标签反转后梯度反向。"
follow_ups:
  - "DPO 为什么能消去 partition function？"
  - "近确定偏好、标签噪声和极端长度不平衡时怎样选 IPO/KTO/Robust DPO？"
  - "VLM DPO 为什么不能盲目 max_length 截断？"
pitfalls:
  - "chosen/rejected 交换或 ratio 符号反了。"
  - "reference 反传、prompt token 计入 response logp。"
  - "只看平均 margin，不看长度/领域/语言分桶。"
  - "采用默认 in-batch KL 估计时 batch=1，或 desirable/undesirable 权重未校准。"
signals: ["能推导 log-ratio", "能解释数据契约", "能用分桶指标诊断"]
provenance: synthesized_clean_room
reviewed_at: "2026-08-30"
```

验收：toy DPO/IPO/KTO 梯度方向与数值梯度一致；reference 无梯度；长度配对和不配对数据分别报告；VLM 样本保留所有 image token。

### 15.4 `EGT-PT-011` — PPO 到 GRPO 的 advantage/ratio 链路

```yaml
id: EGT-PT-011
title: "PPO/GRPO：从 rollout reward 到 token update"
domain: post_training
tracks: [post_training, llm_algorithm, agent]
skills: [skill.ppo, skill.grpo, skill.advantage_estimation]
priority: P0
seniority: [intern, new_grad, mid]
source_ids: [instructgpt-220302155, ppo-paper, deepseekmath-grpo-2402, trl-official-docs]
related_problems: [COD-PT-002]
formula: >-
  rho_t=pi_theta(a_t|s_t)/pi_old(a_t|s_t);
  L_clip=E[min(rho_t A_t, clip(rho_t,1-eps,1+eps)A_t)].
  GRPO: A_bg=(r_bg-mean_g r_bg)/(std_g r_bg+eps), broadcast to [B,G,T].
answer_layers:
  one_liner: "PPO 用 old/current ratio 和 clip 复用近 on-policy 样本；GRPO 用同 prompt group 的相对 reward 替代独立 critic。"
  core_answer:
    - "rollout ids [B,G,T]、old/ref logp [B,G,T]、reward [B,G]、advantage 广播到 token。"
    - "old logp、reward、advantage 必须 detach；EOS/截断和 completion mask 决定 credit assignment。"
    - "PPO 的 value/critic 显存昂贵；GRPO 的 zero-variance group 会产生零信息梯度。"
  derivation_or_example: "B=1,G=2,T=3，奖励 [1,0] 时手算 group advantage、ratio、clip 分支。"
follow_ups:
  - "sequence reward 如何分配到 token？GAE 与 KL shaping 有何差异？"
  - "为什么 ratio 全为 1 或 clip fraction 突然升高？"
  - "GRPO group size、std scaling 和 global/token reduction 如何影响长度？"
pitfalls:
  - "把 current logp 当 old logp，或把 ratio 写成 old/current。"
  - "不同 prompt 混组、std=0 未统计、跨 rank group reshape 错。"
  - "把 objective KL、approx KL、reference KL 当成同一指标。"
  - "没有 EOS/termination mask，模型靠无限变长获取 reward。"
signals: ["shape 和 detach 准确", "能定位 ratio/KL/critic 故障", "能解释 GRPO trade-off"]
provenance: synthesized_clean_room
reviewed_at: "2026-08-30"
```

验收：同一 toy batch 对照手工实现；翻转 advantage 后 policy 梯度反向；全同 reward 组被标记为 zero-gradient；日志包含 ratio、clip fraction、KL、entropy、长度。

### 15.5 `EGT-PT-012` — DAPO/GSPO 与 stale rollout

```yaml
id: EGT-PT-012
title: "长 CoT RL：DAPO、GSPO 与 stale rollout 稳定性"
domain: post_training
tracks: [post_training, llm_algorithm, inference_system]
skills: [skill.dapo, skill.gspo, skill.rollout_consistency, skill.rl_stability]
priority: P1
seniority: [new_grad, mid]
source_ids:
  - deepseekmath-grpo-2402
  - gspo-paper
  - trl-official-docs
  - post-training-dapo-paper  # 待登记：arXiv:2503.14476
related_problems: [COD-PT-002]
formula: >-
  DAPO decouples clip bounds and uses effective-token normalization;
  GSPO s_bg=exp(mean_t[m_bg,t*(log pi_theta-log pi_old)]),
  then applies a sequence-level clipped objective. Always log policy_version.
answer_layers:
  one_liner: "DAPO 针对长 CoT 的探索、有效样本和截断噪声做 recipe；GSPO 把 importance ratio 提升到序列粒度以降低长序列 token 方差。"
  core_answer:
    - "Clip-Higher、Dynamic Sampling、token-level reduction、overlong filtering/shaping 各自对应一个可观测失败。"
    - "GSPO 使用有效 completion token 的平均 log-ratio 后 exp（几何平均），不能直接 exp(sum) 或 raw product。"
    - "异步 rollout 需记录 policy/model/tokenizer/template version，并监控 stale KL/ratio/等待时间。"
  derivation_or_example: "对两条长度不同 completion 比较 sample-level、token-level 和 geometric sequence ratio。"
follow_ups:
  - "Dynamic Sampling 是否改变训练分布，如何估计选择偏差？"
  - "为何 Clip-Higher 可能缓解 entropy collapse，却不能替代 hidden eval？"
  - "GSPO 整序列裁剪时一个坏 token 会发生什么？"
pitfalls:
  - "把 DAPO token denominator、GRPO sample denominator、GSPO sequence ratio 混成一个公式。"
  - "过滤全对/全错组后跨 rank 不一致，或补采样不记录成本。"
  - "用异步吞吐提升掩盖 stale policy 和 off-policy bias。"
  - "截断样本无条件 punitive reward，误伤正确但过长的 reasoning。"
signals: ["能按粒度比较算法", "能提出消融和监控", "理解训推解耦风险"]
provenance: synthesized_clean_room
reviewed_at: "2026-08-30"
```

验收：toy 中验证 `exp(mean(log ratio))` 与 raw product 不同；人为制造全对/全错/截断/stale 样本，确认每类都有独立计数、mask 和回归断言。

### 15.6 `EGT-PT-013` — Reward/Verifier/污染感知发布门禁

```yaml
id: EGT-PT-013
title: "Reward、Verifier、reward hacking 与污染感知评测"
domain: post_training
tracks: [post_training, llm_algorithm, evaluation, agent]
skills: [skill.reward_modeling, skill.verifier, skill.data_contamination, skill.release_gate]
priority: P0
seniority: [intern, new_grad, mid]
source_ids:
  - instructgpt-220302155
  - dedup-paper
  - post-training-prm-paper  # 待登记：arXiv:2305.20050
  - reward-overoptimization-paper  # 待登记：arXiv:2406.02900
  - contamination-survey  # 待登记：arXiv:2406.04244
  - livebench-benchmark  # 待登记：arXiv:2406.19314
related_problems: [COD-EVAL-001]
formula: >-
  R_proxy(x,y) != R_true(x,y) in general; release only if hidden quality,
  safety, contamination, latency and cost gates pass. Report bootstrap/Wilson
  confidence intervals, not a lone leaderboard point.
answer_layers:
  one_liner: "高 proxy reward 不是成功；要把 verifier/RM、隐藏测试、污染审计、成本和安全拆开测，并定位 proxy-true gap。"
  core_answer:
    - "ORM 给结果级信号，PRM 给过程级信号，规则 verifier 可解释但覆盖窄；组合时保留分项日志。"
    - "污染包括 direct、near-duplicate、semantic、公开反馈和 Agent trace 泄漏；exact match 不是充分审计。"
    - "评测至少包含公开分桶、私有/动态集、对抗 reward-hack、线上 trace 与统计置信区间。"
  derivation_or_example: "构造关键词 proxy reward，让 BoN 找到高 proxy/低 hidden 的输出；画 reward、长度、真实成功率曲线。"
follow_ups:
  - "如何区分 reward、数据、优化和评测协议造成的回归？"
  - "如何对 LLM judge 做 position/verbosity bias 校准？"
  - "为什么 pass@k、RM accuracy 和线上成功率不能互换？"
pitfalls:
  - "只看公开 leaderboard 或 proxy reward，忽略 hidden test/CI。"
  - "只做 exact string 去重，不记录近重复/语义匹配和时间切分。"
  - "把 verifier 当作绝对真值，忽略 parser 漏洞、工具故障和数据污染。"
  - "把质量、安全、成本、延迟压成一个未经校准的 reward 标量。"
signals: ["能给出失败归因树", "会设计 hidden/adversarial eval", "报告不确定性与回滚条件"]
provenance: synthesized_clean_room
reviewed_at: "2026-08-30"
```

验收：同一 checkpoint 同时输出 proxy/hidden/长度/重复/安全/成本；污染扫描保存 hash 与抽样审计记录但不保存敏感原文；release gate 失败时阻止进入岗位准备包。
