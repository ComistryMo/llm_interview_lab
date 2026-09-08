"""最小标量自动微分：独立实现共享计算图。"""


class Value:
    def __init__(self, data):
        self.data = float(data)
        self.grad = 0.0

    def __add__(self, other):
        raise NotImplementedError

    def __radd__(self, other):
        raise NotImplementedError

    def __mul__(self, other):
        raise NotImplementedError

    def __rmul__(self, other):
        raise NotImplementedError

    def tanh(self):
        raise NotImplementedError

    def backward(self):
        raise NotImplementedError
