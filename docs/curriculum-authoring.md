# Curriculum Authoring

Catalog shards 是唯一课程元数据源。ready/stable 节点必须有严格四文件目录；planned 节点不得有目录。所有 ID 唯一、前置存在、DAG 无环、Track 引用有效。

题面必须定义接口、输入输出、shape、dtype/device、异常、禁止 API、mutation、复杂度与数值稳定要求。测试只依赖注入的 `submission` fixture，不 import starter、不改 `sys.path`、不硬编码 Workspace，也不复制 loader。

公开测试至少覆盖正常、边界、异常、不变式和 non-mutation。PyTorch 题按适用项覆盖 shape、dtype、device、gradient、mask、稳定性及透明官方参考。公开仓库没有真正隐藏测试；私人变式进入当前 Profile。

Runner 与 Oracle 分开：Runner 当前为 pytest；Oracle 只能是 `fixture_expected`、`closed_form`、`framework_reference`、`brute_force`、`cross_implementation`、`property_only`。来源优先论文、官方文档与官方源码，但题面和测试必须 clean-room 重写。

提示分 H1 概念检查、H2 结构、H3 步骤，不给完整函数。`variant_axes` 描述可改变维度，`invariants` 描述必须保持的性质，`common_bugs` 驱动调试变式。D+2 是无旧答案等价复写，D+7 是边界、调试或集成迁移。
