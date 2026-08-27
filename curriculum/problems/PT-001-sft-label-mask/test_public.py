import pytest
torch=pytest.importorskip("torch")

def test_prompt_and_padding_are_ignored(submission):
    ids=torch.tensor([[10,11,20,21,0],[12,30,31,0,0]]); mask=torch.tensor([[0,0,1,1,1],[0,1,1,1,1]],dtype=torch.bool)
    expected=torch.tensor([[-100,-100,20,21,-100],[-100,30,31,-100,-100]])
    assert torch.equal(submission.build_sft_labels(ids,mask,0),expected)

def test_custom_ignore_index(submission):
    ids=torch.tensor([[1,2]]); mask=torch.tensor([[0,1]],dtype=torch.bool)
    assert torch.equal(submission.build_sft_labels(ids,mask,0,-1),torch.tensor([[-1,2]]))

def test_output_is_clone_and_inputs_unchanged(submission):
    ids=torch.tensor([[1,2]]); mask=torch.tensor([[0,1]],dtype=torch.bool); before=ids.clone()
    labels=submission.build_sft_labels(ids,mask,0); labels[0,1]=9
    assert torch.equal(ids,before)

def test_every_row_requires_supervised_token(submission):
    with pytest.raises(ValueError): submission.build_sft_labels(torch.tensor([[1,0]]),torch.tensor([[0,1]],dtype=torch.bool),0)

@pytest.mark.parametrize("ids,mask", [(torch.ones(2,3),torch.ones(2,3,dtype=torch.bool)),(torch.ones(2,3,dtype=torch.long),torch.ones(2,2,dtype=torch.bool)),(torch.ones(2,3,dtype=torch.long),torch.ones(2,3))])
def test_invalid_shape_or_dtype_raises(submission,ids,mask):
    with pytest.raises(ValueError): submission.build_sft_labels(ids,mask,0)

def test_bool_special_token_ids_are_rejected(submission):
    ids=torch.tensor([[1]],dtype=torch.long); mask=torch.tensor([[1]],dtype=torch.bool)
    with pytest.raises(ValueError): submission.build_sft_labels(ids,mask,True)

