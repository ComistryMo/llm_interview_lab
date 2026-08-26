# EXT-CS336-A4：Data Companion

## 定位与边界

本卡覆盖 Stanford CS336 Spring 2026 Assignment 4 的网页抽取、语言识别、PII、内容安全、质量过滤/分类、exact/MinHash 去重、完整预训练数据流水线、tokenization 与训练对照。它不复制官方 PDF、tests、fixtures、模型、数据、配置或 staff training implementation。

根 MIT LICENSE 不能自动替第三方网页、书籍、模型权重、数据集或测试 fixture 授权；任何真实资产必须逐项审计 provenance。

上游 checkout 含 A1 staff training implementation，因此也属于 `EXT-CS336-A1` 答案泄漏源；只有 A1 集成 Gate 通过并显式确认 spoiler 后才能安装。整份 assignment 是聚合 Gate；当前 `integration_status=inventory-audited` 只允许安装与 Preview，升级为 `implementation-ready` 后每次才可登记一个 `EXT-CS336-A4-<group>`。

## 前置 Gate

- `EXT-CS336-A1` 的全部 `portable-required` groups 分别至少 `reviewed`，或有明确登记、可核实的等价原生 LM capstone 路径；安装 A4 时还必须单独确认 A1 staff material 的 spoiler 风险；
- 文件/JSONL、iterator、异常、pytest、hash/set、正则与多进程边界至少 `retained_7d`；
- 数据模型、泄漏检查、determinism 与数据卡能口述；
- end-to-end LM A/B 前，tokenizer、training loop、checkpoint 和 Transformer 至少 `reviewed`；
- 所有默认任务先用自写安全 fixture 与 fake predictor 离线完成。

## 上游作业覆盖

机器清单固定登记 13 个 Problem、11 个 adapter 和 21 个顶层 test node：

1. Common Crawl/WARC/WET 检查与 bytes-to-text；
2. language ID、email/phone/IP masking、NSFW/toxicity；
3. rule quality 与 learned quality classifier；
4. exact-line dedup、MinHash/LSH/Jaccard/传递聚类；
5. filtering pipeline、人工 retained/removed audit、tokenization 和 LM A/B。

上游 pytest 对 classifier 多为少量 sanity case；没有充分覆盖阈值、非法 IPv4、空文档、hash collision、传递簇、确定性、泄漏或端到端训练。上游提交脚本容忍 pytest 失败，因此不能作为本仓库 Gate。

## 安装与验证

```bash
python scripts/manage_external_course.py show EXT-CS336-A4
python scripts/manage_external_course.py install EXT-CS336-A4 --acknowledge-policy --acknowledge-spoilers
python scripts/manage_external_course.py status EXT-CS336-A4
python scripts/manage_external_course.py commands EXT-CS336-A4
```

网络、真实 classifier、WET、Modal、W&B 与多 GPU 只在用户显式 opt-in 后运行；默认 CI 不下载模型、不访问网页、不处理真实 PII。

## AI 与学术诚信

最高 H2。AI 可解释库接口、错误、指标与高层数据治理，但不能写 pipeline、正则/阈值答案、MinHash/LSH 伪代码、filter 顺序或训练实现。代码审查必须以提问、invariant 与 missing-evidence 形式进行。

## 证据与验收

- 每个 stage 有输入/输出 schema、失败策略、计数、seed/version 和确定性说明；
- classifier 通过依赖注入测试，区分 label、score、threshold 与 calibration；
- PII 评估同时记录 false positive/negative，测试数据不得含真实个人信息；
- dedup 覆盖跨文件、空行、collision、fuzzy threshold、传递簇与稳定保留规则；
- leakage audit 在 tokenize/train 之前，数据卡记录来源、许可、过滤、删除和限制；
- 大规模 pipeline/训练没有运行时写 `not_run`；tiny A/B 不能冒充官方 8×B200 结果。

## D+2 / D+7

- 复测只针对当前 canonical problem group；classification/privacy、dedup 与 end-to-end data 分别保留状态。
- D+2：用新 synthetic JSONL/HTML fixture 闭卷重写当前 group 的一个 primitive，测试不查看官方 fixture。
- D+7：改变当前 group 适用的 predictor、shard、阈值、collision、异常编码或 pipeline 顺序，完成确定性变式与相应审计 artifact。
- 若输入 fixture 来源不清、不能解释误删/漏删、或只靠上游少量 sanity tests，不得记 retention。

## 资源与停止条件

- portable companion：CPU/offline primitive、fake model、synthetic shard 和 pipeline smoke；这是 `portable-required/elective` group 的验收层。
- official-full：真实公开模型/数据和完整训练必须有 URL、版本、checksum、license、缓存与成本记录；无资源时写 `not_run`，不得声称官方 full completion。
- optional：自有单 GPU tiny LM A/B 可作额外证据；多 B200 结果不是 portable Gate。
- 发现公司数据、内部样本、真实 PII、未授权网页/模型，或无法核实数据许可证时立即停止并删除未提交临时材料。
