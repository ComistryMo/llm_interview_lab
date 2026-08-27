import math
import pytest
torch=pytest.importorskip("torch")

def test_parameter_shapes_and_bias_flag(submission):
    layer=submission.ManualLinear(3,4,True)
    assert tuple(layer.weight.shape)==(4,3) and tuple(layer.bias.shape)==(4,)
    assert submission.ManualLinear(3,4,False).bias is None

def test_forward_matches_explicit_formula(submission):
    layer=submission.ManualLinear(2,3); x=torch.randn(4,5,2)
    assert torch.allclose(layer(x),x@layer.weight.T+layer.bias)

def test_initialization_bounds(submission):
    layer=submission.ManualLinear(5,20); bound=1/math.sqrt(5)
    assert torch.all(layer.weight.abs()<=bound) and torch.all(layer.bias.abs()<=bound)

def test_gradients_reach_input_and_parameters(submission):
    layer=submission.ManualLinear(2,3).double(); x=torch.randn(4,2,dtype=torch.float64,requires_grad=True)
    layer(x).sum().backward()
    assert x.grad is not None and layer.weight.grad is not None and layer.bias.grad is not None

@pytest.mark.parametrize("args", [(0,2,True),(2,0,True),(True,2,True),(2,3,1)])
def test_invalid_constructor_raises(submission,args):
    with pytest.raises(ValueError): submission.ManualLinear(*args)

def test_invalid_input_last_dimension_raises(submission):
    with pytest.raises(ValueError): submission.ManualLinear(2,3)(torch.zeros(4,4))

