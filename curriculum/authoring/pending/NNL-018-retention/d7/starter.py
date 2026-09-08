import numpy as np


def shared_embedding_projection_vjp(token_ids: np.ndarray, hidden: np.ndarray,
                                    weight: np.ndarray, grad_embeddings: np.ndarray,
                                    grad_logits: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return hidden and shared-weight gradients without autograd."""
    raise NotImplementedError("Implement the reviewed contract independently")
