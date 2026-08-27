import pytest
torch=pytest.importorskip("torch")

def reference(x,c,s):
    even=x[...,0::2]; odd=x[...,1::2]; c=c.view(1,1,*c.shape); s=s.view(1,1,*s.shape)
    return torch.stack((even*c-odd*s,even*s+odd*c),-1).flatten(-2)

def test_matches_pairwise_reference(submission):
    x=torch.randn(2,3,4,6,dtype=torch.float64); theta=torch.randn(4,3,dtype=torch.float64); c=theta.cos(); s=theta.sin()
    assert torch.allclose(submission.apply_rope(x,c,s),reference(x,c,s),atol=1e-12)

def test_zero_angle_is_identity(submission):
    x=torch.randn(1,2,3,4); c=torch.ones(3,2); s=torch.zeros(3,2)
    assert torch.equal(submission.apply_rope(x,c,s),x)

def test_pairwise_norm_is_preserved(submission):
    x=torch.randn(1,2,3,4); theta=torch.randn(3,2); out=submission.apply_rope(x,theta.cos(),theta.sin())
    assert torch.allclose(out.reshape(*out.shape[:-1],-1,2).square().sum(-1),x.reshape(*x.shape[:-1],-1,2).square().sum(-1),atol=1e-5)

def test_gradient_matches_reference(submission):
    x=torch.randn(1,2,3,4,dtype=torch.float64,requires_grad=True); y=x.detach().clone().requires_grad_(); theta=torch.randn(3,2,dtype=torch.float64); c=theta.cos(); s=theta.sin()
    submission.apply_rope(x,c,s).sum().backward(); reference(y,c,s).sum().backward()
    assert torch.allclose(x.grad,y.grad,atol=1e-12)

@pytest.mark.parametrize("x,c,s", [(torch.zeros(2,3,4),torch.zeros(3,2),torch.zeros(3,2)),(torch.zeros(1,1,3,5),torch.zeros(3,2),torch.zeros(3,2)),(torch.zeros(1,1,3,4),torch.zeros(2,2),torch.zeros(2,2)),(torch.zeros(1,1,3,4),torch.zeros(3,2),torch.zeros(3,1))])
def test_invalid_contract_raises(submission,x,c,s):
    with pytest.raises(ValueError): submission.apply_rope(x,c,s)

