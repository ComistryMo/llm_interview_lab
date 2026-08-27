import pytest
torch=pytest.importorskip("torch")

def test_forward_values(submission):
    x=torch.tensor([1.,-2.],requires_grad=True)
    out,snapshot=submission.autograd_probe(x)
    assert torch.equal(out,x.square()+x) and torch.equal(snapshot,x)

def test_detached_branch_does_not_contribute_gradient(submission):
    x=torch.tensor([1.,-2.],requires_grad=True); out,_=submission.autograd_probe(x)
    out.sum().backward()
    assert torch.equal(x.grad,2*x.detach())

def test_snapshot_is_detached_and_not_aliased(submission):
    x=torch.tensor([1.,2.],requires_grad=True); _,snapshot=submission.autograd_probe(x)
    assert not snapshot.requires_grad and snapshot.grad_fn is None
    snapshot.add_(1)
    assert torch.equal(x,torch.tensor([1.,2.]))

def test_dtype_device_and_shape(submission):
    x=torch.randn(2,3,dtype=torch.float64,requires_grad=True); out,snap=submission.autograd_probe(x)
    assert out.shape==x.shape and out.dtype==snap.dtype==x.dtype and out.device==snap.device==x.device

@pytest.mark.parametrize("x", [torch.tensor([1]), torch.tensor([1.]), torch.tensor([True])])
def test_invalid_input_raises(submission,x):
    with pytest.raises(ValueError): submission.autograd_probe(x)

