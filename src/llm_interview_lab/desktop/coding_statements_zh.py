"""Reviewed Chinese task display; frozen English assets and graders stay unchanged."""

import hashlib
import re


CONTRACTS = {
    "FND-001": """统计一个虚构样本的多次预测中，与 `label` 不同的预测数量。
- `label` 和每个预测必须是严格的内置 `int`，不接受 `bool`；`predictions` 必须是非空的内置 `list`。
- 违反以上条件均抛出 `ValueError`。包括校验失败时也不得修改输入列表。
- 返回 `int`，使用清晰的逐元素命名，不在 `return` 后保留不可达语句。
- 目标复杂度：时间 `O(n)`，额外空间 `O(1)`。
公开测试通过只记录实现证据，不代表已掌握、通过口述或完成间隔复测。""",
    "FND-002": """校验一条虚构推理样本，并返回独立的规范化副本。
- `sample` 的确切类型必须为 `dict`，包含 `sample_id`、`label`、`predictions`。
- `sample_id` 是非空 `str`；`label` 和每个预测是严格整数，拒绝 `bool`。
- `predictions` 必须是非空的内置 `list`；违反契约抛出 `ValueError`。
- 返回新字典，并复制预测列表；不得修改输入，也不得与输入列表共享可变引用。""",
    "FND-003": """筛选预测错误次数至少达到阈值的困难样本。
- `samples` 必须是内置 `list`；每项满足 FND-002 的严格样本契约。
- `min_errors` 是严格正整数；非法输入抛出 `ValueError`。
- 按原顺序返回符合条件的样本副本，预测列表也必须复制。
- 不得修改外层列表或任何嵌套输入列表。""",
    "FND-004": """汇总重复推理样本的确定性错误统计。
- 校验外层列表；每个样本满足 FND-002 的严格契约。
- 返回且只返回 `total_samples`、`total_predictions`、`total_errors`、`hard_samples`、`error_rate`。
- 至少有一次错误预测即为困难样本；空输入的计数为整数零，`error_rate` 为 `0.0`。
- 错误率为总错误数除以总预测数；不得修改输入。""",
    "FND-005": """流式读写 UTF-8 JSONL，不把整个数据集一次读入内存。
- `JsonlIO.read(path)` 返回 JSON 对象迭代器；坏行或空行抛出含从 1 开始行号的 `ValueError`。
- `JsonlIO.write(path, records)` 每行写一个紧凑 JSON 对象，返回写入条数。
- 非对象记录抛出 `ValueError`；普通文件系统异常向调用方传播。
- 读取必须惰性；两种方法都支持 `str` 和 `pathlib.Path` 路径。""",
    "FND-006": """以确定顺序惰性产出小批量，不修改输入或共享输入容器。
- `items` 为内置 `list`；`batch_size` 为严格正整数；`drop_last` 为严格 `bool`。
- 按原顺序产出新列表；除非 `drop_last=True`，否则保留末尾不足一批的数据。
- 空输入不产出批次，非法参数抛出 `ValueError`。
- 返回迭代器，不暴露与原列表共享可变容器的切片。""",
    "CAP-FND-001": """把六项 Python 数据可靠性能力组合为本地 JSONL 流水线：读取、校验、统计错误、筛选、汇总、写出与分批。
- 每个非空 UTF-8 JSONL 行必须是对象，且仅含 `sample_id`、`label`、`predictions`，类型遵循 FND-002。
- `min_errors`、`batch_size` 为严格正整数，拒绝 `bool`。预测与标签不符次数不少于 `min_errors` 即为困难样本。
- 校验完整输入后才可替换输出；契约失败抛出带从 1 开始行号的 `ValueError`，已有输出保持不变；普通文件异常传播。
- 按输入顺序将困难样本副本写为紧凑 JSONL。
- 返回且只返回 `input_samples`、`total_predictions`、`total_errors`、`hard_samples`、`label_counts`、`batches`。
- `label_counts` 按整数标签统计困难样本；批次为新列表，保留末尾不足批次，顺序与输出一致。
- 不修改输入文件；返回批次与内部记录不共享可变嵌套列表。该综合关卡在 FND-001～006 均已掌握后解锁。""",
    "TNS-002": """通过 reshape / permute 完成多头拆分。
- 输入为三维 `(batch, sequence, hidden)` 张量，`num_heads` 是严格正整数。
- 要求 `hidden % num_heads == 0`，不满足时抛出 `ValueError`。
- 返回连续内存的 `(batch, num_heads, sequence, head_dim)` 张量。
- 保持 dtype、device、数值与梯度连接，不修改输入。""",
    "TNS-003": """通过广播给输入加上偏置。
- `x` 为 `(batch, sequence, hidden)`，`bias` 为 `(hidden,)`。
- 两者 dtype、device 一致；维数或尺寸不合法抛出 `ValueError`。
- 通过广播返回 `x + bias`，不用 Python 循环或显式扩展副本。
- 保留自动求导连接，不修改输入。""",
    "TNS-006": """沿最后一维按索引取值。
- `values` 至少二维；`indices` 与其维数相同，前导维度匹配。
- 索引为同设备的 `torch.long`，每个索引位于 `[0, values.shape[-1])`。
- 返回形状严格等于 `indices.shape` 的结果。
- 保持 values 的 dtype、device、梯度，不修改输入。""",
    "TNS-010": """根据序列长度构造布尔 Mask。
- `lengths` 为一维 `torch.long`，元素为非负长度。
- `max_length` 为 `None` 或严格非负整数，且不能小于最大长度。
- 返回 `(batch, max_length)` 布尔张量，仅在位置 `< length` 时为 `True`。
- 保持 device；显式提供 `max_length` 时支持空批次；不要对样本使用 Python 循环。""",
    "TNS-011": """提取每个样本最后一个有效 Token 的隐藏状态。
- `hidden_states` 为 `(batch, sequence, hidden)`，布尔 `attention_mask` 为 `(batch, sequence)`。
- 每行至少有一个有效 Token，左右 Padding 都必须支持。
- 按每行最大的有效索引返回 `(batch, hidden)`。
- 保持 dtype、device、梯度连接，不修改输入。""",
    "TNS-013": """实现显式的自动求导与 detach 边界。
- 输入为浮点张量，且 `requires_grad=True`。
- 返回 `output = x.square() + x.detach()`，以及与 `x` 等值、已 detach 的克隆快照。
- 输出数值包含两条分支，梯度只通过平方分支。
- 保持 shape、dtype、device，不在函数内调用 backward。""",
    "LOSS-007": """实现数值稳定的 Softmax。
- 输入为非空浮点张量，`dim` 有效。
- 沿 `dim` 减去最大值后计算；禁止 `torch.softmax` 和 `torch.nn.functional.softmax`。
- 输出 shape、dtype、device 不变，沿 `dim` 的概率和为 1。
- 很大幅值下保持有限，保留梯度，不修改 logits。""",
    "LOSS-008": """实现数值稳定的 LogSumExp。
- 输入为非空浮点张量，`dim` 有效，`keepdim` 为严格 `bool`。
- 使用减去最大值的恒等式；禁止 `torch.logsumexp`。
- 两种 `keepdim` 下输出形状与 PyTorch 语义一致，保持 dtype、device、梯度。
- 大幅有限 logits 下仍为有限结果，不修改输入。""",
    "LOSS-013": """直接从 logits 实现稳定二元交叉熵。
- logits 与 targets 是非空浮点张量，shape、dtype、device 一致；targets 在 `[0,1]` 内。
- 使用数值稳定的 logits 空间公式；禁止 `torch.nn.functional.binary_cross_entropy_with_logits` 和 `torch.nn.BCEWithLogitsLoss`。
- 仅支持 `none`、`sum`、`mean` 三种 reduction，输出形状与之匹配。
- 保持梯度和输入，非法契约抛出 `ValueError`。""",
    "LOSS-014": """实现数值稳定的多类别交叉熵。
- logits 为非空浮点 `(batch, classes)`，类别数至少 2；targets 为同设备的 long `(batch,)`。
- targets 是有效类别下标或等于严格整数 `ignore_index`；使用稳定 LogSumExp 与 gather。
- 支持 `none`、`sum`、`mean`；忽略行贡献零，全部忽略时 mean 返回可微的零。
- 禁止 `torch.nn.functional.cross_entropy`、`torch.nn.CrossEntropyLoss`、`torch.log_softmax`、`torch.nn.functional.log_softmax`。
- 保持 dtype、device、梯度，不修改输入。""",
    "NNL-001": """用显式参数与基础张量运算实现 Linear 层。
- 注册 weight `(out_features, in_features)`，可选 bias `(out_features,)`。
- 权重与偏置均匀初始化到 `[-1/sqrt(in_features), +1/sqrt(in_features)]`。
- 接受最后一维为 in_features 的浮点 x，输出保留前导维并将末维改为 out_features。
- 数值匹配 `x @ weight.T + bias`，保持 dtype、device、梯度；禁止 `torch.nn.Linear`。""",
    "NNL-002": """用显式参数实现 Embedding 查表。
- 注册标准正态初始化的 weight `(num_embeddings, embedding_dim)`。
- 接受任意形状的 `torch.long` ID，输出追加 embedding_dim 维。
- 设置 padding_idx 时，Padding 输出严格为零，对应权重行梯度为零。
- 拒绝越界 ID；禁止 `torch.nn.Embedding`、`torch.nn.functional.embedding`。""",
    "NNL-008": """实现 RMSNorm 层。
- 注册初始化为 1 的可学习 scale `(dim,)`，eps 为有限正数。
- 仅沿末维以 `x * rsqrt(mean(x^2) + eps)` 归一化，再施加 scale。
- float16 / bfloat16 输入使用 float32 累加，再将归一化值转回输入 dtype。
- 保持前导维、device、梯度；禁止 `torch.nn.RMSNorm` 或 LayerNorm。""",
    "OPT-001": """显式完成一次 SGD 更新。
- parameters 为非空内置列表，元素是浮点张量；学习率为有限正标量。
- 对有梯度的参数在 no-grad 下原地执行 `parameter -= lr * grad`；跳过 `grad is None`。
- 更新任何参数前校验梯度 shape、device、dtype，不允许发生部分更新。
- 不修改梯度，不让更新进入求导图；禁止 `torch.optim`。""",
    "OPT-002": """实现带动量的一次更新。
- parameters 与 velocities 是等长非空内置列表；velocity 为 None 或与参数匹配。
- 缺失 velocity 从零开始，执行 `v = momentum * v + grad`，再 `parameter -= lr * v`。
- 返回与参数对齐、detach 后克隆的 velocities；缺失梯度时参数与 velocity 都不变。
- 完整校验后才更新；lr 为有限正数，`0 <= momentum < 1`。禁止 `torch.optim`，不修改调用者的梯度与状态。""",
    "OPT-004": """显式完成 Adam 更新。
- 状态与参数对齐，为 None 或含已 detach 的 m、v 及严格正整数 step 的字典。
- 对有梯度的参数更新有偏矩、递增 step、偏置修正，再更新参数。
- 无梯度时连同 step 一起跳过；返回独立、已 detach 的新状态。
- 更新前校验所有 shape、dtype、device 与超参数范围；禁止 `torch.optim`，不修改调用者的梯度与状态。""",
    "OPT-005": """实现 AdamW 的解耦权重衰减。
- 矩状态及偏置修正与 OPT-004 相同。
- 对有梯度参数单独施加 `parameter *= (1 - lr * weight_decay)`，与自适应更新分开。
- 无梯度时跳过参数、衰减和 step 递增。
- weight_decay 为有限非负数，其余参数满足 Adam 范围；不得把 L2 衰减加进梯度。
- 完整校验后才可修改参数；不修改调用者的梯度与状态；禁止 `torch.optim`。""",
    "ATT-002": """实现缩放点积注意力。
- Q/K/V 为浮点 `(batch, heads, q_len/k_len, head_dim)`；K/V 长度、dtype、device 一致。
- 分数除以 `sqrt(head_dim)`，在稳定 Softmax 前施加布尔允许位置 Mask，可选方形因果 Mask。
- 每个 Query 行至少允许一个 Key，返回 `(B,H,Q,Dv)` 输出和 `(B,H,Q,K)` 概率。
- 屏蔽位置概率严格为零，梯度保持连接；禁止框架 SDPA / MHA。""",
    "ATT-004": """实现预投影输入上的多头注意力。
- 输入为三维 `(batch, length, hidden)`；Q/K 隐藏维相同，且能被严格正整数 num_heads 整除。
- 拆分隐藏维成多个头，逐头做缩放注意力，再按原隐藏维顺序拼接。
- V 隐藏维也可被 num_heads 整除，输出 `(batch, q_len, value_hidden)`。
- 支持可广播布尔 Mask 与 causal 模式；禁止框架 MHA / SDPA。""",
    "ATT-005": """实现共享 K/V 头的多查询注意力。
- Q 为 `(B,Q,num_heads*head_dim)`，K 为 `(B,K,head_dim)`，V 为 `(B,K,value_dim)`。
- 将单一 KV 头广播到 Query 头，不物化独立可学习 KV 投影。
- 逐 Query 头计算缩放注意力，拼接输出 `(B,Q,num_heads*value_dim)`。
- 支持 Mask / causal，保留梯度；禁止框架 SDPA / MHA 或 repeat-interleave KV 副本。""",
    "ATT-006": """实现分组查询注意力。
- Q 隐藏维为 num_query_heads*head_dim，K 为 num_kv_heads*head_dim，V 为 num_kv_heads*value_dim。
- 要求 `num_query_heads % num_kv_heads == 0`；连续 Query 头组共享一个 KV 头。
- 缩放注意力后输出 `(B,Q,num_query_heads*value_dim)`，支持 Mask 与 causal。
- 保留共享梯度；禁止框架 SDPA / MHA。""",
    "ATT-007": """实现旋转位置编码。
- 浮点 x 为 `(batch, heads, sequence, head_dim)`，head_dim 为偶数；cos / sin 为 `(sequence, head_dim/2)`。
- 使用提供的余弦与正弦旋转相邻偶 / 奇特征对。
- 返回相同 shape、dtype、device，保持逐对范数与梯度，不修改输入。
- 拒绝 shape / dtype / device 不匹配；禁止库中的 RoPE 辅助函数。""",
    "ATT-009": """实现推理 KV Cache。
- 预分配 K/V `(batch_size, num_kv_heads, max_length, head_dim)`，暴露只读整数 length。
- append 接受匹配的 `(B,H,new_tokens,D)`，在 no-grad 下复制到末尾并原子增加长度。
- 返回仅包含已写位置的视图；溢出或 shape / dtype / device 不匹配时先拒绝，再考虑修改。
- 缓存已 detach，不提供训练梯度，也不是恶意代码沙箱。""",
    "PT-001": """构造 SFT 监督标签。
- input_ids 是 long `(batch, sequence)`，response_mask 是同 shape / device 的布尔张量。
- 返回克隆的 long 标签：回答且非 Padding 位置保留 ID，其余为严格整数 ignore_index。
- 拒绝没有监督回答 Token 的行，以及 `pad_token_id == ignore_index`。
- 不修改或共享输入，输出保留输入设备。""",
    "PT-002": """计算 Token 与序列 Logprob。
- logits 为浮点 `(B,S,V)`，token_ids 为 long `(B,S)`，mask 为同 Token shape / device 的布尔张量。
- 通过稳定 LogSumExp 计算选中 Token 的 logprob，禁止框架 log-softmax / cross-entropy。
- 返回 Mask 外严格为零的 `(B,S)` Token logprob，以及 `(B,)` 序列和。
- 校验 ID，每行至少选中一个 Token；保留 logits 梯度，不修改输入。""",
    "PT-006": """实现 DPO 损失。
- 四个输入是有限浮点 `(batch,)`，dtype / device 一致，reference 不要求梯度。
- 计算 `logits = beta * ((policy_chosen-policy_rejected) - (reference_chosen-reference_rejected))`。
- 返回稳定的逐样本 `-log(sigmoid(logits))` 与标量奖励准确率 `(logits > 0).mean()`。
- beta 为有限正数；保留 policy 梯度，不修改输入。""",
    "PT-014": """计算 GRPO 组内优势。
- rewards 为有限浮点 `(prompts, completions_per_prompt)`，每组至少两条 completion。
- 使用每行总体均值和总体标准差归一化。
- 零方差行返回严格零，不能放大数值噪声。
- 返回已 detach 的优势，shape / dtype / device 不变；eps 为有限正数。""",
    "PT-015": """实现 GRPO 裁剪损失。
- logprobs / old_logprobs 是有限浮点 `(B,G,S)`，advantages 为已 detach 的 `(B,G)`，mask 为布尔 `(B,G,S)`。
- 计算 `exp(logprobs-old_logprobs)`，优势广播到 Token；取未裁剪与裁剪 surrogate 的较小值。
- 仅对有效 Mask 位置求负均值；至少一个有效 Token，且 `0 < clip_eps < 1`。
- 梯度只通过当前 logprobs，不修改输入。""",
    "PT-016": """在 Verifier 与 GRPO 训练器之间过滤无效 completion，避免污染优势统计。
- rewards 为浮点 `(B,G)`，valid_mask 为同设备布尔 `(B,G)`；B、G 为正，eps 为有限正数；不修改输入。
- 仅用有效 completion 计算总体均值、标准差，以有效个数作分母（unbiased=False）。无效位置可含 NaN / 无穷哨兵值，必须完全忽略。
- 返回 `(advantages, kept_mask)`：优势保持 shape / dtype / device，无效位置严格零；kept_mask 为 valid_mask 的独立副本。
- 至少两条有效 completion 且标准差大于 eps 时，用 `(reward - mean) / std`；仅一条或零 / 近零方差时优势为零，但保留有效 Mask。
- 全无效行保留全零 / 全假以便统计或过滤；整个批次全无效时抛出 ValueError。
- 有效奖励必须有限；输出从奖励求导图 detach。半精度 / bfloat16 采用适当累加精度后转回，结果须有限。""",
    "AGT-001": """校验本地工具 Schema。
- 输入为内置字典，包含非空 name、description 和 parameters。
- name 为小写字母 / 数字 / 下划线，且字母开头；parameters 是含 `type: object`、properties、required 的类 JSON Schema 对象。
- 每个属性使用一种支持的基础类型；required 的名称都存在于 properties；拒绝未知顶层字段。
- 所有嵌套容器都需足够深的独立副本；非法输入抛出 ValueError。
仅执行用户信任的本地函数，不提供网络、进程、权限或多租户隔离。""",
    "AGT-002": """实现本地工具注册与调用。
- 注册经过校验的 Schema 与可调用 handler，拒绝重名和不可调用对象。
- 暴露排序后的 names，不暴露可变注册表内部对象。
- 调用 handler 前校验必需 / 未知参数及支持的基础类型。
- 未知工具或非法参数抛出 ValueError；handler 异常直接传播，不重试。
仅执行用户信任的本地函数，不提供网络、进程、权限或多租户隔离。""",
    "AGT-006": """实现本地工具调用循环：解析并校验 action、执行注册工具、将观察或错误追加到 history / trajectory。
- 只操作输入消息字典的独立副本，`model(history)` 返回本地 action 字典。
- final action 为 `{type: final, content: str}`；tool action 指定注册工具及参数字典。
- 追加显式的 assistant action 与 tool observation；非法 action 转为错误观察并消耗一步。
- 遇 final 停止；超过严格正整数 max_steps 抛出 RuntimeError；不实现网络调用、重试或并发。
仅执行用户信任的本地函数，不提供网络、进程、权限或多租户隔离。""",
    "AGT-009": """以 JSONL 保存并重放 Agent 轨迹。
- 每个事件为内置字典，含严格整数 step、非空字符串 type 与字典 payload。
- step 在文件物理顺序中从 0 连续；拒绝重复、跳号、空行、非对象 JSON 与非法 UTF-8。
- 写出紧凑 UTF-8 JSONL 并返回事件数；读取为惰性迭代器。
- 返回独立对象，不按时间戳重排序；普通文件系统异常传播。
不提供网络、进程、权限或多租户隔离。""",
    "VLM-007": """实现视觉语言 SFT 的标签与损失。只让有效、被注意到且非视觉占位的 assistant 目标参与因果语言模型损失；不依赖具体 processor / tokenizer / model。
- logits 为浮点 `(B,L,V)`，位置 t 预测 input_ids[:,t]；函数做因果错位，删除最后一个 logit 和第一个 label。
- input_ids 为同设备有符号整数 `(B,L)`，B > 0、L >= 2、V > 0，不修改输入。
- 三种 Mask 是同设备布尔 `(B,L)`。有效位置严格为 `attention_mask & assistant_mask & ~image_mask`；视觉屏蔽优先。
- 返回 `(loss, labels)`：labels 是新 `(B,L)`，有效位置取输入 ID，其余为 ignore_index；loss 只对错位后有效目标的交叉熵求均值，dtype / device 与 logits 一致。
- 每行在错位后至少一个有效目标，否则 ValueError。有效错位 ID 在 `[0,V)` 内，忽略位置允许范围外占位 ID。
- ignore_index 为非 bool 的 Python 整数，可由输入整数 dtype 表示。先拒绝 shape / device / dtype 不匹配、非有限 logits 与非法 Mask。
- 梯度只通过 logits；不修改任何调用者张量。""",
    "INF-003": """实现确定性的本地自回归服务调度器，只模拟控制面，不调用模型或分配 GPU。
- 配置为正 Python 整数，拒绝 bool。max_active_tokens 为驻留 KV 容量；prefill 消耗 prompt_tokens，每个 decode Token 再消耗一个驻留槽。
- 请求满足 `0 < prompt_tokens < max_active_tokens`、max_new_tokens > 0；ID 是终身唯一的非空字符串，已结束 ID 也不能重用。submit 按 FIFO 入队。
- deadline_step 若提供，是不早于当前时刻的非负绝对步号；初始步号 0。
- step 先将步号加 1；截止时间严格早于新步号的排队或活动请求过期并释放容量，过期与用户取消分开报告。
- 可选预算为不超过配置上限的非负整数，0 表示该阶段不工作。
- FIFO 准入同时受剩余 prefill 与驻留容量约束；首个放不下的请求阻塞后续，不跳队。刚准入的请求本次不能 decode。
- 活动请求使用持久轮询顺序，每次每请求最多一个 Token；数量受 decode_budget 与驻留空槽限制。递增 generated_tokens，达到 max_new_tokens 即完成并释放容量。
- cancel 可取消排队或活动请求，finish 只完成活动请求；成功返回 True，未知或已结束 ID 返回 False。
- step 返回新字典，元组字段 admitted / decoded / completed / expired / queued / active，整数字段 prefill_tokens / decode_tokens / active_tokens / step。
- snapshot 按提交顺序返回新记录字典元组；修改返回值不能修改内部状态。无网络、线程、墙钟等待、模型调用或 GPU 依赖，不暴露可变队列。""",
}


