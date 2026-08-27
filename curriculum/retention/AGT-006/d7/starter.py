def replay_tool_actions(
    actions: list[dict[str, object]],
    registry: object,
    max_steps: int = 8,
) -> list[dict[str, object]]:
    """Replay actions into a complete bounded trajectory ending in final."""
    raise NotImplementedError
