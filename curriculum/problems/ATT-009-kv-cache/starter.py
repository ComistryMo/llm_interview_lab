import torch


class KVCache:
    """A fixed-capacity inference key/value cache."""

    def __init__(
        self,
        batch_size: int,
        max_length: int,
        num_kv_heads: int,
        head_dim: int,
        *,
        dtype: torch.dtype,
        device: torch.device | str,
    ) -> None:
        raise NotImplementedError

    @property
    def length(self) -> int:
        raise NotImplementedError

    def append(self, key: torch.Tensor, value: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        raise NotImplementedError

