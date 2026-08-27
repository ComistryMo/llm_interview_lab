# Generate private variant

输入当前 Profile 的目标 Track、已掌握节点、近期错误、允许帮助等级，以及一个固定 `base_problem`。只使用该节点的 `variant_axes`、`invariants`、`common_bugs` 和 retention 契约。

输出到当前 Profile 的 `generated/` 与 `private_tests/`：私人题面、无答案 starter、测试、不变式、口述问题、与基题差异和适配理由。使用固定 seed；不得读取旧答案，不得自动改 Catalog，不得用生成器自己的答案作为唯一 Oracle。
