import math
import pytest
torch=pytest.importorskip("torch")

def reference(q,k,v,h,mask=None):
    b,ql,hidden=q.shape; d=hidden//h; q=q.reshape(b,ql,h,d).transpose(1,2)
    s=q@k.unsqueeze(1).transpose(-2,-1)/math.sqrt(d)
    if mask is not None:s=s.masked_fill(~mask,float("-inf"))
    return (torch.softmax(s,-1)@v.unsqueeze(1)).transpose(1,2).reshape(b,ql,h*v.shape[-1])

def test_reference_and_shape(submission):
    q=torch.randn(2,3,8,dtype=torch.float64); k=torch.randn(2,5,2,dtype=torch.float64); v=torch.randn(2,5,3,dtype=torch.float64)
    out=submission.multi_query_attention(q,k,v,4)
    assert out.shape==(2,3,12) and torch.allclose(out,reference(q,k,v,4),atol=1e-10)

def test_shared_values_feed_every_head(submission):
    q=k=torch.zeros(1,2,2); q=torch.zeros(1,2,4); v=torch.tensor([[[1.,2.],[3.,4.]]])
    out=submission.multi_query_attention(q,k,v,2)
    assert torch.allclose(out,torch.tensor([[[2.,3.,2.,3.],[2.,3.,2.,3.]]]))

def test_mask_reference(submission):
    q=torch.randn(1,2,4); k=torch.randn(1,3,2); v=torch.randn(1,3,2); m=torch.tensor([[[[1,0,0],[1,1,0]]]],dtype=torch.bool)
    assert torch.allclose(submission.multi_query_attention(q,k,v,2,m),reference(q,k,v,2,m))

def test_gradients_reach_shared_kv(submission):
    q=torch.randn(1,2,4,requires_grad=True); k=torch.randn(1,3,2,requires_grad=True); v=torch.randn(1,3,2,requires_grad=True)
    submission.multi_query_attention(q,k,v,2).sum().backward()
    assert q.grad is not None and k.grad is not None and v.grad is not None

@pytest.mark.parametrize("q,k,v,h", [(torch.zeros(1,2,5),torch.zeros(1,2,2),torch.zeros(1,2,2),2),(torch.zeros(1,2,4),torch.zeros(1,3,3),torch.zeros(1,3,2),2),(torch.zeros(1,2,4),torch.zeros(1,3,2),torch.zeros(1,2,2),2),(torch.zeros(1,2,4),torch.zeros(1,2,2),torch.zeros(1,2,2),0)])
def test_invalid_contract_raises(submission,q,k,v,h):
    with pytest.raises(ValueError): submission.multi_query_attention(q,k,v,h)

