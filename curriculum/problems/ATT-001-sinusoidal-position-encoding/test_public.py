import math
import pytest

torch = pytest.importorskip("torch")


def test_position_zero_and_unit_frequency(submission):
    result = submission.sinusoidal_encoding(2, 4, dtype=torch.float64)
    torch.testing.assert_close(result[0], torch.tensor([0., 1., 0., 1.], dtype=torch.float64))
    assert result[1, 0].item() == pytest.approx(math.sin(1))
    assert result[1, 2].item() == pytest.approx(math.sin(0.01))


def test_odd_width_uses_original_dimension(submission):
    result = submission.sinusoidal_encoding(1, 3, offset=2, base=8., dtype=torch.float64)
    torch.testing.assert_close(result, torch.tensor([[math.sin(2), math.cos(2), math.sin(0.5)]], dtype=torch.float64))


def test_offset_chunks_match_full(submission):
    full = submission.sinusoidal_encoding(7, 5)
    chunk = submission.sinusoidal_encoding(4, 5, offset=3)
    torch.testing.assert_close(chunk, full[3:])


def test_empty_and_single_channel(submission):
    result = submission.sinusoidal_encoding(0, 1, dtype=torch.float64, device="cpu")
    assert result.shape == (0, 1) and result.dtype == torch.float64
    assert result.device.type == "cpu"
    torch.testing.assert_close(submission.sinusoidal_encoding(1, 1), torch.zeros(1, 1))


@pytest.mark.parametrize("args", [(-1, 4), (1, 0), (1, 4, -1), (1, 4, 0, 1.), (1, 4, 0, float("inf")), (1.5, 4)])
def test_invalid_contract(submission, args):
    with pytest.raises(ValueError):
        submission.sinusoidal_encoding(*args)


def test_dtype_and_random_state_preserved(submission):
    state = torch.random.get_rng_state().clone()
    assert submission.sinusoidal_encoding(2, 2).dtype == torch.float32
    assert torch.equal(state, torch.random.get_rng_state())
    with pytest.raises(ValueError):
        submission.sinusoidal_encoding(2, 2, dtype=torch.int64)
