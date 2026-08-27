import pytest
torch=pytest.importorskip("torch")

def test_single_parameter_update(submission):
    p=torch.tensor([1.,-2.],requires_grad=True); p.grad=torch.tensor([.5,-1.])
    assert submission.sgd_step([p],.1) is None
    assert torch.allclose(p,torch.tensor([.95,-1.9]))

def test_none_gradient_is_skipped(submission):
    p=torch.tensor([1.],requires_grad=True); submission.sgd_step([p],.2)
    assert p.item()==1

def test_update_is_not_tracked_and_gradient_unchanged(submission):
    p=torch.tensor([1.],requires_grad=True); p.grad=torch.tensor([2.]); g=p.grad.clone()
    submission.sgd_step([p],.1)
    assert p.is_leaf and p.grad_fn is None and torch.equal(p.grad,g)

def test_multiple_parameters(submission):
    a=torch.tensor([1.],requires_grad=True); b=torch.tensor([2.],requires_grad=True); a.grad=torch.tensor([1.]); b.grad=torch.tensor([-2.])
    submission.sgd_step([a,b],.5)
    assert a.item()==.5 and b.item()==3

@pytest.mark.parametrize("params,lr", [([],0.1),([torch.tensor([1])],0.1),([torch.tensor([1.],requires_grad=True)],0),([torch.tensor([1.],requires_grad=True)],True)])
def test_invalid_contract_raises(submission,params,lr):
    with pytest.raises(ValueError): submission.sgd_step(params,lr)

def test_invalid_later_gradient_does_not_partially_update(submission):
    a=torch.tensor([1.],requires_grad=True); b=torch.tensor([2.],requires_grad=True); a.grad=torch.tensor([1.]); b.grad=torch.tensor([1.,2.])
    with pytest.raises(ValueError): submission.sgd_step([a,b],.1)
    assert a.item()==1

