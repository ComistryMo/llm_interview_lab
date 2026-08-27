import pytest
torch=pytest.importorskip("torch")

def reference(lp,old,adv,mask,eps):
    ratio=(lp-old).exp(); a=adv.unsqueeze(-1); surrogate=torch.minimum(ratio*a,ratio.clamp(1-eps,1+eps)*a)
    return -surrogate.masked_select(mask).mean()

def test_matches_reference(submission):
    lp=torch.randn(2,3,4,dtype=torch.float64); old=torch.randn(2,3,4,dtype=torch.float64); adv=torch.randn(2,3,dtype=torch.float64); mask=torch.rand(2,3,4)>.3
    assert torch.allclose(submission.grpo_clipped_loss(lp,old,adv,mask,.2),reference(lp,old,adv,mask,.2),atol=1e-12)

def test_positive_and_negative_advantages_clip_correct_side(submission):
    lp=torch.log(torch.tensor([[[2.0],[2.0]]])); old=torch.zeros_like(lp); adv=torch.tensor([[1.,-1.]]); mask=torch.ones_like(lp,dtype=torch.bool)
    assert torch.allclose(submission.grpo_clipped_loss(lp,old,adv,mask,.2),reference(lp,old,adv,mask,.2))

def test_masked_tokens_have_zero_gradient(submission):
    lp=torch.zeros(1,1,2,requires_grad=True); old=torch.zeros_like(lp); adv=torch.ones(1,1); mask=torch.tensor([[[1,0]]],dtype=torch.bool)
    submission.grpo_clipped_loss(lp,old,adv,mask,.2).backward()
    assert lp.grad[0,0,1]==0 and lp.grad[0,0,0]!=0

def test_old_logprobs_and_advantages_need_no_gradient(submission):
    lp=torch.zeros(1,1,1,requires_grad=True); old=torch.zeros(1,1,1); adv=torch.ones(1,1); mask=torch.ones(1,1,1,dtype=torch.bool)
    loss=submission.grpo_clipped_loss(lp,old,adv,mask,.2); loss.backward()
    assert lp.grad is not None and old.grad is None and adv.grad is None

@pytest.mark.parametrize("shape,eps", [((2,3),.2),((1,1,1),0),((1,1,1),1.),((0,1,1),.2)])
def test_invalid_shape_or_clip_raises(submission,shape,eps):
    lp=torch.zeros(shape); old=torch.zeros_like(lp); adv=torch.zeros(shape[:2]); mask=torch.ones_like(lp,dtype=torch.bool)
    with pytest.raises(ValueError): submission.grpo_clipped_loss(lp,old,adv,mask,eps)

def test_empty_mask_raises(submission):
    lp=torch.zeros(1,1,2)
    with pytest.raises(ValueError): submission.grpo_clipped_loss(lp,lp,torch.zeros(1,1),torch.zeros_like(lp,dtype=torch.bool),.2)

