import pytest
torch=pytest.importorskip("torch")

def test_first_step_decouples_weight_decay(submission):
    p=torch.tensor([2.],dtype=torch.float64,requires_grad=True); p.grad=torch.tensor([1.],dtype=torch.float64)
    state=submission.adamw_step([p],[None],.1,.9,.999,1e-8,.2)[0]
    assert torch.allclose(p,torch.tensor([1.86],dtype=torch.float64),atol=1e-8) and state["step"]==1

def test_zero_decay_matches_adam_formula(submission):
    p=torch.tensor([1.],dtype=torch.float64,requires_grad=True); p.grad=torch.tensor([2.],dtype=torch.float64)
    submission.adamw_step([p],[None],.01,.9,.999,1e-8,0.)
    assert torch.allclose(p,torch.tensor([.99],dtype=torch.float64),atol=1e-8)

def test_none_gradient_skips_decay_and_step(submission):
    p=torch.tensor([2.],requires_grad=True); old={"m":torch.zeros(1),"v":torch.zeros(1),"step":4}
    state=submission.adamw_step([p],[old],.1,weight_decay=.5)[0]
    assert p.item()==2 and state["step"]==4

def test_two_parameters_have_independent_state(submission):
    a=torch.tensor([1.],requires_grad=True); b=torch.tensor([3.],requires_grad=True); a.grad=torch.tensor([1.]); b.grad=torch.tensor([-1.])
    states=submission.adamw_step([a,b],[None,None],.01,weight_decay=.1)
    assert len(states)==2 and states[0] is not states[1] and a.item()<1 and b.item()>2.9

@pytest.mark.parametrize("decay", [-1.,float("inf"),True])
def test_invalid_weight_decay_raises_without_update(submission,decay):
    p=torch.tensor([1.],requires_grad=True); p.grad=torch.tensor([1.])
    with pytest.raises(ValueError): submission.adamw_step([p],[None],.1,weight_decay=decay)
    assert p.item()==1

