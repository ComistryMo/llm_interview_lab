import pytest
torch = pytest.importorskip("torch")

def test_shape_and_value_layout(submission):
    x = torch.arange(24).reshape(2,3,4)
    out = submission.split_heads(x, 2)
    assert out.shape == (2,2,3,2)
    assert torch.equal(out, x.reshape(2,3,2,2).permute(0,2,1,3))

def test_output_is_contiguous(submission):
    assert submission.split_heads(torch.randn(2,3,8), 4).is_contiguous()

def test_dtype_device_and_gradient_are_preserved(submission):
    x = torch.randn(2,3,4, dtype=torch.float64, requires_grad=True)
    out = submission.split_heads(x, 2)
    assert out.dtype == x.dtype and out.device == x.device
    out.sum().backward()
    assert torch.equal(x.grad, torch.ones_like(x))

@pytest.mark.parametrize("shape,heads", [((2,3),2), ((2,3,5),2), ((2,3,4),0), ((2,3,4),True)])
def test_invalid_contract_raises(submission, shape, heads):
    with pytest.raises(ValueError):
        submission.split_heads(torch.zeros(shape), heads)

def test_input_shape_and_values_are_unchanged(submission):
    x = torch.randn(1,2,4)
    before = x.clone()
    submission.split_heads(x, 2)
    assert x.shape == (1,2,4) and torch.equal(x,before)

