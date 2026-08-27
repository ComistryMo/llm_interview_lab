from collections.abc import Iterable, Iterator
from pathlib import Path


class JsonlIO:
    """Streaming UTF-8 JSONL reader and writer."""

    @staticmethod
    def read(path: str | Path) -> Iterator[dict[str, object]]:
        raise NotImplementedError

    @staticmethod
    def write(path: str | Path, records: Iterable[dict[str, object]]) -> int:
        raise NotImplementedError

