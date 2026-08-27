import math
import pytest
torch=pytest.importorskip("torch")

def reference(q,k,v,mask=None):
    scores=q@k.transpose(-2,-1)/math.sqrt(q.shape[-1])
    if mask is not None: scores=scores.masked_fill(~mask,float("-inf"))
    probs=torch.softmax(scores,-1)
    return probs@v,probs

def test_values_and_probabilities_match_reference(submission):
    q=torch.randn(2,3,4,5,dtype=torch.float64); k=torch.randn(2,3,6,5,dtype=torch.float64); v=torch.randn(2,3,6,7,dtype=torch.float64)
    out,p=submission.scaled_dot_product_attention(q,k,v); ro,rp=reference(q,k,v)
    assert out.shape==(2,3,4,7) and p.shape==(2,3,4,6) and torch.allclose(out,ro,atol=1e-10) and torch.allclose(p,rp,atol=1e-10)

def test_boolean_mask_zeroes_forbidden_positions(submission):
    q=k=v=torch.randn(1,1,3,4); mask=torch.tensor([[[[1,1,0],[1,0,0],[1,1,1]]]],dtype=torch.bool)
    _,p=submission.scaled_dot_product_attention(q,k,v,mask)
    assert torch.equal(p.masked_select(~mask),torch.zeros(3)) and torch.allclose(p.sum(-1),torch.ones(1,1,3))

def test_causal_mask_prevents_future_attention(submission):
    q=k=v=torch.randn(1,2,4,3); _,p=submission.scaled_dot_product_attention(q,k,v,causal=True)
    assert torch.equal(torch.triu(p,diagonal=1),torch.zeros_like(p))

def test_gradient_matches_reference(submission):
    q=torch.randn(1,2,3,4,dtype=torch.float64,requires_grad=True); k=torch.randn_like(q,requires_grad=True); v=torch.randn_like(q,requires_grad=True)
    q2=q.detach().clone().requires_grad_(); k2=k.detach().clone().requires_grad_(); v2=v.detach().clone().requires_grad_()
    submission.scaled_dot_product_attention(q,k,v)[0].sum().backward(); reference(q2,k2,v2)[0].sum().backward()
    assert torch.allclose(q.grad,q2.grad,atol=1e-10) and torch.allclose(k.grad,k2.grad,atol=1e-10) and torch.allclose(v.grad,v2.grad,atol=1e-10)

@pytest.mark.parametrize("q,k,v", [(torch.zeros(2,3,4),torch.zeros(2,3,4),torch.zeros(2,3,4)),(torch.zeros(1,1,2,3),torch.zeros(1,1,2,4),torch.zeros(1,1,2,3)),(torch.zeros(1,1,2,3),torch.zeros(1,1,3,3),torch.zeros(1,1,2,3))])
def test_invalid_shapes_raise(submission,q,k,v):
    with pytest.raises(ValueError): submission.scaled_dot_product_attention(q,k,v)

def test_fully_masked_row_raises(submission):
    x=torch.randn(1,1,2,3); mask=torch.tensor([[[[1,0],[0,0]]]],dtype=torch.bool)
    with pytest.raises(ValueError): submission.scaled_dot_product_attention(x,x,x,mask)

