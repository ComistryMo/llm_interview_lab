import pytest
torch=pytest.importorskip("torch")

def test_expected_mask_and_shape(submission):
    lengths=torch.tensor([3,1,0])
    out=submission.sequence_mask(lengths)
    expected=torch.tensor([[1,1,1],[1,0,0],[0,0,0]],dtype=torch.bool)
    assert out.dtype==torch.bool and torch.equal(out,expected)

def test_explicit_longer_max_length(submission):
    out=submission.sequence_mask(torch.tensor([2]),4)
    assert torch.equal(out,torch.tensor([[1,1,0,0]],dtype=torch.bool))

def test_empty_batch_with_explicit_length(submission):
    out=submission.sequence_mask(torch.empty(0,dtype=torch.long),3)
    assert out.shape==(0,3) and out.dtype==torch.bool

@pytest.mark.parametrize("lengths,max_len", [(torch.tensor([[1]]),None),(torch.tensor([1.]),None),(torch.tensor([-1]),None),(torch.tensor([3]),2),(torch.tensor([1]),True)])
def test_invalid_contract_raises(submission,lengths,max_len):
    with pytest.raises(ValueError): submission.sequence_mask(lengths,max_len)

def test_device_and_input_are_preserved(submission):
    lengths=torch.tensor([1,2]); before=lengths.clone(); out=submission.sequence_mask(lengths)
    assert out.device==lengths.device and torch.equal(lengths,before)

