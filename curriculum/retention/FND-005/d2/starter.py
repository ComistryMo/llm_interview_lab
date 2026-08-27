"""D+2 equivalent rewrite for FND-005."""

from collections.abc import Iterable, Iterator


def iter_jsonl_objects(lines: Iterable[str]) -> Iterator[dict[str, object]]:
    raise NotImplementedError("implement iter_jsonl_objects")
