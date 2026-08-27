import torch


def grouped_adamw_step(
    groups: list[dict[str, object]],
    states: dict[str, dict[str, object]],
) -> dict[str, dict[str, object]]:
    """Update named parameters in groups and return fresh per-name state."""
    raise NotImplementedError
