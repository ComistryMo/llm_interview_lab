# NNL-018 训练闭环候选 · 等待人工审查

状态：`AUTHOR_PENDING_REVIEW`。不是已开放课程，不进入 Catalog、D+2/D+7 复测推荐、已验证题数或掌握证据。基础题 NNL-018 已有 Oracle，但没有已验证复测变式，因此补两个实质不同的梯度迁移场景，而非重复堆基础题。

| 候选 | 目标 | 与基础题的区别 |
|---|---|---|
| D+2：微批梯度累积 | 保持各批输入梯度，累积共享参数梯度 | 不同 leading shape、空批和分块不变性；区分求和与均值 |
| D+7：共享词嵌入与输出投影 | 正确合并同一参数的两条梯度路径 | 重复 token 的散加、两路证据、有限差分交叉验证 |

素材都是原创合成张量；无雇主数据、上游作业或现成答案。public tests 只给输入/输出或不变量，不提供实现。H1–H3 不含完整解法；私有 Oracle 与有限差分在本轮 ignored 维护目录，不能进入发布包。

来源：[PyTorch Linear 官方契约](https://docs.pytorch.org/docs/2.9/generated/torch.nn.Linear.html)、[Embedding 官方契约](https://docs.pytorch.org/docs/2.9/generated/torch.nn.Embedding.html)、[Press & Wolf：共享输出嵌入](https://arxiv.org/abs/1608.05859)。D+7 为基于上述参数共享关系设计的独立 VJP 练习，不声称论文的语言模型收益已在本题重现。

人工审查清单：契约/测试一致、非同构迁移、空批/广播/非连续输入、不变性、复杂度、提示等级、题面是否清楚区分 independent hidden 与从 embedding 推导的 hidden。验收合格后再按已有 `validate_oracle.py` 和 retention 流程生成 fingerprint，禁止手工提升状态。当前不改变 NNL-018 及历史会话。

维护者定向验证结果记录在本轮候选报告；仅 AI/自动测试通过不能替代人工 Review 或真实 D+2/D+7 无帮助复测。
