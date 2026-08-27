import pytest
torch=pytest.importorskip("torch")
F=torch.nn.functional

@pytest.mark.parametrize("reduction",["none","sum","mean"])
def test_matches_framework(submission,reduction):
    x=torch.randn(2,3,dtype=torch.float64); y=torch.rand(2,3,dtype=torch.float64)
    assert torch.allclose(submission.bce_with_logits(x,y,reduction),F.binary_cross_entropy_with_logits(x,y,reduction=reduction),atol=1e-12)

def test_extreme_logits_are_finite(submission):
    x=torch.tensor([-10000.,10000.]); y=torch.tensor([0.,1.])
    out=submission.bce_with_logits(x,y,"none")
    assert torch.isfinite(out).all() and torch.all(out<1e-4)

def test_gradient_matches_reference(submission):
    x=torch.randn(4,dtype=torch.float64,requires_grad=True); y=torch.rand(4,dtype=torch.float64); z=x.detach().clone().requires_grad_()
    submission.bce_with_logits(x,y).backward(); F.binary_cross_entropy_with_logits(z,y).backward()
    assert torch.allclose(x.grad,z.grad,atol=1e-10)

@pytest.mark.parametrize("x,y,r", [(torch.ones(2),torch.ones(3),"mean"),(torch.ones(2),torch.tensor([0.,2.]),"mean"),(torch.ones(0),torch.ones(0),"mean"),(torch.ones(2),torch.ones(2),"bad")])
def test_invalid_contract_raises(submission,x,y,r):
    with pytest.raises(ValueError): submission.bce_with_logits(x,y,r)

def test_inputs_not_mutated(submission):
    x=torch.randn(2); y=torch.rand(2); xb=x.clone(); yb=y.clone(); submission.bce_with_logits(x,y)
    assert torch.equal(x,xb) and torch.equal(y,yb)

