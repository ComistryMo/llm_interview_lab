import pytest
torch=pytest.importorskip("torch")

def test_first_step_matches_closed_form(submission):
    p=torch.tensor([1.,-1.],dtype=torch.float64,requires_grad=True); p.grad=torch.tensor([2.,-4.],dtype=torch.float64)
    state=submission.adam_step([p],[None],.1,.9,.999,1e-8)[0]
    expected=torch.tensor([.9,-.9],dtype=torch.float64)
    assert torch.allclose(p,expected,atol=1e-8) and state["step"]==1
    assert torch.equal(state["m"],torch.tensor([.2,-.4],dtype=torch.float64))

def test_two_steps_match_manual_reference(submission):
    p=torch.tensor([1.],dtype=torch.float64,requires_grad=True); state=None
    for grad in (2.,1.):
        p.grad=torch.tensor([grad],dtype=torch.float64)
        state=submission.adam_step([p],[state],.01,.5,.9,1e-8)[0]
    m=.5*1+.5*1; v=.9*.4+.1*1; expected=1-.01-.01*(m/(1-.5**2))/(v/(1-.9**2))**.5
    assert abs(p.item()-expected)<1e-8 and state["step"]==2

def test_none_gradient_preserves_step_and_parameter(submission):
    p=torch.tensor([1.],requires_grad=True); old={"m":torch.zeros(1),"v":torch.ones(1),"step":3}
    state=submission.adam_step([p],[old],.1)[0]
    assert p.item()==1 and state["step"]==3 and state is not old

def test_state_is_detached_and_not_aliased(submission):
    p=torch.tensor([1.],requires_grad=True); p.grad=torch.tensor([1.]); state=submission.adam_step([p],[None],.1)[0]
    assert not state["m"].requires_grad and not state["v"].requires_grad
    state["m"].add_(10); assert p.item()!=10

@pytest.mark.parametrize("lr,b1,b2,eps", [(0,.9,.999,1e-8),(.1,1.,.999,1e-8),(.1,.9,1.,1e-8),(.1,.9,.999,0)])
def test_invalid_hyperparameters_raise(submission,lr,b1,b2,eps):
    p=torch.tensor([1.],requires_grad=True)
    with pytest.raises(ValueError): submission.adam_step([p],[None],lr,b1,b2,eps)

