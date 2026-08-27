import math
import pytest
torch=pytest.importorskip("torch")

def reference(q,k,v,h,mask=None):
    b,ql,hd=q.shape; kl=k.shape[1]; d=hd//h; dv=v.shape[-1]//h
    q=q.reshape(b,ql,h,d).transpose(1,2); k=k.reshape(b,kl,h,d).transpose(1,2); v=v.reshape(b,kl,h,dv).transpose(1,2)
    s=q@k.transpose(-2,-1)/math.sqrt(d)
    if mask is not None: s=s.masked_fill(~mask,float("-inf"))
    return (torch.softmax(s,-1)@v).transpose(1,2).contiguous().reshape(b,ql,h*dv)

def test_shape_and_reference(submission):
    q=torch.randn(2,3,8,dtype=torch.float64); k=torch.randn(2,5,8,dtype=torch.float64); v=torch.randn(2,5,12,dtype=torch.float64)
    out=submission.multi_head_attention(q,k,v,4)
    assert out.shape==(2,3,12) and torch.allclose(out,reference(q,k,v,4),atol=1e-10)

def test_heads_are_independent(submission):
    q=k=torch.zeros(1,2,4); v=torch.tensor([[[1.,2.,10.,20.],[3.,4.,30.,40.]]])
    assert torch.allclose(submission.multi_head_attention(q,k,v,2),v.mean(1,keepdim=True).expand_as(v))

def test_mask_is_applied_per_head(submission):
    q=k=v=torch.randn(1,3,4); mask=torch.tensor([[[[1,0,0],[1,1,0],[1,1,1]]]],dtype=torch.bool)
    assert torch.allclose(submission.multi_head_attention(q,k,v,2,mask),reference(q,k,v,2,mask))

def test_gradients_reach_all_inputs(submission):
    q=torch.randn(1,2,4,requires_grad=True); k=torch.randn(1,3,4,requires_grad=True); v=torch.randn(1,3,4,requires_grad=True)
    submission.multi_head_attention(q,k,v,2).sum().backward()
    assert q.grad is not None and k.grad is not None and v.grad is not None

@pytest.mark.parametrize("q,k,v,h", [(torch.zeros(2,3),torch.zeros(2,3),torch.zeros(2,3),1),(torch.zeros(1,2,5),torch.zeros(1,2,5),torch.zeros(1,2,4),2),(torch.zeros(1,2,4),torch.zeros(1,3,4),torch.zeros(1,2,4),2),(torch.zeros(1,2,4),torch.zeros(1,2,4),torch.zeros(1,2,4),True)])
def test_invalid_contract_raises(submission,q,k,v,h):
    with pytest.raises(ValueError): submission.multi_head_attention(q,k,v,h)

def test_input_is_not_mutated(submission):
    q=torch.randn(1,2,4); before=q.clone(); submission.multi_head_attention(q,q,q,2)
    assert torch.equal(q,before)

