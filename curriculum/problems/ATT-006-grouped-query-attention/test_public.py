import math
import pytest
torch=pytest.importorskip("torch")

def reference(q,k,v,hq,hkv):
    b,ql,_=q.shape; kl=k.shape[1]; d=k.shape[-1]//hkv; dv=v.shape[-1]//hkv; groups=hq//hkv
    q=q.reshape(b,ql,hq,d).transpose(1,2); k=k.reshape(b,kl,hkv,d).transpose(1,2); v=v.reshape(b,kl,hkv,dv).transpose(1,2)
    k=k.repeat_interleave(groups,1); v=v.repeat_interleave(groups,1)
    out=torch.softmax(q@k.transpose(-2,-1)/math.sqrt(d),-1)@v
    return out.transpose(1,2).reshape(b,ql,hq*dv)

def test_reference_and_shape(submission):
    q=torch.randn(2,3,16,dtype=torch.float64); k=torch.randn(2,5,8,dtype=torch.float64); v=torch.randn(2,5,12,dtype=torch.float64)
    out=submission.grouped_query_attention(q,k,v,8,4)
    assert out.shape==(2,3,24) and torch.allclose(out,reference(q,k,v,8,4),atol=1e-10)

def test_mha_equivalence_when_head_counts_equal(submission):
    q=torch.randn(1,2,4); k=torch.randn(1,3,4); v=torch.randn(1,3,4)
    assert torch.allclose(submission.grouped_query_attention(q,k,v,2,2),reference(q,k,v,2,2))

def test_mqa_equivalence_with_one_kv_head(submission):
    q=torch.randn(1,2,8); k=torch.randn(1,3,2); v=torch.randn(1,3,3)
    assert torch.allclose(submission.grouped_query_attention(q,k,v,4,1),reference(q,k,v,4,1))

def test_gradients_accumulate_into_shared_kv(submission):
    q=torch.randn(1,2,8,requires_grad=True); k=torch.randn(1,3,4,requires_grad=True); v=torch.randn(1,3,4,requires_grad=True)
    submission.grouped_query_attention(q,k,v,4,2).sum().backward()
    assert q.grad is not None and k.grad is not None and v.grad is not None

@pytest.mark.parametrize("hq,hkv", [(3,2),(0,1),(4,0),(True,1)])
def test_invalid_head_configuration(submission,hq,hkv):
    q=torch.zeros(1,2,8); k=v=torch.zeros(1,2,4)
    with pytest.raises(ValueError): submission.grouped_query_attention(q,k,v,hq,hkv)

