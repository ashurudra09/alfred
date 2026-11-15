import json
from datetime import date

import pytest
from jsonschema import Draft202012Validator

from alfred.contracts.export import openai_tools
from alfred.contracts.prompt import render_system_prompt
from alfred.contracts.schemas import Example, Message, ToolCall
from data import augment

FOLDERS = {"Documents": r"C:\Users\asha\Documents", "Downloads": r"C:\Users\asha\Downloads"}


def alfred_example() -> Example:
    path = r"C:\Users\asha\Downloads\old_report.pdf"
    return Example(id="syn-1", source="synthetic", category="multi_step", tools=openai_tools(), messages=[
        Message(role="system", content=render_system_prompt(FOLDERS, date(2026, 10, 22))),
        Message(role="user", content="find my old report and delete it, don't use search_notes for this"),
        Message(role="assistant", tool_calls=[ToolCall(name="search_files", arguments={"query": "old report",
                                                                                      "modified_within_days": 30})]),
        Message(role="tool", name="search_files", content=f"1 file:\n{path} (2.1 MB, modified 2026-10-15)"),
        Message(role="assistant", tool_calls=[ToolCall(name="move_to_recycle_bin", arguments={"path": path})]),
        Message(role="tool", name="move_to_recycle_bin", content=f"Moved {path} to the Recycle Bin. Undo: /undo"),
        Message(role="assistant", content="Done, old_report.pdf is in the Recycle Bin.")])


def plain_word_example() -> Example:
    """xLAM style: the tool and its argument are ordinary words that also occur in the request."""
    tool = {"type": "function", "function": {"name": "search", "description": "Search the web. See also get_news.",
                                             "parameters": {"type": "object", "required": ["query"], "properties": {
                                                 "query": {"type": "string", "description": "What to search for"},
                                                 "max_results": {"type": "integer", "description": "Cap on results"}}}}}
    news = {"type": "function", "function": {"name": "get_news", "description": "Headlines; max_results as in search.",
                                             "parameters": {"type": "object", "properties": {}, "required": []}}}
    return Example(id="xlam-00007", source="xlam", category="tool_call", tools=[tool, news], messages=[
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="search for my query about llamas, 3 results"),
        Message(role="assistant", tool_calls=[ToolCall(name="search", arguments={"query": "llamas", "max_results": 3})])])


@pytest.mark.parametrize("make", [alfred_example, plain_word_example])
def test_mask_is_consistent_and_reversible(make):
    ex = make()
    masked, mapping = augment.mask(ex, seed=1)
    assert augment.leaks(masked, mapping) == []
    schemas = {t["function"]["name"]: Draft202012Validator(t["function"]["parameters"]) for t in masked.tools}
    calls = [c for m in masked.messages for c in m.tool_calls or []]
    assert calls and all(schemas[c.name].is_valid(c.arguments) for c in calls)  # calls fit the masked schemas
    assert [m.name for m in masked.messages if m.role == "tool"] == [c.name for c in calls if any(
        m.role == "tool" for m in masked.messages)]
    assert augment.unmask(masked, mapping).model_dump_json() == ex.model_dump_json()  # byte for byte
    assert augment.mask(ex, seed=1)[1] == mapping and augment.mask(ex, seed=2)[1] != mapping  # deterministic per seed


def test_alfred_names_are_gone_everywhere():
    ex = alfred_example()
    masked, mapping = augment.mask(ex)
    blob = masked.model_dump_json()
    for name in mapping["tools"]:
        if augment.identifier_like(name):
            assert name not in blob, name  # system prompt, descriptions and the user's own mention included
    assert mapping["tools"]["move_to_recycle_bin"] in masked.messages[0].content
    assert mapping["tools"]["search_notes"] in masked.messages[1].content
    assert [m.content for m in masked.messages[3:]] == [m.content for m in ex.messages[3:]]  # results, reply untouched
    assert masked.messages[2].tool_calls[0].arguments == {mapping["args"]["query"]: "old report",
                                                          mapping["args"]["modified_within_days"]: 30}


def test_plain_words_stay_in_text():
    masked, mapping = augment.mask(plain_word_example())
    assert masked.messages[1].content == "search for my query about llamas, 3 results"
    f = masked.tools[0]["function"]
    assert f["name"] == mapping["tools"]["search"] and mapping["tools"]["get_news"] in f["description"]
    assert mapping["args"]["max_results"] in masked.tools[1]["function"]["description"]
    assert set(f["parameters"]["properties"]) == set(mapping["args"].values())
    assert f["parameters"]["required"] == [mapping["args"]["query"]]


def test_apply_masks_the_configured_share():
    exs = [plain_word_example().model_copy(update={"id": f"xlam-{i:05d}"}) for i in range(2000)]
    out, mappings = augment.apply(exs, seed=3)
    assert 0.29 < len(mappings) / len(exs) < 0.37 and len(out) == len(exs)
    assert all((o.id in mappings) == (o.tools != e.tools) for o, e in zip(out, exs))
    syn = [alfred_example().model_copy(update={"id": f"syn-{i}"}) for i in range(1000)]
    assert 0.07 < len(augment.apply(syn, seed=3)[1]) / 1000 < 0.13


def test_masked_example_renders_through_the_chat_template():
    pytest.importorskip("transformers")
    from data.mix import render
    try:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained("Qwen/Qwen3.5-2B")
    except Exception as e:
        pytest.skip(f"tokenizer unavailable offline: {e}")
    ex = alfred_example()
    masked, mapping = augment.mask(ex)
    text = render(masked, tok)
    assert "search_files" not in text and "move_to_recycle_bin" not in text
    assert json.dumps(mapping["tools"]["search_files"]) in text
    extra = len(tok(text)["input_ids"]) - len(tok(render(ex, tok))["input_ids"])
    print(f"\nmasking adds {extra} tokens to an Alfred example")
    assert 0 < extra < 450  # random names cost more tokens than real ones; matters for the 4,096-token limit
