# PT-022 · DPO loss：先对齐回答 token，再比较相对偏好

资料映射：AI08。这是原创训练任务，不代表某公司必考题。

推荐准备：[PT-002](../PT-002-token-sequence-logprob/task.md)、[PT-006](../PT-006-dpo-loss/task.md)。推荐顺序不等于硬解锁条件；实际解锁条件见课程入口。

## 接口

```python
def completion_logp(logits, tokens, completion_mask): ...
def paired_dpo(policy, reference, beta=0.1): ...
```

## 题目要求

- logits[B,T,V] 第 t 位置预测 tokens[:,t+1]
- tokens/int64 与 completion_mask/bool 都为 [B,T]。mask 标记目标 token 属于回答（包含真实 EOS，不包含 prompt/padding）
- T≥2，每条回答至少一个有效 shifted token。返回序列 log-prob[B]，按回答 token 求和，不作长度均值
- 忽略位置允许 -100，先屏蔽再 gather。另实现 paired_dpo(policy[B,2], reference[B,2], beta=.1)→mean softplus(-beta*((πc-πr)-(refc-refr)))，列为 chosen,rejected，reference detach，beta>0。这是 PT-002/006 的对齐整合变式，不修改旧接口。

## 共同约定

输入不允许被原地修改（接口明确的状态更新除外）。除题目指定的空输入与异常，输入形状合法、数值有限；不要增加与本题目标无关的校验。张量位于同一设备；浮点使用 float32/float64，保持输出设备与明确的梯度路径；禁止直接调用题目要求手写的整层/算法。

## 验收与复盘

可在编辑器中自行构造输入并运行，也可运行公开测试。测试通过只是实现证据，不等于掌握。完成后解释 shape、复杂度、一个失败边界和测试依据；提示见 hints.md。

## 口述与追问

- logits、labels 和 completion mask 需要怎样一起 shift？
- 回答含 EOS 但不含 padding 时，监督从哪里开始？
- 序列 sum 改成 mean 会不会改变 DPO 的目标？
- 冻结 reference 与采样 old policy 是不是同一角色？

## 来源

- [技术定义 1](https://arxiv.org/html/2305.18290v3)
