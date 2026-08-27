import pytest
torch=pytest.importorskip("torch")

def test_matches_reference_on_rank_three(submission):
    x=torch.randn(2,3,4,dtype=torch.float64)
    assert torch.allclose(submission.stable_softmax(x,1),torch.softmax(x,1),atol=1e-12,rtol=1e-10)

def test_large_logits_remain_finite(submission):
    x=torch.tensor([[10000.,10001.,9999.]])
    out=submission.stable_softmax(x,-1)
    assert torch.isfinite(out).all() and torch.allclose(out.sum(-1),torch.ones(1))

def test_shift_invariance(submission):
    x=torch.randn(3,5)
    assert torch.allclose(submission.stable_softmax(x),submission.stable_softmax(x+12345),atol=1e-4)

def test_gradient_matches_framework(submission):
    x=torch.randn(2,4,dtype=torch.float64,requires_grad=True); y=x.detach().clone().requires_grad_()
    submission.stable_softmax(x,1)[:,0].sum().backward(); torch.softmax(y,1)[:,0].sum().backward()
    assert torch.allclose(x.grad,y.grad,atol=1e-10)

@pytest.mark.parametrize("x,dim", [(torch.tensor([1,2]),0),(torch.empty(2,0),1),(torch.ones(2,3),2),(torch.ones(2,3),True)])
def test_invalid_contract_raises(submission,x,dim):
    with pytest.raises(ValueError): submission.stable_softmax(x,dim)

def test_input_not_mutated(submission):
    x=torch.randn(2,3); before=x.clone(); submission.stable_softmax(x)
    assert torch.equal(x,before)