# These are translations of the source Acceptance / Oral defense sections,
# not a generic substitute for their problem-specific requirements.
ACCEPTANCE = {
    "FND": "覆盖正常、边界、异常、确定性与输入不变性。使用虚构数据，不使用公司数据或复制外部作业。",
    "TNS": "覆盖 shape、dtype、device、数值、梯度、非法输入及适用的输入不变性。",
    "LOSS": "与框架参考实现对比数值和梯度，并覆盖极端值、reduction、非法输入及输入不变性。",
    "NNL": "检查注册参数、形状、初始化、数值、dtype、device、梯度、非法输入和参考实现一致性。",
    "OPT": "覆盖闭式更新、缺失梯度、状态隔离、参数校验与 no-grad 更新语义。",
    "ATT": "覆盖形状、参考数值、mask、dtype、device、梯度或推理 detach、非法输入及输入不变性。",
    "PT": "覆盖形状、mask、数值稳定、梯度、退化组、非法数据及输入不变性。",
    "AGT": "覆盖有效流程、非法 action / 数据、确定顺序、状态隔离、终止和输入不变性。",
    "CAP-FND-001": "仅当 FND-001～FND-006 均已掌握后解锁；验证完整的数据流水线。",
    "PT-016": "覆盖过滤后的统计量、无效离群值与哨兵、单元素与零方差组、全无效处理、dtype / device、梯度 detach、形状与取值校验及输入不变性。",
    "VLM-007": "覆盖参考数值、因果错位、图像 / 提示词 / Padding 优先级、逐行空目标、dtype / device / shape、梯度、输入不变性和非法输入。",
    "INF-003": "覆盖 FIFO 准入、prefill 与 KV 预算、轮询公平性、自动完成、手动 finish / cancel、到期、零预算、快照、输入校验及终态容量释放。",
}

