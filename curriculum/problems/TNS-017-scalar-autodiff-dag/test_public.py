import math
import pytest


def test_square_plus_x(submission):
    x = submission.Value(3)
    y = x * x + x
    y.backward()
    assert x.grad == 7


def test_same_parent_twice(submission):
    x = submission.Value(2)
    y = x + x
    y.backward()
    assert x.grad == 2


def test_repeat_backward_resets(submission):
    x = submission.Value(3)
    y = x * x
    y.backward()
    y.backward()
    assert x.grad == 6


def test_tanh(submission):
    x = submission.Value(0.3)
    y = x.tanh()
    y.backward()
    assert x.grad == pytest.approx(1 - math.tanh(0.3) ** 2)


def test_scalar_reverse_operators(submission):
    x = submission.Value(2)
    y = 3 * x + 4
    y.backward()
    assert y.data == 10 and x.grad == 3


def test_diamond(submission):
    x = submission.Value(2)
    shared = x * x
    y = shared * 3 + shared * 4
    y.backward()
    assert x.grad == 28
