import torch


def autograd_probe(x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Return a mixed-gradient output and a detached snapshot."""
    raise NotImplementedError

