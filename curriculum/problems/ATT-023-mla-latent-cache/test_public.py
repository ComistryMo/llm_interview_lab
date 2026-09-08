import pytest

torch = pytest.importorskip("torch")


def weights():
    generator=torch.Generator().manual_seed(230)
    shapes={"w_dkv":(2,6),"w_uk":(6,2),"w_uv":(4,2),"w_dq":(3,6),"w_uq":(6,3),"w_qr":(4,3),"w_kr":(2,6),"wo":(6,4)}
    return {key:torch.randn(shape,generator=generator,dtype=torch.float64)*.4 for key,shape in shapes.items()}


def test_single_token_only_uses_value_path(submission):
    w=weights()
    x=torch.arange(6.,dtype=torch.float64).reshape(1,1,6)/5
    y,cache=submission.mla_attention(x,w,2,torch.tensor([[7]]))
    expected=x@w["w_dkv"].T@w["w_uv"].T@w["wo"].T
    torch.testing.assert_close(y,expected)
    assert cache[0].shape==(1,1,2) and cache[1].shape==(1,1,2)


def test_compressed_cache_and_zero_output_projection(submission):
    w=weights()
    w["wo"].zero_()
    x=torch.arange(36.,dtype=torch.float64).reshape(2,3,6)/17
    y,cache=submission.mla_attention(x,w,2,torch.tensor([[0,1,2],[10,12,15]]))
    torch.testing.assert_close(y,torch.zeros_like(y))
    assert cache[0].shape==(2,3,2) and cache[1].shape==(2,3,2)
    assert sum(t.numel() for t in cache)==2*3*(2+2)


def test_chunked_cache_matches_full_without_mutation(submission):
    x=torch.arange(60.,dtype=torch.float64).reshape(2,5,6).sin()
    positions=torch.tensor([[3,4,8,9,12],[0,2,5,7,11]])
    full,full_cache=submission.mla_attention(x,weights(),2,positions)
    first,cache=submission.mla_attention(x[:,:2],weights(),2,positions[:,:2])
    saved=tuple(t.clone() for t in cache)
    rest,merged=submission.mla_attention(x[:,2:],weights(),2,positions[:,2:],cache)
    torch.testing.assert_close(torch.cat((first,rest),1),full)
    for actual,expected in zip(merged,full_cache):
        torch.testing.assert_close(actual,expected)
    for actual,expected in zip(cache,saved):
        torch.testing.assert_close(actual,expected)


def test_common_position_shift_preserves_relative_rope(submission):
    x=torch.arange(24.,dtype=torch.float64).reshape(1,4,6).cos()
    positions=torch.tensor([[0,2,3,8]])
    a,_=submission.mla_attention(x,weights(),2,positions)
    b,_=submission.mla_attention(x,weights(),2,positions+17)
    torch.testing.assert_close(a,b)


def test_positions_really_affect_attention(submission):
    x=torch.arange(18.,dtype=torch.float64).reshape(1,3,6).sin()
    a,_=submission.mla_attention(x,weights(),2,torch.tensor([[0,1,2]]))
    b,_=submission.mla_attention(x,weights(),2,torch.tensor([[0,1,9]]))
    torch.testing.assert_close(a[:,:2],b[:,:2])
    assert not torch.allclose(a[:,2],b[:,2])


def test_causal_future_isolation(submission):
    x=torch.arange(24.,dtype=torch.float64).reshape(1,4,6).cos()
    changed=x.clone()
    changed[:,2:,0]+=9
    p=torch.arange(4)[None]
    a,_=submission.mla_attention(x,weights(),2,p)
    b,_=submission.mla_attention(changed,weights(),2,p)
    torch.testing.assert_close(a[:,:2],b[:,:2])


def test_all_gradients_connected(submission):
    w={key:value.requires_grad_() for key,value in weights().items()}
    x=torch.arange(18.,dtype=torch.float64).reshape(1,3,6).sin().requires_grad_()
    y,_=submission.mla_attention(x,w,2,torch.arange(3)[None])
    y.square().sum().backward()
    for tensor in (x,*w.values()):
        assert tensor.grad is not None and torch.isfinite(tensor.grad).all()
    assert y.dtype==x.dtype and y.device==x.device


def test_invalid_positions_heads_and_cache(submission):
    x=torch.ones(1,2,6,dtype=torch.float64)
    for positions in (torch.tensor([[0,-1]]),torch.ones(1,2),torch.ones(2,dtype=torch.long)):
        with pytest.raises(ValueError):
            submission.mla_attention(x,weights(),2,positions)
    with pytest.raises(ValueError):
        submission.mla_attention(x,weights(),0,torch.tensor([[0,1]]))
    with pytest.raises(ValueError):
        submission.mla_attention(x,weights(),2,torch.tensor([[0,1]]),base=1.)
    with pytest.raises(ValueError):
        submission.mla_attention(x,weights(),2,torch.tensor([[0,1]]),(torch.zeros(1,2,3),torch.zeros(1,2,2)))
