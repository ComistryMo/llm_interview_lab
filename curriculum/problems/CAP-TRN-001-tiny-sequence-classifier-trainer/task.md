# CAP-TRN-001 — Tiny Sequence Classifier Trainer

从 primitive Tensor 操作构建一个确定性的 CPU toy trainer，把 Embedding、Mask、
Linear、稳定 Cross Entropy、Autograd 与手写 AdamW 串起来。不得调用
`torch.nn.Embedding`、`torch.nn.Linear` 或 `torch.optim`。

## 接口

```python
def train_tiny_sequence_classifier(
    input_ids: torch.Tensor,       # [N, T], torch.long, CPU
    attention_mask: torch.Tensor,  # [N, T], strict bool, CPU
    targets: torch.Tensor,         # [N], torch.long, CPU
    *,
    vocab_size: int,
    num_classes: int,
    embedding_dim: int = 8,
    batch_size: int = 2,
    epochs: int = 20,
    lr: float = 0.05,
    weight_decay: float = 0.01,
    seed: int = 0,
    dtype: torch.dtype = torch.float64,
) -> dict[str, object]
```

## 固定训练契约

1. 用本地 CPU `torch.Generator` 与 `seed` 初始化，不改变全局 RNG：Embedding
   weight `[V, H]` 与 classifier weight `[C, H]` 服从 `normal(0, 0.05)`，bias 为零；
2. 每个 epoch 按原顺序遍历连续 Mini-Batch，保留最后一个不足 batch；不 shuffle；
3. lookup 后仅对 Mask 为真的 Token 做 mean pooling；每行必须至少一个有效 Token；
4. 计算 Linear logits 和数值稳定的 mean Cross Entropy；
5. 每个 batch 执行 `backward`，保存三个参数的梯度范数，再执行手写 AdamW；
6. AdamW 使用 `beta1=0.9`、`beta2=0.999`、`eps=1e-8`，bias correction 与
   decoupled weight decay，三个参数各自维护 `m`、`v` 与 `step`；
7. 更新在 no-grad 环境完成，每个 batch 前确保旧梯度不会累积。

返回字典必须且只能含：

```text
loss_history          list[float]，每个 batch 更新前的 loss
embedding_weight      detached clone [V, H]
classifier_weight     detached clone [C, H]
classifier_bias       detached clone [C]
optimizer_state       三个键 embedding/weight/bias，各含 step/m/v 的 detached copy
last_gradient_norms   三个键 embedding/weight/bias，有限非负 float
```

## 校验与边界

- 所有整数配置必须为 strict positive int（`seed` 为 strict non-negative int）；
- `vocab_size >= 2`、`num_classes >= 2`，ID/target 必须在范围内；
- `dtype` 只接受 `torch.float32` 或 `torch.float64`；`lr` 为有限正数，decay 为有限非负数；
- 输入 Shape、dtype、device 或全 Padding 行不合法时，在初始化或更新前抛 `ValueError`；
- 不修改 input IDs、Mask 或 targets；返回 state 不得与内部可变状态共享；
- 同一输入与 seed 的返回值完全可复现；对可分 toy 数据，足够训练后 loss 应明显下降。

## 首版不做

AMP、GPU、DDP、Scheduler、Gradient Accumulation、Checkpoint、Early Stopping、
日志平台、配置框架和真实数据均不在本题范围。

## 验收口述

1. 从 IDs 到 pooled state、logits、loss 和 gradient 的 Shape 如何变化？
2. 为什么每个 batch 都要清理旧梯度，AdamW 的持久状态又为何不能清理？
3. decoupled weight decay 与把 L2 项加进 gradient 有何区别？
4. 固定 seed 和 loss 下降分别能证明什么，又不能证明什么？
