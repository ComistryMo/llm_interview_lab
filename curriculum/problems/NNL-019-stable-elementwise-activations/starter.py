"""三个独立激活接口；不包含 Linear 投影。"""

import torch


def manual_relu(x):
    raise NotImplementedError("请完成实现")


def stable_sigmoid(x):
    raise NotImplementedError("请完成实现")


def swiglu_activation(gate, up):
    raise NotImplementedError("请完成实现")
