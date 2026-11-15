from jsonschema import Draft202012Validator

from alfred.contracts.schemas import Example, Message, ToolCall
from alfred.contracts.tools import REGISTRY
from eval.unseen import specs


def test_specs_are_valid_and_disjoint_from_alfred():
    assert len(specs.HELD_OUT) == 10 and len(specs.NAMES) == 10 and not specs.NAMES & set(REGISTRY)
    for t in specs.HELD_OUT:
        Draft202012Validator.check_schema(t["function"]["parameters"])
        props = t["function"]["parameters"]["properties"]
        assert set(t["function"]["parameters"]["required"]) <= set(props) and t["function"]["description"]
        assert all(p.get("description") for p in props.values())
    assert all("read_only" not in t for t in specs.openai_tools())


def test_uses_held_out_sees_offers_calls_and_lookalikes():
    def ex(tool, call=None):
        t = {"type": "function", "function": {"name": tool, "description": "", "parameters": {"type": "object"}}}
        return Example(id="x", source="xlam", category="tool_call", tools=[t], messages=[
            Message(role="user", content="q"), Message(role="assistant", tool_calls=[ToolCall(name=call or tool)])])
    assert specs.uses_held_out(ex("get_weather")) == set()
    assert specs.uses_held_out(ex("ConvertUnits")) == {"convertUnits"}  # case-insensitive
    assert specs.uses_held_out(ex("get_weather", call="todo_add")) == {"todo_add"}
    assert specs.uses_held_out(ex("hsl_to_rgb")) == {"hsl_to_rgb"}  # same job under another name
