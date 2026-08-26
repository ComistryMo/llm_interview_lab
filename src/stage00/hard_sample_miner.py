"""Task 00A / 00B：根据多次推理结果筛选困难样本。

这个训练任务只使用完全虚构的 toy 数据，不对应任何真实业务实现。
禁止放入任何第三方内部数据。
"""

from typing import Any


def count_wrong_predictions(label: int, predictions: list[int]) -> int:
    """返回 predictions 中与 label 不相等的预测数量。

    示例：
        label = 1
        predictions = [1, 0, 0]
        返回 2

    要求：
    - predictions 不能为空；
    - 每个预测都应是 int；
    - 不要修改传入的列表。
    """
    if len(predictions) == 0:
        raise ValueError("predictions cannot be empty")
    nums = 0
    for i in predictions:
        if label != i:
            nums += 1
    return nums
    raise NotImplementedError("TODO: implement count_wrong_predictions")


def select_hard_samples(
    samples: list[dict[str, Any]],
    min_wrong: int = 2,
) -> list[dict[str, Any]]:
    """筛选错误次数不少于 min_wrong 的样本。

    每个样本的格式：

    {
        "id": "sample-001",
        "label": 1,
        "predictions": [1, 0, 0],
    }

    要求：
    - 保持原始顺序；
    - 返回一个新的 list；
    - 不修改 samples 及其内部字典；
    - min_wrong 必须大于 0；
    - 缺少字段时抛出 ValueError；
    - predictions 为空时抛出 ValueError。
    """
    raise NotImplementedError("TODO: implement select_hard_samples")


def summarize_hard_samples(
    samples: list[dict[str, Any]],
    min_wrong: int = 2,
) -> dict[str, Any]:
    """Task 00B：返回简单统计信息。

    期望返回：

    {
        "total": 4,
        "hard_count": 2,
        "hard_ratio": 0.5,
        "hard_count_by_label": {
            0: 1,
            1: 1,
        },
    }

    空输入时 hard_ratio 应为 0.0。
    """
    raise NotImplementedError("TODO: implement summarize_hard_samples")
