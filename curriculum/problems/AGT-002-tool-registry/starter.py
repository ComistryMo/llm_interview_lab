from collections.abc import Callable


class ToolRegistry:
    """A deterministic in-process registry for trusted toy tools."""

    def __init__(self) -> None:
        raise NotImplementedError

    @property
    def names(self) -> tuple[str, ...]:
        raise NotImplementedError

    def register(self, schema: dict[str, object], handler: Callable[..., object]) -> None:
        raise NotImplementedError

    def call(self, name: str, arguments: dict[str, object]) -> object:
        raise NotImplementedError

