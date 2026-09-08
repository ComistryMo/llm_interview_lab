"""Dropout 的前向、反向与训练模式：从公开契约独立实现。"""

import numpy as np


def dropout_forward(x, p, training=True, rng=None):
    raise NotImplementedError("请完成实现")


def dropout_backward(upstream, multiplier):
    raise NotImplementedError
