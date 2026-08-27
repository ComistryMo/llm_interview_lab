import pytest
torch=pytest.importorskip("torch")

def test_right_padding(submission):
    h=torch.arange(24.).reshape(2,3,4); m=torch.tensor([[1,1,0],[1,1,1]],dtype=torch.bool)
    assert torch.equal(submission.last_valid_token(h,m),torch.stack([h[0,1],h[1,2]]))

def test_left_and_gapped_masks_use_greatest_valid_index(submission):
    h=torch.arange(15.).reshape(1,5,3); m=torch.tensor([[0,1,0,1,0]],dtype=torch.bool)
    assert torch.equal(submission.last_valid_token(h,m),h[:,3])

def test_gradient_reaches_only_selected_rows(submission):
    h=torch.randn(2,3,2,requires_grad=True); m=torch.tensor([[1,0,0],[1,1,0]],dtype=torch.bool)
    submission.last_valid_token(h,m).sum().backward()
    expected=torch.zeros_like(h); expected[0,0]=1; expected[1,1]=1
    assert torch.equal(h.grad,expected)

@pytest.mark.parametrize("h,m", [(torch.zeros(2,3),torch.ones(2,3,dtype=torch.bool)),(torch.zeros(2,3,4),torch.ones(2,2,dtype=torch.bool)),(torch.zeros(1,2,3),torch.zeros(1,2,dtype=torch.bool)),(torch.zeros(1,2,3),torch.ones(1,2))])
def test_invalid_contract_raises(submission,h,m):
    with pytest.raises(ValueError): submission.last_valid_token(h,m)

def test_input_is_unchanged(submission):
    h=torch.randn(1,2,3); m=torch.tensor([[1,0]],dtype=torch.bool); before=h.clone()
    submission.last_valid_token(h,m)
    assert torch.equal(h,before)

