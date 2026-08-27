from __future__ import annotations

import pytest


pytestmark = [pytest.mark.infrastructure, pytest.mark.requires_torch]
torch = pytest.importorskip("torch")


def test_cpu_tensor_reference_supports_alpha_validation_axes() -> None:
    values = torch.tensor([[10000.0, 9999.0, -10000.0]], dtype=torch.float64, requires_grad=True)
    non_contiguous = values.expand(3, -1).t()
    assert non_contiguous.device.type == "cpu" and not non_contiguous.is_contiguous()

    probabilities = torch.softmax(values, dim=-1)
    probabilities[0, 1].backward()

    assert probabilities.shape == values.shape
    assert probabilities.dtype == values.dtype
    assert torch.isfinite(probabilities).all()
    assert values.grad is not None and torch.isfinite(values.grad).all()


def test_cpu_optimizer_state_dict_resume_matches_uninterrupted_run() -> None:
    def run(steps: int, state=None):
        parameter = torch.nn.Parameter(torch.tensor([1.0]))
        optimizer = torch.optim.AdamW([parameter], lr=0.01, weight_decay=0.1)
        if state is not None:
            parameter.data.copy_(state[0])
            optimizer.load_state_dict(state[1])
        for _ in range(steps):
            parameter.grad = torch.tensor([0.25])
            optimizer.step()
        return parameter.detach().clone(), optimizer.state_dict()

    uninterrupted, _ = run(3)
    first, state = run(1)
    resumed, _ = run(2, (first, state))
    assert torch.allclose(resumed, uninterrupted)
