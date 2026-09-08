# PT-009 分级提示

## H1

先核对题面接口、归约轴、允许的 API；阅读题面末尾的技术来源。

## H2

旧 log-prob、优势与回报目标全部 detach；`r=exp(new-old)`，`policy=-mean(min(r*A,clip(r,1-e,1+e)*A))`；`value_loss=mean((V-R)²)/2`；`entropy=-sum(p*logp)`；总损失 `policy+cv*value_loss-ce*entropy`。本题的 value loss 不裁剪，不能与带 value clipping 的实现不加说明地对比。[OpenAI Spinning Up：PPO](https://spinningup.openai.com/en/latest/algorithms/ppo.html)

## H3

先实现最小非退化输入，再补状态和边界。`r=1` 时策略项为 `-mean(A)`；`A=-1,r=1.5,e=0.2`，该位置损失是 1.5，不能误取 1.2；均匀 C 类分布熵为 `log(C)`。padding 不进入任何分量的分母。

## 口述追问

改变一个输入规模或边界条件后，公式和复杂度是否仍成立？给出可复现的小例子。

## 复测方向

D+2：关闭旧作答，改成显式状态/批次输入，重新独立实现。D+7：用本题最容易混淆的定义设计一个反例，再验证原实现。当前未提供已验证的独立复测资产，不据此自动授予 retention。
