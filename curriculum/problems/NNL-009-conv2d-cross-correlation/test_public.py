import math
import pytest

torch = pytest.importorskip("torch")


def test_small_values(submission):
    y = submission.conv2d(
        torch.arange(1.0, 10.0).reshape(1, 1, 3, 3), torch.ones(1, 1, 2, 2)
    )
    torch.testing.assert_close(y, torch.tensor([[[[12.0, 16.0], [24.0, 28.0]]]]))


def test_kernel_not_flipped(submission):
    x = torch.tensor([[[[1.0, 0.0], [0.0, 0.0]]]])
    w = torch.tensor([[[[2.0, 3.0], [4.0, 5.0]]]])
    assert submission.conv2d(x, w).item() == 2


def test_channels_and_bias(submission):
    y = submission.conv2d(
        torch.ones(1, 2, 1, 1), torch.ones(3, 2, 1, 1), torch.tensor([1.0, 2.0, 3.0])
    )
    torch.testing.assert_close(y.flatten(), torch.tensor([3.0, 4.0, 5.0]))


def test_stride_padding_reference(submission):
    x = torch.randn(2, 2, 5, 6)
    w = torch.randn(3, 2, 3, 2)
    torch.testing.assert_close(
        submission.conv2d(x, w, stride=2, padding=1),
        torch.nn.functional.conv2d(x, w, stride=2, padding=1),
    )


def test_kernel_too_large(submission):
    with pytest.raises(ValueError):
        submission.conv2d(torch.ones(1, 1, 2, 2), torch.ones(1, 1, 3, 3))
