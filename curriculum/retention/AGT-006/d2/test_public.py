import copy
import pytest


class Registry:
    def call(self, name, arguments):
        if name != "add": raise ValueError("unknown tool")
        if set(arguments) != {"a", "b"}: raise ValueError("invalid arguments")
        return arguments["a"] + arguments["b"]


def test_success_observation(submission):
    assert submission.execute_tool_action({"type": "tool", "name": "add", "arguments": {"a": 2, "b": 3}}, Registry()) == {"type": "observation", "name": "add", "result": 5}


@pytest.mark.parametrize("action", [{}, {"type": "final"}, {"type": "tool", "name": 1, "arguments": {}}, {"type": "tool", "name": "add", "arguments": []}])
def test_invalid_action_is_an_error_observation(submission, action):
    result = submission.execute_tool_action(action, Registry())
    assert result["type"] == "observation" and isinstance(result["error"], str)


def test_registry_validation_error_is_observed(submission):
    result = submission.execute_tool_action({"type": "tool", "name": "missing", "arguments": {}}, Registry())
    assert "error" in result and result["name"] == "missing"


def test_handler_exception_is_observed(submission):
    class Broken:
        def call(self, name, arguments): raise RuntimeError("boom")
    result = submission.execute_tool_action({"type": "tool", "name": "x", "arguments": {}}, Broken())
    assert result["error"] == "boom"


def test_action_is_not_mutated(submission):
    action = {"type": "tool", "name": "add", "arguments": {"a": 1, "b": 2}}; before = copy.deepcopy(action)
    submission.execute_tool_action(action, Registry())
    assert action == before
