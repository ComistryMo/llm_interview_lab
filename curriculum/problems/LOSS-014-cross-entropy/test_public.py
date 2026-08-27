import pytest
torch=pytest.importorskip("torch")
F=torch.nn.functional

@pytest.mark.parametrize("reduction",["none","sum","mean"])
def test_matches_framework_without_ignored_rows(submission,reduction):
    x=torch.randn(4,5,dtype=torch.float64); y=torch.tensor([0,4,2,1])
    assert torch.allclose(submission.cross_entropy(x,y,reduction),F.cross_entropy(x,y,reduction=reduction),atol=1e-10)

def test_ignore_index_matches_reference(submission):
    x=torch.randn(3,4,dtype=torch.float64); y=torch.tensor([1,-100,3])
    assert torch.allclose(submission.cross_entropy(x,y,"mean",-100),F.cross_entropy(x,y,ignore_index=-100),atol=1e-10)

def test_extreme_logits_remain_finite(submission):
    x=torch.tensor([[10000.,9999.,-10000.]]); y=torch.tensor([0])
    assert torch.isfinite(submission.cross_entropy(x,y))

def test_gradient_matches_framework(submission):
    x=torch.randn(3,4,dtype=torch.float64,requires_grad=True); y=torch.tensor([0,2,1]); z=x.detach().clone().requires_grad_()
    submission.cross_entropy(x,y).backward(); F.cross_entropy(z,y).backward()
    assert torch.allclose(x.grad,z.grad,atol=1e-10)

def test_all_ignored_mean_is_differentiable_zero(submission):
    x=torch.randn(2,3,requires_grad=True); y=torch.tensor([-1,-1]); loss=submission.cross_entropy(x,y,"mean",-1)
    assert loss.shape==() and loss.item()==0; loss.backward(); assert torch.equal(x.grad,torch.zeros_like(x))

@pytest.mark.parametrize("x,y,r", [(torch.ones(3),torch.tensor([0]),"mean"),(torch.ones(2,1),torch.tensor([0,0]),"mean"),(torch.ones(2,3),torch.tensor([0]),"mean"),(torch.ones(2,3),torch.tensor([0,3]),"mean"),(torch.ones(2,3),torch.tensor([0,1]),"bad")])
def test_invalid_contract_raises(submission,x,y,r):
    with pytest.raises(ValueError): submission.cross_entropy(x,y,r)

