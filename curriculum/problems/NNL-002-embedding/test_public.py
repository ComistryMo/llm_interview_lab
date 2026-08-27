import pytest
torch=pytest.importorskip("torch")

def test_parameter_and_output_shapes(submission):
    layer=submission.ManualEmbedding(7,3); ids=torch.tensor([[1,2],[3,4]])
    assert tuple(layer.weight.shape)==(7,3) and layer(ids).shape==(2,2,3)

def test_lookup_values_match_weight_rows(submission):
    layer=submission.ManualEmbedding(4,2)
    with torch.no_grad(): layer.weight.copy_(torch.arange(8.).reshape(4,2))
    ids=torch.tensor([3,1,3])
    assert torch.equal(layer(ids),layer.weight.detach()[ids])

def test_padding_is_zero_and_has_zero_gradient(submission):
    layer=submission.ManualEmbedding(5,3,padding_idx=0); ids=torch.tensor([0,1,0,2])
    out=layer(ids); assert torch.equal(out[[0,2]],torch.zeros(2,3))
    out.sum().backward(); assert torch.equal(layer.weight.grad[0],torch.zeros(3))

def test_repeated_ids_accumulate_gradient(submission):
    layer=submission.ManualEmbedding(4,2); layer(torch.tensor([2,2])).sum().backward()
    assert torch.equal(layer.weight.grad[2],torch.tensor([2.,2.]))

@pytest.mark.parametrize("ids", [torch.tensor([1.]),torch.tensor([-1]),torch.tensor([4])])
def test_invalid_ids_raise(submission,ids):
    with pytest.raises(ValueError): submission.ManualEmbedding(4,2)(ids)

@pytest.mark.parametrize("args", [(0,2,None),(3,0,None),(True,2,None),(3,2,3)])
def test_invalid_constructor_raises(submission,args):
    with pytest.raises(ValueError): submission.ManualEmbedding(*args)

