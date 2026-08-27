from collections.abc import Iterable, Iterator
from pathlib import Path


class TrajectoryJsonl:
    """Streaming, physical-order trajectory storage."""

    @staticmethod
    def write(path: str | Path, events: Iterable[dict[str, object]]) -> int:
        raise NotImplementedError

    @staticmethod
    def read(path: str | Path) -> Iterator[dict[str, object]]:
        raise NotImplementedError

