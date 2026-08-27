from collections.abc import Callable


def run_tool_calling_loop(
    model: Callable[[list[dict[str, object]]], dict[str, object]],
    registry: object,
    messages: list[dict[str, object]],
    max_steps: int = 8,
) -> list[dict[str, object]]:
    """Run a deterministic local tool-calling loop and return its trajectory."""
    raise NotImplementedError

