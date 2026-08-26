import pytest

torch = pytest.importorskip("torch")

from src.stage00.classification_head import LastValidTokenClassificationHead


pytestmark = [
    pytest.mark.training,
    pytest.mark.locked,
    pytest.mark.requires_torch,
]


def test_output_shape():
    module = LastValidTokenClassificationHead(hidden_size=4, num_classes=3)
    hidden_states = torch.randn(2, 5, 4)
    attention_mask = torch.tensor(
        [
            [1, 1, 1, 0, 0],
            [1, 1, 1, 1, 1],
        ]
    )
    logits = module(hidden_states, attention_mask)
    assert logits.shape == (2, 3)


def test_uses_last_valid_token():
    module = LastValidTokenClassificationHead(hidden_size=2, num_classes=2)

    with torch.no_grad():
        module.classifier.weight.copy_(torch.eye(2))
        module.classifier.bias.zero_()

    hidden_states = torch.tensor(
        [
            [[1.0, 0.0], [2.0, 0.0], [99.0, 99.0]],
            [[0.0, 1.0], [0.0, 2.0], [0.0, 3.0]],
        ]
    )
    attention_mask = torch.tensor(
        [
            [1, 1, 0],
            [1, 1, 1],
        ]
    )

    logits = module(hidden_states, attention_mask)
    expected = torch.tensor(
        [
            [2.0, 0.0],
            [0.0, 3.0],
        ]
    )
    assert torch.allclose(logits, expected)


def test_gradient_flows_to_selected_hidden_state():
    module = LastValidTokenClassificationHead(hidden_size=3, num_classes=2)
    hidden_states = torch.randn(2, 4, 3, requires_grad=True)
    attention_mask = torch.tensor(
        [
            [1, 1, 0, 0],
            [1, 1, 1, 0],
        ]
    )

    loss = module(hidden_states, attention_mask).sum()
    loss.backward()

    assert hidden_states.grad is not None
    assert hidden_states.grad.shape == hidden_states.shape


def test_rejects_all_padding_sequence():
    module = LastValidTokenClassificationHead(hidden_size=3, num_classes=2)
    hidden_states = torch.randn(1, 3, 3)
    attention_mask = torch.tensor([[0, 0, 0]])

    with pytest.raises(ValueError):
        module(hidden_states, attention_mask)
