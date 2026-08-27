import pytest
torch=pytest.importorskip("torch")

def reference(x,weight,eps):
    work=x.float() if x.dtype in (torch.float16,torch.bfloat16) else x
    return (work*torch.rsqrt(work.square().mean(-1,keepdim=True)+eps)).to(x.dtype)*weight

def test_shape_parameter_and_reference(submission):
    layer=submission.RMSNorm(4,1e-6).double(); x=torch.randn(2,3,4,dtype=torch.float64)
    assert tuple(layer.weight.shape)==(4,) and torch.allclose(layer(x),reference(x,layer.weight,layer.eps),atol=1e-12)

def test_scale_parameter_is_applied(submission):
    layer=submission.RMSNorm(2)
    with torch.no_grad(): layer.weight.copy_(torch.tensor([2.,3.]))
    x=torch.tensor([[1.,1.]])
    assert torch.allclose(layer(x),torch.tensor([[2.,3.]]),atol=1e-5)

def test_zero_input_is_finite(submission):
    out=submission.RMSNorm(3)(torch.zeros(2,3))
    assert torch.isfinite(out).all() and torch.equal(out,torch.zeros_like(out))

def test_gradients_reach_input_and_weight(submission):
    layer=submission.RMSNorm(3).double(); x=torch.randn(2,3,dtype=torch.float64,requires_grad=True)
    layer(x).sum().backward()
    assert x.grad is not None and layer.weight.grad is not None

def test_low_precision_output_dtype(submission):
    layer=submission.RMSNorm(4).to(dtype=torch.float16); x=torch.randn(2,4,dtype=torch.float16)
    assert layer(x).dtype==torch.float16 and torch.isfinite(layer(x)).all()

@pytest.mark.parametrize("dim,eps", [(0,1e-6),(True,1e-6),(3,0),(3,float("inf"))])
def test_invalid_constructor_raises(submission,dim,eps):
    with pytest.raises(ValueError): submission.RMSNorm(dim,eps)

