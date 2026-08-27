def mine_hard_samples(
    samples: list[dict[str, object]],
    min_errors: int = 1,
) -> list[dict[str, object]]:
    """Return defensive copies of samples meeting the error threshold."""
    raise NotImplementedError

