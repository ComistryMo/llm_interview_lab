import pytest

torch = pytest.importorskip("torch")


def weights():
    generator = torch.Generator().manual_seed(240)
    shapes = {"wqkv":(12,4), "bqkv":(12,), "wo":(4,4), "bo":(4,), "w1":(16,4), "b1":(16,), "w2":(4,16), "b2":(4,)}
    result = {key:torch.randn(shape, generator=generator, dtype=torch.float64)*.2 for key,shape in shapes.items()}
    for index in (1,2):
        result[f"ln{index}_weight"] = torch.tensor([1., .8, 1.2, .6], dtype=torch.float64)
        result[f"ln{index}_bias"] = torch.tensor([.1, -.2, .3, .05], dtype=torch.float64)*index
    return result


def test_zero_output_branches_give_identity(submission):
    w=weights()
    for key in ("wo","bo","w2","b2"):
        w[key].zero_()
    x=torch.arange(12.,dtype=torch.float64).reshape(1,3,4)
    result,cache=submission.gpt2_block(x,w,2)
    torch.testing.assert_close(result,x)
    assert cache[0].shape == (1,2,3,2) and cache[1].shape == (1,2,3,2)


def test_layernorm_removes_common_feature_shift(submission):
    x=torch.tensor([[[1.,-2.,.5,3.],[.2,.8,2.,-1.]]],dtype=torch.float64)
    left,_=submission.gpt2_block(x,weights(),2)
    right,_=submission.gpt2_block(x+7.,weights(),2)
    torch.testing.assert_close(right,left+7.)


def test_future_cannot_change_past(submission):
    x=torch.arange(16.,dtype=torch.float64).reshape(1,4,4)/9
    modified=x.clone()
    modified[:,2:,0]+=20
    a,_=submission.gpt2_block(x,weights(),2)
    b,_=submission.gpt2_block(modified,weights(),2)
    torch.testing.assert_close(a[:,:2],b[:,:2])
    assert not torch.allclose(a[:,2:],b[:,2:])


def test_chunk_cache_matches_full_and_is_not_mutated(submission):
    x=torch.arange(20.,dtype=torch.float64).reshape(1,5,4).sin()
    whole,full_cache=submission.gpt2_block(x,weights(),2)
    first,cache=submission.gpt2_block(x[:,:2],weights(),2)
    saved=tuple(t.clone() for t in cache)
    last,merged=submission.gpt2_block(x[:,2:],weights(),2,cache)
    torch.testing.assert_close(torch.cat((first,last),1),whole)
    for a,b,old in zip(merged,full_cache,saved):
        torch.testing.assert_close(a,b)
        torch.testing.assert_close(a[:,:,:2],old)
    for a,b in zip(cache,saved):
        torch.testing.assert_close(a,b)


def test_all_parameters_connected_and_input_preserved(submission):
    w={key:value.requires_grad_() for key,value in weights().items()}
    x=torch.arange(8.,dtype=torch.float64).reshape(1,2,4).sin().requires_grad_()
    before=x.detach().clone()
    y,_=submission.gpt2_block(x,w,2)
    y.square().sum().backward()
    for value in (x,*w.values()):
        assert value.grad is not None and torch.isfinite(value.grad).all()
    assert y.dtype == x.dtype and y.device == x.device
    torch.testing.assert_close(x,before)


def test_bad_heads_eps_and_cache_rejected(submission):
    x=torch.ones(1,2,4,dtype=torch.float64)
    for heads in (0,3):
        with pytest.raises(ValueError):
            submission.gpt2_block(x,weights(),heads)
    with pytest.raises(ValueError):
        submission.gpt2_block(x,weights(),2,eps=0.)
    with pytest.raises(ValueError):
        submission.gpt2_block(x,weights(),2,(torch.zeros(1,1,2,2),torch.zeros(1,1,2,2)))
