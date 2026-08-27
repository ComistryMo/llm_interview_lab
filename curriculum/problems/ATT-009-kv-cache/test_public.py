import pytest
torch=pytest.importorskip("torch")

def make(submission):
    return submission.KVCache(2,5,3,4,dtype=torch.float32,device="cpu")

def test_preallocation_and_initial_length(submission):
    cache=make(submission)
    assert cache.length==0 and cache.key_cache.shape==(2,3,5,4) and cache.value_cache.shape==(2,3,5,4)

def test_append_returns_populated_prefix(submission):
    cache=make(submission); k=torch.randn(2,3,2,4); v=torch.randn(2,3,2,4)
    keys,values=cache.append(k,v)
    assert cache.length==2 and torch.equal(keys,k) and torch.equal(values,v) and keys.shape==(2,3,2,4)

def test_multiple_appends_preserve_order(submission):
    cache=make(submission); a=torch.ones(2,3,1,4); b=torch.full((2,3,2,4),2.)
    keys,_=cache.append(a,a); keys,_=cache.append(b,b)
    assert cache.length==3 and torch.equal(keys[:,:,:1],a) and torch.equal(keys[:,:,1:],b)

def test_cached_values_are_detached_copies(submission):
    cache=make(submission); k=torch.randn(2,3,1,4,requires_grad=True); v=torch.randn_like(k)
    keys,_=cache.append(k,v)
    assert not keys.requires_grad
    with torch.no_grad(): k.add_(10)
    assert not torch.equal(keys,k)

@pytest.mark.parametrize("k,v", [(torch.zeros(1,3,1,4),torch.zeros(1,3,1,4)),(torch.zeros(2,2,1,4),torch.zeros(2,2,1,4)),(torch.zeros(2,3,1,5),torch.zeros(2,3,1,5)),(torch.zeros(2,3,1,4,dtype=torch.float64),torch.zeros(2,3,1,4,dtype=torch.float64))])
def test_invalid_append_is_atomic(submission,k,v):
    cache=make(submission)
    with pytest.raises(ValueError): cache.append(k,v)
    assert cache.length==0

def test_overflow_is_rejected_without_length_change(submission):
    cache=make(submission); x=torch.zeros(2,3,4,4); cache.append(x,x)
    with pytest.raises(ValueError): cache.append(torch.zeros(2,3,2,4),torch.zeros(2,3,2,4))
    assert cache.length==4

