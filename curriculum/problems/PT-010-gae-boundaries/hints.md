# PT-010 分级提示

## H1

先核对题面接口、归约轴、允许的 API；阅读题面末尾的技术来源。

## H2

`delta_t=r_t+gamma*(1-terminated_t)*V_next_t-V_t`；反向递推 `A_t=delta_t+gamma*lambda*(1-boundary_t)*A_next`；返回 `A` 与 `A+V`。边界截断优势递推，而不一定取消 bootstrap。截断时 next_value 必须来自截断前最终 observation，不能来自自动 reset 后的新 episode。[GAE 原论文](https://arxiv.org/abs/1506.02438)、[Gymnasium：时间限制与 bootstrap](https://gymnasium.farama.org/tutorials/gymnasium_basics/handling_time_limits/)

## H3

先实现最小非退化输入，再补状态和边界。lambda=0 时 A 等于 TD residual；真正终止时未来 value 不影响该步 delta；时间截断可保留 bootstrap，但不能把下一 episode 的 reward 带回来。两步 reward 都为 1、value=0，gamma=0.9、lambda=0.95、第二步终止，结果 `[1.855,1]`。

## 口述追问

改变一个输入规模或边界条件后，公式和复杂度是否仍成立？给出可复现的小例子。

## 复测方向

D+2：关闭旧作答，改成显式状态/批次输入，重新独立实现。D+7：用本题最容易混淆的定义设计一个反例，再验证原实现。当前未提供已验证的独立复测资产，不据此自动授予 retention。
