import pytest
torch=pytest.importorskip("torch")

def test_matches_framework_reference(submission):
    x=torch.randn(2,3,4,dtype=torch.float64)
    assert torch.allclose(submission.stable_logsumexp(x,1),torch.logsumexp(x,1),atol=1e-12)

def test_keepdim_shape(submission):
    x=torch.randn(2,3,4)
    assert submission.stable_logsumexp(x,-1,True).shape==(2,3,1)

def test_large_values_are_finite_and_correct(submission):
    x=torch.tensor([[10000.,10001.]])
    out=submission.stable_logsumexp(x)
    assert torch.isfinite(out).all() and torch.allclose(out,torch.logsumexp(x,-1))

def test_gradient_matches_reference(submission):
    x=torch.randn(2,3,dtype=torch.float64,requires_grad=True); y=x.detach().clone().requires_grad_()
    submission.stable_logsumexp(x,0).sum().backward(); torch.logsumexp(y,0).sum().backward()
    assert torch.allclose(x.grad,y.grad,atol=1e-10)

@pytest.mark.parametrize("x,dim,keep", [(torch.ones(2,3,dtype=torch.long),0,False),(torch.empty(0,3),0,False),(torch.ones(2,3),3,False),(torch.ones(2,3),0,1)])
def test_invalid_contract_raises(submission,x,dim,keep):
    with pytest.raises(ValueError): submission.stable_logsumexp(x,dim,keep)

def test_input_not_mutated(submission):
    x=torch.randn(2,3); before=x.clone(); submission.stable_logsumexp(x)
    assert torch.equal(x,before)

