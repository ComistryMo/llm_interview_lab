import copy
import pytest

class Registry:
    names=("add",)
    def call(self,name,args):
        if name!="add": raise ValueError("unknown")
        return args["a"]+args["b"]

def test_tool_then_final_trajectory(submission):
    actions=iter([{"type":"tool","name":"add","arguments":{"a":2,"b":3}},{"type":"final","content":"5"}])
    trajectory=submission.run_tool_calling_loop(lambda h:next(actions),Registry(),[{"role":"user","content":"add"}])
    assert trajectory[-1]=={"type":"final","content":"5"}
    assert any(item.get("type")=="observation" and item.get("result")==5 for item in trajectory)

def test_model_receives_updated_defensive_history(submission):
    lengths=[]
    def model(history):
        lengths.append(len(history)); return {"type":"final","content":"done"}
    messages=[{"role":"user","content":"x"}]; submission.run_tool_calling_loop(model,Registry(),messages)
    assert lengths==[1] and messages==[{"role":"user","content":"x"}]

def test_invalid_action_becomes_observation_then_can_recover(submission):
    actions=iter([{"bad":1},{"type":"final","content":"ok"}])
    trajectory=submission.run_tool_calling_loop(lambda h:next(actions),Registry(),[])
    assert any(item.get("type")=="observation" and "error" in item for item in trajectory)
    assert trajectory[-1]["content"]=="ok"

def test_tool_validation_error_is_observed(submission):
    actions=iter([{"type":"tool","name":"missing","arguments":{}},{"type":"final","content":"fallback"}])
    trajectory=submission.run_tool_calling_loop(lambda h:next(actions),Registry(),[])
    assert "error" in trajectory[1] and trajectory[-1]["content"]=="fallback"

def test_max_steps_raises(submission):
    with pytest.raises(RuntimeError): submission.run_tool_calling_loop(lambda h:{"bad":1},Registry(),[],2)

@pytest.mark.parametrize("messages,steps", [({},2),([],0),([],True)])
def test_invalid_outer_contract_raises(submission,messages,steps):
    with pytest.raises(ValueError): submission.run_tool_calling_loop(lambda h:{},Registry(),messages,steps)

