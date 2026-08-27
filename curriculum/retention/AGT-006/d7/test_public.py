import copy
import pytest


class Registry:
    def call(self, name, arguments):
        if name == "timeout": raise TimeoutError("deadline")
        if name != "echo": raise ValueError("unknown")
        if set(arguments) != {"value"}: raise ValueError("arguments")
        return arguments["value"]


def test_successful_replay_has_complete_trajectory(submission):
    actions = [{"type": "tool", "name": "echo", "arguments": {"value": "x"}}, {"type": "final", "content": "done"}]
    trajectory = submission.replay_tool_actions(actions, Registry())
    assert trajectory == [actions[0], {"type": "observation", "name": "echo", "result": "x"}, actions[1]]


@pytest.mark.parametrize("action", [{"type": "tool", "name": "missing", "arguments": {}}, {"type": "tool", "name": "echo", "arguments": {}}, {"bad": 1}, {"type": "tool", "name": "timeout", "arguments": {}}])
def test_failures_are_recorded_before_recovery(submission, action):
    trajectory = submission.replay_tool_actions([action, {"type": "final", "content": "fallback"}], Registry())
    assert trajectory[0] == action and trajectory[1]["type"] == "observation" and "error" in trajectory[1]
    assert trajectory[-1]["content"] == "fallback"


def test_repeated_action_is_explicit(submission):
    action = {"type": "tool", "name": "echo", "arguments": {"value": 1}}
    trajectory = submission.replay_tool_actions([action, action, {"type": "final", "content": "ok"}], Registry())
    assert trajectory[3]["error"] == "repeated action"


def test_max_steps_and_missing_final_raise(submission):
    with pytest.raises(RuntimeError):
        submission.replay_tool_actions([{"bad": 1}, {"bad": 2}], Registry(), 2)


@pytest.mark.parametrize("actions,steps", [({}, 2), ([], 0), ([], True)])
def test_invalid_outer_contract(submission, actions, steps):
    with pytest.raises(ValueError):
        submission.replay_tool_actions(actions, Registry(), steps)


def test_actions_are_not_mutated(submission):
    actions = [{"type": "final", "content": "done"}]; before = copy.deepcopy(actions)
    submission.replay_tool_actions(actions, Registry())
    assert actions == before
