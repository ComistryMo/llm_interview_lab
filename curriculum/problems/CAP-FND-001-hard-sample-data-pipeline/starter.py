"""Starter for CAP-FND-001. It intentionally contains no implementation."""

from pathlib import Path


def run_hard_sample_pipeline(
    input_path: str | Path,
    output_path: str | Path,
    min_errors: int,
    batch_size: int,
) -> dict[str, object]:
    raise NotImplementedError("implement run_hard_sample_pipeline")
