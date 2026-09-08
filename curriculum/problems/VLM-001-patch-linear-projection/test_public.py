import math
import pytest

torch = pytest.importorskip("torch")


def test_patch_row_major(submission):
    x = torch.arange(16.0).reshape(1, 1, 4, 4)
    y = submission.patch_embedding(x, torch.eye(4), torch.zeros(4), 2)
    torch.testing.assert_close(
        y,
        torch.tensor(
            [
                [
                    [0.0, 1.0, 4.0, 5.0],
                    [2.0, 3.0, 6.0, 7.0],
                    [8.0, 9.0, 12.0, 13.0],
                    [10.0, 11.0, 14.0, 15.0],
                ]
            ]
        ),
    )


def test_channels_before_pixels(submission):
    x = torch.arange(8.0).reshape(1, 2, 2, 2)
    y = submission.patch_embedding(x, torch.eye(8), torch.zeros(8), 2)
    torch.testing.assert_close(y.flatten(), torch.arange(8.0))


def test_conv_equivalence(submission):
    x = torch.randn(2, 3, 6, 4)
    w = torch.randn(5, 12)
    b = torch.randn(5)
    expected = (
        torch.nn.functional.conv2d(x, w.reshape(5, 3, 2, 2), b, stride=2)
        .flatten(2)
        .transpose(1, 2)
    )
    torch.testing.assert_close(submission.patch_embedding(x, w, b, 2), expected)


def test_bad_image_size(submission):
    with pytest.raises(ValueError):
        submission.patch_embedding(
            torch.ones(1, 1, 3, 4), torch.ones(1, 4), torch.zeros(1), 2
        )


def test_p_one(submission):
    x = torch.ones(1, 2, 2, 2)
    y = submission.patch_embedding(x, torch.ones(3, 2), torch.ones(3), 1)
    torch.testing.assert_close(y, torch.full((1, 4, 3), 3.0))
