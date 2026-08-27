import pytest
torch=pytest.importorskip("torch")
F=torch.nn.functional

def test_matches_reference_values(submission):
    pc=torch.tensor([-1.,-2.]); pr=torch.tensor([-3.,-1.]); rc=torch.tensor([-2.,-2.]); rr=torch.tensor([-2.5,-1.5])
    loss,acc=submission.dpo_loss(pc,pr,rc,rr,.2); logits=.2*((pc-pr)-(rc-rr))
    assert torch.allclose(loss,-F.logsigmoid(logits)) and torch.equal(acc,(logits>0).float().mean())

def test_extreme_margins_are_finite(submission):
    x=torch.tensor([10000.,-10000.]); z=torch.zeros(2)
    loss,_=submission.dpo_loss(x,z,z,z,1.)
    assert torch.isfinite(loss).all()

def test_policy_gradients_match_reference(submission):
    pc=torch.randn(3,dtype=torch.float64,requires_grad=True); pr=torch.randn(3,dtype=torch.float64,requires_grad=True); a=pc.detach().clone().requires_grad_(); b=pr.detach().clone().requires_grad_(); r=torch.zeros(3,dtype=torch.float64)
    submission.dpo_loss(pc,pr,r,r,.3)[0].mean().backward(); (-F.logsigmoid(.3*(a-b))).mean().backward()
    assert torch.allclose(pc.grad,a.grad) and torch.allclose(pr.grad,b.grad)

def test_accuracy_is_scalar_without_gradient(submission):
    x=torch.tensor([1.,-1.],requires_grad=True); z=torch.zeros(2)
    _,acc=submission.dpo_loss(x,z,z,z,1.)
    assert acc.shape==() and not acc.requires_grad

@pytest.mark.parametrize("shape,beta", [((2,1),.1),((0,),.1),((2,),0),((2,),True)])
def test_invalid_contract_raises(submission,shape,beta):
    x=torch.zeros(shape)
    with pytest.raises(ValueError): submission.dpo_loss(x,x,x,x,beta)

def test_mismatched_inputs_raise(submission):
    with pytest.raises(ValueError): submission.dpo_loss(torch.zeros(2),torch.zeros(3),torch.zeros(2),torch.zeros(2),.1)

