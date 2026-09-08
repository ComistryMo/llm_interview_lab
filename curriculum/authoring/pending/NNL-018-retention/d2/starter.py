import numpy as np


def accumulate_linear_vjp(chunks: list[tuple[np.ndarray, np.ndarray]],
                          weight: np.ndarray) -> tuple[list[np.ndarray], np.ndarray, np.ndarray]:
    """Return per-chunk input gradients and summed shared parameter gradients."""
    raise NotImplementedError("Implement the reviewed contract independently")
