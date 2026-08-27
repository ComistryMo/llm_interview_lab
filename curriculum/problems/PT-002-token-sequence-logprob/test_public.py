import pytest
torch=pytest.importorskip("torch")

def reference(logits,ids,mask):
    selected=torch.log_softmax(logits,-1).gather(-1,ids.unsqueeze(-1)).squeeze(-1)
    token=torch.where(mask,selected,torch.zeros_like(selected))
    return token,token.sum(-1)

def test_values_shapes_and_mask(submission):
    x=torch.randn(2,3,5,dtype=torch.float64); ids=torch.tensor([[0,1,2],[4,3,2]]); mask=torch.tensor([[1,1,0],[0,1,1]],dtype=torch.bool)
    out,seq=submission.token_sequence_logprobs(x,ids,mask); ro,rs=reference(x,ids,mask)
    assert out.shape==(2,3) and seq.shape==(2,) and torch.allclose(out,ro,atol=1e-10) and torch.allclose(seq,rs,atol=1e-10)

def test_large_logits_are_finite(submission):
    x=torch.tensor([[[10000.,9999.]]]); ids=torch.tensor([[0]]); mask=torch.tensor([[1]],dtype=torch.bool)
    token,seq=submission.token_sequence_logprobs(x,ids,mask)
    assert torch.isfinite(token).all() and torch.isfinite(seq).all()

def test_gradient_matches_reference(submission):
    x=torch.randn(1,2,3,dtype=torch.float64,requires_grad=True); y=x.detach().clone().requires_grad_(); ids=torch.tensor([[0,2]]); m=torch.ones(1,2,dtype=torch.bool)
    submission.token_sequence_logprobs(x,ids,m)[1].sum().backward(); reference(y,ids,m)[1].sum().backward()
    assert torch.allclose(x.grad,y.grad,atol=1e-10)

def test_masked_positions_have_zero_gradient(submission):
    x=torch.randn(1,2,3,requires_grad=True); ids=torch.tensor([[0,1]]); m=torch.tensor([[1,0]],dtype=torch.bool)
    submission.token_sequence_logprobs(x,ids,m)[1].sum().backward()
    assert torch.equal(x.grad[:,1],torch.zeros_like(x.grad[:,1]))

@pytest.mark.parametrize("x,ids,m", [(torch.zeros(2,3),torch.zeros(2,dtype=torch.long),torch.ones(2,dtype=torch.bool)),(torch.zeros(1,2,3),torch.tensor([[3,0]]),torch.ones(1,2,dtype=torch.bool)),(torch.zeros(1,2,3),torch.tensor([[0,1]]),torch.zeros(1,2,dtype=torch.bool)),(torch.zeros(1,2,3),torch.tensor([[0.,1.]]),torch.ones(1,2,dtype=torch.bool))])
def test_invalid_contract_raises(submission,x,ids,m):
    with pytest.raises(ValueError): submission.token_sequence_logprobs(x,ids,m)

