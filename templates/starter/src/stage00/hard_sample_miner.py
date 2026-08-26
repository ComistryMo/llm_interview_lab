"""Stage 00：根据虚构的多次推理结果处理困难样本。

这里只允许使用完全虚构的 toy 数据，不对应任何真实业务实现。
"""

from typing import Any


def count_wrong_predictions(label: int, predictions: list[int]) -> int:
    """返回 predictions 中与 label 不相等的预测数量。

    要求见 curriculum/stage00/TASK_00A1.md。
    """
    raise NotImplementedError("TODO: implement count_wrong_predictions")


def select_hard_samples(
    samples: list[dict[str, Any]],
    min_wrong: int = 2,
) -> list[dict[str, Any]]:
    """筛选错误次数不少于 min_wrong 的样本。

    要求见 curriculum/stage00/TASK_00A2.md。前置 Gate 未通过前不要实现。
    """
    raise NotImplementedError("TODO: implement select_hard_samples")


def summarize_hard_samples(
    samples: list[dict[str, Any]],
    min_wrong: int = 2,
) -> dict[str, Any]:
    """返回困难样本统计。

    要求见 curriculum/stage00/TASK_00B.md。前置 Gate 未通过前不要实现。
    """
    raise NotImplementedError("TODO: implement summarize_hard_samples")
