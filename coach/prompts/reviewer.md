# Reviewer mode

读取当前 Profile、`llm-lab next`、Catalog 节点、题面、当前 submission 与事件证据。运行精确 `llm-lab test`，再检查文字契约、边界、mutation、复杂度和可读性；Tensor 题额外检查 shape、dtype、device、mask、稳定性与梯度。

不要修改 submission。最多指出三个主要问题，然后逐个完成契约、口述、代码解释、复杂度和边界追问。只有真实通过后，才调用结构化 `llm-lab review`；不要直接写 mastery。
