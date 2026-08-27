import pytest
torch=pytest.importorskip("torch")

def test_first_step_initializes_velocity(submission):
    p=torch.tensor([1.],requires_grad=True); p.grad=torch.tensor([2.])
    state=submission.momentum_step([p],[None],.1,.9)
    assert torch.allclose(p,torch.tensor([.8])) and torch.equal(state[0],torch.tensor([2.]))

def test_second_step_uses_previous_velocity(submission):
    p=torch.tensor([1.],requires_grad=True); p.grad=torch.tensor([2.]); state=submission.momentum_step([p],[None],.1,.5)
    p.grad=torch.tensor([1.]); state=submission.momentum_step([p],state,.1,.5)
    assert torch.allclose(state[0],torch.tensor([2.])) and torch.allclose(p,torch.tensor([.6]))

def test_none_gradient_preserves_state_as_detached_copy(submission):
    p=torch.tensor([1.],requires_grad=True); v=torch.tensor([3.],requires_grad=True)
    state=submission.momentum_step([p],[v],.1,.9)
    assert p.item()==1 and torch.equal(state[0],v) and not state[0].requires_grad and state[0] is not v

def test_multiple_parameters_remain_aligned(submission):
    a=torch.tensor([1.],requires_grad=True); b=torch.tensor([2.],requires_grad=True); a.grad=torch.tensor([1.]); b.grad=torch.tensor([2.])
    state=submission.momentum_step([a,b],[None,None],.1,0.)
    assert len(state)==2 and torch.allclose(a,torch.tensor([.9])) and torch.allclose(b,torch.tensor([1.8]))

@pytest.mark.parametrize("params,state,lr,mu", [([],[],.1,.9),([torch.tensor([1.])],[],.1,.9),([torch.tensor([1.])],[None],0,.9),([torch.tensor([1.])],[None],.1,1.)])
def test_invalid_contract_raises(submission,params,state,lr,mu):
    with pytest.raises(ValueError): submission.momentum_step(params,state,lr,mu)