ORAL_DEFENSE = {
    "FND": "解释运行时输入要求、一个会拒绝的边界例子、时间和额外空间复杂度，以及为何不会修改输入。",
    "TNS": "说明每个输入 / 输出的形状，解释轴或视图操作、梯度流向，并给出时间和额外空间复杂度。",
    "LOSS": "推导稳定公式，说明 reduction 和输出形状，解释反向传播信号，并给出时间 / 空间复杂度。",
    "NNL": "解释参数形状和初始化，推导前向公式，指出梯度流向，并说明时间 / 空间复杂度。",
    "OPT": "写出更新公式，指出持久状态张量，解释 step 时机和偏置修正，区分耦合 L2 与解耦权重衰减。",
    "ATT": "画出每一步形状变化，解释缩放和 mask 位置，按题意比较 MHA / MQA / GQA 的 KV 头，并说明 prefill / decode 的时间和显存成本。",
    "PT": "从 token 或 reward 追踪到目标函数，推导公式，解释 mask / reduction，并指出奖励投机或零方差的失效情形。",
    "AGT": "解释 schema 校验、状态转移、非法 action、终止、确定性回放，以及生产隔离中哪些能力不在本题范围内。",
    "PT-016": """- 为什么把无效 completion 纳入统计，会同时改变所有有效优势的基线和尺度？
- 推导总体方差；在小组中，它与无偏样本标准差有何差异？
- 如何处理全部被 verifier 拒绝的一组？为什么不能悄悄把它视为零奖励？
- 为什么 reward 和 advantage 要从策略计算图 detach？
- 如何允许无效位置含 NaN 哨兵，但不让它污染归约？""",
    "VLM-007": """- 画出 `(B,L,V) → (B,L-1,V)` 与 `(B,L) → (B,L-1)` 的错位。
- 为什么视觉嵌入和提示词是上下文而非 SFT 目标？为什么 image mask 优先于 assistant mask？
- 不同图像数量与 Padding 如何经过 collator，而不把标签泄漏到其他样本？
- 一行目标全被忽略会怎样？生产 collator 应如何过滤或报告？
- 哪些张量需要梯度？样本 token 数不同时，loss reduction 有何区别？""",
    "INF-003": """- 画出 queued、active、completed、cancelled、expired 状态机。
- 为什么 prefill 受 prompt token 限制，而 decode 每次增加一个 KV token？预留最大输出为何可能浪费容量？
- decode 预算小于批大小时，持久轮询游标如何避免长请求使后来者饥饿？
- 队首阻塞与跳过大请求有何权衡？不同延迟目标可能选择什么策略？
- 真实服务还需怎样处理取消竞争、租户公平性、GPU kernel 打包、prefix cache 归属和墙钟截止时间？""",
}


