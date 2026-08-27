# EXT-CS336-A5：Alignment Companion

## 定位与边界

本卡覆盖 Stanford CS336 Spring 2026 Assignment 5 主作业与安全/RLHF supplement：prompt/eval、response log-prob、reward、group normalization、on/off-policy objectives、GRPO variants、SFT、MMLU/GSM8K/AlpacaEval/SimpleSafetyTests 和 DPO。

固定版本 `c2734a…` 的仓库树没有发现根或子目录 LICENSE、COPYING、NOTICE。本项目只登记事实性接口与 problem/test 名称，并允许用户从官方 URL 本地检出；不复制、翻译、改编或再分发其中任何代码、PDF、prompt、数据、模型、tests、snapshot 或 fixture。

整份 assignment 是聚合 Gate；当前 `integration_status=inventory-audited` 只允许安装与 Preview，problem-group ID 不写入原生 Workspace。priority 表示岗位价值，不等于 portable/official completion role。

## 前置 Gate

- `EXT-CS336-A1` 的全部 `portable-required` groups 分别至少 `reviewed`，或有明确登记、可核实的等价原生 LM capstone 路径；
- sequence/token log-prob、mask/reduction、SFT、DPO 至少 `retained_7d`；
- reward、advantage、KL/entropy、clipping、gradient accumulation 和 optimizer step 至少 `reviewed`；
- 能处理 invalid completion、全组零 reward variance、空 response mask、长度偏置和数值稳定；
- 完整训练前先通过 CPU tiny-model correctness 与 rollout→reward→advantage→update 数据流口试。

## 上游作业覆盖

机器清单固定登记 44 个 Problem（主 handout 28 个、supplement 16 个）、12 个 adapter 和 21 个顶层 test node，覆盖：

1. prompting baseline、tokenization、response log-prob/entropy、rollout reward；
2. GRPO/Dr.GRPO/MaxRL group signal、token/sequence aggregation、on-policy train step；
3. off-policy token clipping、GSPO sequence weighting、train-step variants 与实验；
4. evaluation parser、packed SFT dataset/batches、SFT 与四类 evaluation/red-team；
5. preference data、per-instance DPO loss 与 DPO training。

完整 inventory 同时保留推导/思考 Problem；pytest 只验证部分函数，不能替代实验、推导、评测有效性和 reward hacking 审查。

## 安装与验证

```bash
python scripts/manage_external_course.py show EXT-CS336-A5
python scripts/manage_external_course.py install EXT-CS336-A5 --acknowledge-policy
python scripts/manage_external_course.py status EXT-CS336-A5
python scripts/manage_external_course.py commands EXT-CS336-A5
```

安装即表示用户理解：公开可见不等于获得再分发许可。外部 checkout 应保留为独立本地/private Git 工作区；不得把文件移动到本仓库。

## AI 与学术诚信

最高 H2。允许解释公式、shape、mask、报错与一般 sanity checks；禁止写实现/伪代码、补 adapter、给 objective 推导答案、选择最终超参数或自动编辑/运行官方作业。H3–H5 对官方 assignment 永久禁用；演示只能使用不同接口、不同数据和独立题目。

## 证据与验收

- 用户亲自运行并区分 GRPO required、data/metrics、optional DPO 测试；记录没有运行的 GPU 实验；
- 所有 tensor 说明 batch/group/sequence/vocab shape、response mask、reduction、dtype/device 与梯度边界；
- group reward 覆盖零方差，rollout 覆盖 invalid/unparseable completion，aggregation 覆盖空/不等长 response；
- off-policy 解释 old/new log-prob、importance ratio、token vs sequence weighting 与 clipping bias；
- SFT/DPO 数据说明 prompt/response boundary、padding/label mask、chosen/rejected 和 leakage；
- 实验报告同时看 reward、format、accuracy、length、entropy、KL、invalid rate 与 held-out evaluation，不能只看单一 reward。

## D+2 / D+7

- 复测只针对当前 canonical problem group；GRPO core、variants、off-policy、SFT/eval 与 DPO 等 groups 分别保留状态。
- D+2：不看外部 checkout，以新 tensor/data shape 闭卷重建当前 group 的一项 capability，并覆盖该 group 的关键空值、invalid 或数值边界。
- D+7：改变当前 group 适用的 group size、长度分布、reward、policy lag、packing 或 preference 约束，完成结构变式与 group-specific 口试。
- 使用官方/第三方实现对齐只能发生在独立版本 `reviewed` 后；看到关键答案则重新安排变式。

## 资源与停止条件

- portable companion：CPU tiny tokenizer/model 的 unit tests、formula/shape 和被标为 `portable-required/elective` 的 SFT/DPO/GRPO core；只据此声明 portable aggregate。
- official-full：实际 rollout、训练与评测使用单 GPU/B200；记录模型、数据、预算、seed 和失败实验。未运行时不能声称完成官方 full assignment。
- 外部 evaluator/API：属于额外资源，必须核实许可、版本、费用与泄漏；不能把 judge 输出当绝对真值。
- 无许可证内容被复制、课程答案泄漏、公司/内部数据混入、或 reward 指标改善但 held-out 退化时立即停止并审计。
