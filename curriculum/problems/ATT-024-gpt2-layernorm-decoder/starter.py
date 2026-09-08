"""实现 GPT-2 架构契约，不借用其它 learner submission。"""

import torch


def gpt2_block(x, weights, num_heads, cache=None, eps=1e-5):
    raise NotImplementedError("请完成实现")
