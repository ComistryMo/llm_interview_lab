import copy
import pytest

def valid():
    return {"name":"get_weather","description":"Return toy weather","parameters":{"type":"object","properties":{"city":{"type":"string"},"days":{"type":"integer"}},"required":["city"]}}

def test_valid_schema_is_defensively_copied(submission):
    source=valid(); result=submission.validate_tool_schema(source)
    assert result==source and result is not source and result["parameters"] is not source["parameters"]

def test_nested_result_does_not_alias_input(submission):
    source=valid(); result=submission.validate_tool_schema(source); result["parameters"]["required"].append("days")
    assert source["parameters"]["required"]==["city"]

@pytest.mark.parametrize("change", [{"name":"Bad-Name"},{"name":""},{"description":""},{"parameters":[]},{"extra":1}])
def test_invalid_top_level_contract_raises(submission,change):
    schema=valid(); schema.update(change)
    with pytest.raises(ValueError): submission.validate_tool_schema(schema)

def test_required_name_must_exist(submission):
    schema=valid(); schema["parameters"]["required"]=["missing"]
    with pytest.raises(ValueError): submission.validate_tool_schema(schema)

@pytest.mark.parametrize("kind", ["null","function",True])
def test_unsupported_property_type_raises(submission,kind):
    schema=valid(); schema["parameters"]["properties"]["city"]["type"]=kind
    with pytest.raises(ValueError): submission.validate_tool_schema(schema)

