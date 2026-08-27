import pytest
torch=pytest.importorskip("torch")

def test_gathers_expected_values(submission):
    v=torch.tensor([[10.,20.,30.],[40.,50.,60.]])
    i=torch.tensor([[2,0],[1,1]])
    assert torch.equal(submission.gather_last_dim(v,i),torch.tensor([[30.,10.],[50.,50.]]))

def test_batched_rank_three_shape(submission):
    v=torch.arange(24.).reshape(2,3,4); i=torch.tensor([[[0],[1],[2]],[[3],[2],[1]]])
    out=submission.gather_last_dim(v,i)
    assert out.shape==i.shape and torch.equal(out,torch.gather(v,-1,i))

def test_gradient_accumulates_duplicate_indices(submission):
    v=torch.arange(3.,requires_grad=True); v2=v.view(1,3); i=torch.tensor([[1,1]])
    submission.gather_last_dim(v2,i).sum().backward()
    assert torch.equal(v.grad,torch.tensor([0.,2.,0.]))

@pytest.mark.parametrize("index", [torch.tensor([[0.]]), torch.tensor([0]), torch.tensor([[3]]), torch.tensor([[-1]])])
def test_invalid_indices_raise(submission,index):
    with pytest.raises(ValueError):
        submission.gather_last_dim(torch.zeros(1,3),index)

def test_input_is_not_mutated(submission):
    v=torch.randn(2,3); i=torch.tensor([[0],[2]]); before=v.clone()
    submission.gather_last_dim(v,i)
    assert torch.equal(v,before)