def chinese_statement(problem_id: str, original: str) -> str:
    """Local display only; do not change a frozen Session or translate via AI."""
    original = original.replace("\r\n", "\n")
    # Chinese-authored revisions are already complete. In particular AdamW
    # gained checkpoint requirements; never replace them with its old glossary.
    if problem_id != "PT-005" and re.search(r"^## (?:目标|任务|题目要求)\s*$", original, re.M):
        return re.sub(r"^# [^\n]+\n+", "", original)
    if problem_id in SOURCE_SHA256 and hashlib.sha256(original.encode("utf-8")).hexdigest() != SOURCE_SHA256[problem_id]:
        return "这份历史题目的中文版本尚未同步。请点击“查看英文题目”阅读该场冻结的原题；现有作答不会改变。"
    contract = CONTRACTS.get(problem_id)
    if contract is None:
        # The remaining current tasks already have detailed Chinese bodies.
        body = re.sub(r"^# [^\n]+\n+", "", original)
        if problem_id == "PT-005":
            body = "这是一道合成数据校验题；接口、示例与测试由本课程编写，所引论文仅提供概念背景。\n\n" + body[body.index("## 目标"):]
        return body
    goal, _, requirements = contract.partition("\n")
    interfaces = re.findall(r"```python\n.*?```", original, re.DOTALL)
    commands = re.findall(r"```(?:bash|sh)\n.*?```", original, re.DOTALL)
    family = problem_id.split("-")[0]
    acceptance = ACCEPTANCE.get(problem_id, ACCEPTANCE.get(family, "验证接口、边界、数值和输入不变性。"))
    oral = ORAL_DEFENSE.get(problem_id, ORAL_DEFENSE.get(family, "解释各阶段接口、边界与时间 / 空间复杂度。"))
    body = (goal + "\n\n## 接口\n\n" + "\n\n".join(interfaces)
            + "\n\n## 题目要求\n\n" + requirements)
    if problem_id == "FND-001":
        body += ("\n\n## 示例\n\n"
                 "- `label=1, predictions=[1, 0, 1, 2]`：返回 `2`。\n"
                 "- `label=3, predictions=[3]`：返回 `0`。\n"
                 "- 空列表 `[]`、`label=True` 或预测含 `False`：抛出 `ValueError`，不能当作零错误。")
    body += ("\n\n## 验收\n\n使用本页的“运行公开测试”，或运行 "
             f"`llm-lab test {problem_id} --profile <id>`。" + acceptance)
    if commands:
        body += "\n\n### 命令示例\n\n以下沿用英文题面的 `default` 示例；实际操作请使用自己的档案 ID。\n\n" + "\n\n".join(commands)
    return body + "\n\n## 口述与复盘\n\n" + oral + "\n\n公开测试通过只记录实现证据，不代表口述、保持、迁移或掌握已通过。"


