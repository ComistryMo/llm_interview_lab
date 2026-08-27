import pytest
torch = pytest.importorskip("torch")

def test_broadcast_values_and_shape(submission):
    x = torch.zeros(2,3,4)
    bias = torch.tensor([1.,2.,3.,4.])
    out = submission.broadcast_add_bias(x,bias)
    assert out.shape == x.shape and torch.equal(out, bias.view(1,1,4).expand_as(x))

def test_nonzero_input_matches_reference(submission):
    x=torch.randn(2,1,3); b=torch.randn(3)
    assert torch.allclose(submission.broadcast_add_bias(x,b), x+b)

def test_gradient_reduces_over_broadcast_dimensions(submission):
    x=torch.randn(2,3,4,requires_grad=True); b=torch.randn(4,requires_grad=True)
    submission.broadcast_add_bias(x,b).sum().backward()
    assert torch.equal(x.grad,torch.ones_like(x))
    assert torch.equal(b.grad,torch.full_like(b,6))

@pytest.mark.parametrize("x_shape,b_shape", [((2,3), (3,)), ((2,3,4),(1,4)), ((2,3,4),(5,))])
def test_invalid_shapes_raise(submission,x_shape,b_shape):
    with pytest.raises(ValueError):
        submission.broadcast_add_bias(torch.zeros(x_shape),torch.zeros(b_shape))

def test_dtype_mismatch_and_nonmutation(submission):
    x=torch.zeros(1,1,2); b=torch.ones(2,dtype=torch.float64); before=x.clone()
    with pytest.raises(ValueError): submission.broadcast_add_bias(x,b)
    assert torch.equal(x,before)

