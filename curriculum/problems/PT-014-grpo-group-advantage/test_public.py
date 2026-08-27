import pytest
torch=pytest.importorskip("torch")

def test_groupwise_mean_and_population_std(submission):
    r=torch.tensor([[1.,2.,3.],[2.,4.,8.]],dtype=torch.float64); out=submission.grpo_group_advantage(r)
    ref=(r-r.mean(1,keepdim=True))/r.std(1,unbiased=False,keepdim=True)
    assert torch.allclose(out,ref,atol=1e-12)

def test_each_nonconstant_group_is_centered(submission):
    out=submission.grpo_group_advantage(torch.tensor([[1.,3.],[2.,5.]]))
    assert torch.allclose(out.mean(1),torch.zeros(2),atol=1e-6)

def test_zero_variance_group_is_exact_zero(submission):
    out=submission.grpo_group_advantage(torch.tensor([[2.,2.,2.],[1.,2.,3.]]))
    assert torch.equal(out[0],torch.zeros(3)) and torch.isfinite(out).all()

def test_result_is_detached_and_input_unchanged(submission):
    r=torch.tensor([[1.,2.]],requires_grad=True); before=r.detach().clone(); out=submission.grpo_group_advantage(r)
    assert not out.requires_grad and torch.equal(r.detach(),before)

@pytest.mark.parametrize("r,eps", [(torch.ones(3),1e-8),(torch.ones(2,1),1e-8),(torch.empty(0,2),1e-8),(torch.tensor([[1.,float("nan")]]),1e-8),(torch.ones(2,2),0)])
def test_invalid_contract_raises(submission,r,eps):
    with pytest.raises(ValueError): submission.grpo_group_advantage(r,eps)

