import pytest

SCHEMA={"name":"add","description":"Add integers","parameters":{"type":"object","properties":{"a":{"type":"integer"},"b":{"type":"integer"}},"required":["a","b"]}}

def test_register_and_call(submission):
    registry=submission.ToolRegistry(); registry.register(SCHEMA,lambda a,b:a+b)
    assert registry.call("add",{"a":2,"b":3})==5

def test_names_are_sorted_and_immutable(submission):
    r=submission.ToolRegistry()
    for name in ("z","a"):
        schema={"name":name,"description":"toy","parameters":{"type":"object","properties":{},"required":[]}}
        r.register(schema,lambda:None)
    assert r.names==("a","z") and isinstance(r.names,tuple)

def test_duplicate_and_unknown_tool_raise(submission):
    r=submission.ToolRegistry(); r.register(SCHEMA,lambda a,b:a+b)
    with pytest.raises(ValueError): r.register(SCHEMA,lambda a,b:0)
    with pytest.raises(ValueError): r.call("missing",{})

@pytest.mark.parametrize("args", [{"a":1},{"a":1,"b":2,"c":3},{"a":True,"b":2},{"a":"1","b":2}])
def test_argument_validation_precedes_handler(submission,args):
    called=[]; r=submission.ToolRegistry(); r.register(SCHEMA,lambda **kw:called.append(kw))
    with pytest.raises(ValueError): r.call("add",args)
    assert called==[]

def test_handler_exception_propagates(submission):
    r=submission.ToolRegistry(); r.register(SCHEMA,lambda a,b:1/0)
    with pytest.raises(ZeroDivisionError): r.call("add",{"a":1,"b":2})

