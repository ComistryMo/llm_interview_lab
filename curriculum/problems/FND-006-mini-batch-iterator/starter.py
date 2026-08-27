from collections.abc import Iterator


def iter_minibatches(
    items: list[object],
    batch_size: int,
    drop_last: bool = False,
) -> Iterator[list[object]]:
    """Yield deterministic mini-batches as new lists."""
    raise NotImplementedError