SOURCE_SHA256 = {
    "FND-006": "10e2a34d5e9881e1f2edaf4c8efcd7376b131ab48af21d2205973d3fdf11dc75",
    "LOSS-013": "9dcbeb69f314d442d8286406c68b012b39f3cf1d6e084ef54f8fdbca984c6ebb",
    "ATT-005": "4e4a84f03e7e689e8a3a41948115e258852cc0a4a9ef1bdb5dd29daba01afad3",
    "TNS-013": "93fd1d50b02334e155cf7ee48f37c3fa7c5d30faa7011f5d8d86d17e13ebc707",
    "AGT-001": "08178bae9f2388ba1ad26ba3fad19d1f168b2b3c985df326c1f07df236b5f5f0",
    "PT-005": "afd464f9401ca0e01f74fcea78cfdc7da9d0832cb94be334f6d1e2d85bbafd2e",
    "NNL-008": "7103ec5b534c3159eb958f7d3a7dcc33bff05e5191f2c2c4aca407cc183837fe",
    "PT-016": "71e3bf861286cc538f49d1e3ee238744a1464b2d9064524c660f5ec2f194b3ff",
    "ATT-006": "50bf2513d9c2add766a2151fa2d77791833e9cfd14f5576cfe2a0c0a24186987",
    "CAP-FND-001": "07405eada6c9fbbd2fefc9169512f1ab4426705823a517617fe2da3c54352178",
    "AGT-009": "cb02befa11dc2f3e15e7ff7e541ae41ed9ec2826f131303eaf73467be91c7400",
    "OPT-005": "17f216e537021b0bdfe9da8f5bda5f24b78afea122e1ce8b6341f6d595423180",
    "CAP-TRN-001": "0c15118d60acb3edc8555b5c724ea996eaa55f585806bc4a0514e4fad8ddb729",
    "TNS-002": "5df39e462f571a65160212c3421aee82c1a0f4baa0f6eeca365e58995efe3b17",
    "TNS-006": "4af2b3c51164f2e6d230cbf150ac3409f2f4db46ad6e9447ca07b5026c7f2637",
    "CAP-LOSS-001": "dab4ac3c725620b1e1ae79e7172bba864b0ad9d1a206537dd5f994fd1551892f",
    "PT-001": "6a32ce853f33bee58ad49b0a39504fc3eee2667e0a60edcf2e929a1069cc700a",
    "OPT-001": "1a19c10292917c9a1d4d67ed1894902a426caa285acda86f59f4550cd33a22bd",
    "LOSS-008": "816f20825cb1766e0673ae3f8b4230dfaea4b209c3584ebb4930146d37a05e1d",
    "ATT-004": "cd1c9a9b5d87b889c1ff00323427ae6eb8197c1268995fa0273155625b79566a",
    "TNS-010": "188850c88628fce6e268b29663f84b219261a9a3c8f220c91de1858ef32dba87",
    "FND-002": "5f931be6997f7f363fe41c16ecc22bad45015a44935c32bebea03f4964a07073",
    "VLM-007": "e5b16561761741a3c26d2c9bb4010b696bca1dacd5c035a73f3c2d64bf9ae702",
    "TNS-011": "78e4e63a487e2378f849afae11b3f24b396344ac2722eb4960b61ecc8834b268",
    "INF-003": "2b2e85c54c56ec259358349af6f32104890e5a187759444c9c4bcdf13899527b",
    "PT-002": "17b9962be79cfd87e17f72b928cb51cb5823c48cc9c50d5c1075112144e450ce",
    "TNS-003": "86a41997da87072f52329e28b36c91af1e5ae752ddb3cf839db42d41ef2f56fd",
    "OPT-002": "23600aa35fb07012954ac70ac8729704da967af78863e3040b67bd25998f2e8a",
    "PT-015": "144e717ff185d28dcda654c47515e6e4e30c8f5567c99d53a273460ea50a3dd6",
    "AGT-006": "026c71823c46cb3705992302ae098a4bcca7aaa6bf45c437e4042981aef93fa8",
    "LOSS-014": "f790751b9f1051234c121bf3c557ff2b6826324faaa21afeef84b34ad57654e9",
    "OPT-004": "0d091fc59b59190588b3fbedcf4290c0c2953a391016bab541bd198ecc4e464d",
    "AGT-002": "3b0da00751ffca25f98eeb90014cba1839a9c24402a54872814898697efcaa09",
    "PT-014": "f9f7b3cd26fe8605906f0a89342335dc404dde4804ab686b631cdf1ec6759d24",
    "ATT-009": "8ba056fcaf7774c7f0df8d7de56567d80ad7eb1cb63decae32e9682815d3ab5a",
    "LOSS-007": "251f2c27f799c03f9ddc14f1e0689e14ffb3c57f11dcb0a587d28f7db9896740",
    "NNL-001": "eb8b781ea245a8d4273ebd7489e1eb14ebb004a87e9c589bc08d58801b060d54",
    "FND-005": "d8b0fcdc61fc86e309da8db7d4f47f6faa9ba0057a33adaeb795af69587685e4",
    "ATT-002": "d6f0de8b43c21da2f8dc346258aecf239416d861e3f4d266b9183f85351d3b36",
    "FND-004": "2cbe3c697e38057a4229b5e33e4b01ef77f01935f5fc8497bb8b5f1c6ae70e86",
    "ATT-007": "4f0af5c2fd4b11e05df4904adf7269de01e83f50894ea459b6011d983b0c8187",
    "NNL-002": "63e1ac9f1928685f393082d1d29492f63918cd22ecc4de6bb0d30eab5d6050ae",
    "FND-003": "969045c3cde570396a2ec789aeeb52cada3ac6b5790aa0c1dc8019f54263edd4",
    "FND-001": "58a05367aaa3cbdf1e199558797887995a4add76e6b619ec321878432be4b324",
    "PT-006": "f8189efb0e5764fb5446dee0d4a3ae1ee5a2d493778b162ec0a7fbb3f92802f1"
}
