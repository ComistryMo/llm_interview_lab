"""D+7 integration variant for FND-005."""

from collections.abc import Callable
from pathlib import Path


def transform_jsonl(
    source: str | Path,
    destination: str | Path,
    transform: Callable[[dict[str, object]], dict[str, object]],
) -> int:
    raise NotImplementedError("implement transform_jsonl")
