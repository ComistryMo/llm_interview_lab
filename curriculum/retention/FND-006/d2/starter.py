"""D+2 equivalent rewrite for FND-006."""

from collections.abc import Iterator


def iter_indexed_batches(items: list[object], batch_size: int) -> Iterator[tuple[int, list[object]]]:
    raise NotImplementedError("implement iter_indexed_batches")
