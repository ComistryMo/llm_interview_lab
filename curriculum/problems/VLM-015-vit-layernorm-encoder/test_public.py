import pytest

torch = pytest.importorskip("torch")


def weights():
    generator=torch.Generator().manual_seed(150)
    shapes={"wqkv":(12,4),"bqkv":(12,),"wo":(4,4),"bo":(4,),"w1":(7,4),"b1":(7,),"w2":(4,7),"b2":(4,)}
    result={key:torch.randn(shape,generator=generator,dtype=torch.float64)*.3 for key,shape in shapes.items()}
    for i in (1,2):
        result[f"ln{i}_weight"]=torch.tensor([1.,.5,.8,1.2],dtype=torch.float64)
        result[f"ln{i}_bias"]=torch.tensor([.1,-.2,.3,-.1],dtype=torch.float64)*i
    return result


def test_identity_when_both_output_branches_zero(submission):
    w=weights()
    for key in ("wo","bo","w2","b2"):
        w[key].zero_()
    x=torch.arange(12.,dtype=torch.float64).reshape(1,3,4)
    torch.testing.assert_close(submission.vit_block(x,w,2),x)


def test_later_patch_can_change_first_token(submission):
    x=torch.arange(12.,dtype=torch.float64).reshape(1,3,4).sin()
    modified=x.clone()
    modified[:,2,0]+=10
    y=submission.vit_block(x,weights(),2)
    changed=submission.vit_block(modified,weights(),2)
    assert not torch.allclose(y[:,0],changed[:,0])


def test_masked_key_cannot_change_valid_query(submission):
    x=torch.arange(12.,dtype=torch.float64).reshape(1,3,4).sin()
    modified=x.clone()
    modified[:,2,0]+=10
    mask=torch.tensor([[True,True,False]])
    y=submission.vit_block(x,weights(),2,mask)
    changed=submission.vit_block(modified,weights(),2,mask)
    torch.testing.assert_close(y[:,:2],changed[:,:2])


def test_all_keys_masked_suppresses_attention_bias_with_finite_gradients(submission):
    w={key:value.requires_grad_() for key,value in weights().items()}
    with torch.no_grad():
        w["w2"].zero_()
        w["b2"].zero_()
    x=torch.arange(8.,dtype=torch.float64).reshape(1,2,4).sin().requires_grad_()
    y=submission.vit_block(x,w,2,torch.zeros(1,2,dtype=torch.bool))
    torch.testing.assert_close(y,x)
    y.sum().backward()
    for key in ("wqkv","bqkv","wo","bo"):
        assert w[key].grad is not None and torch.equal(w[key].grad,torch.zeros_like(w[key]))
    torch.testing.assert_close(x.grad,torch.ones_like(x))


def test_layernorm_shift_and_token_permutation(submission):
    x=torch.arange(12.,dtype=torch.float64).reshape(1,3,4).cos()
    y=submission.vit_block(x,weights(),2)
    torch.testing.assert_close(submission.vit_block(x+5.,weights(),2),y+5.)
    order=torch.tensor([2,0,1])
    torch.testing.assert_close(submission.vit_block(x[:,order],weights(),2),y[:,order])


def test_invalid_head_mask_and_epsilon(submission):
    x=torch.ones(1,2,4,dtype=torch.float64)
    with pytest.raises(ValueError):
        submission.vit_block(x,weights(),3)
    with pytest.raises(ValueError):
        submission.vit_block(x,weights(),2,torch.ones(1,2))
    with pytest.raises(ValueError):
        submission.vit_block(x,weights(),2,torch.ones(2,1,dtype=torch.bool))
    with pytest.raises(ValueError):
        submission.vit_block(x,weights(),2,eps=-1.)
