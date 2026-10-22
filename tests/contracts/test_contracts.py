from datetime import date, datetime

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from alfred.contracts.export import TOOLS_JSON, build, load, openai_tools, render
from alfred.contracts.prompt import render_system_prompt
from alfred.contracts.schemas import Example, Message, TestItem, ToolCall
from alfred.contracts.tools import REGISTRY

# requirements Section 5, in order
SPEC_NAMES = ["search_files", "search_file_contents", "list_directory", "read_file", "disk_usage", "move_file",
              "rename_file", "copy_file", "zip_folder", "organize_folder", "move_to_recycle_bin", "open_path",
              "open_app", "system_info", "top_processes", "network_status", "port_in_use", "git_status",
              "create_note", "search_notes", "set_reminder", "list_reminders", "remember", "recall", "calculate"]
SPEC_CONFIRM = {"move_file", "rename_file", "copy_file", "zip_folder", "organize_folder", "move_to_recycle_bin"}
SPEC_READ = {"search_files", "search_file_contents", "list_directory", "read_file", "disk_usage", "system_info",
             "top_processes", "network_status", "port_in_use", "git_status", "search_notes", "list_reminders",
             "recall", "calculate"}
FOLDERS = {"Documents": r"C:\Users\asha\Documents", "Downloads": r"C:\Users\asha\Downloads"}


def test_names_match_spec():
    assert list(REGISTRY) == SPEC_NAMES
    assert [t["name"] for t in load()["tools"]] == SPEC_NAMES


def test_flags_match_spec():
    assert {n for n, r in REGISTRY.items() if r["needs_confirmation"]} == SPEC_CONFIRM
    assert {n for n, r in REGISTRY.items() if r["read_only"]} == SPEC_READ
    assert not any(r["read_only"] and (r["destructive"] or r["needs_confirmation"]) for r in REGISTRY.values())
    for t in load()["tools"]:
        assert t["_meta"]["alfred/needs_confirmation"] == (t["name"] in SPEC_CONFIRM)
        assert t["annotations"]["readOnlyHint"] == (t["name"] in SPEC_READ)


def test_every_tool_and_arg_is_described():
    for t in load()["tools"]:
        assert t["description"] and len(t["description"]) <= 120, t["name"]


def test_tools_json_is_current():
    assert TOOLS_JSON.read_text(encoding="utf-8") == render(build()), "run: uv run python -m alfred.contracts.export"


@pytest.mark.parametrize("compacted", [False, True])
def test_schemas_are_valid_json_schema(compacted):
    schemas = [t["function"]["parameters"] for t in openai_tools()] if compacted else \
        [t["inputSchema"] for t in load()["tools"]]
    for s in schemas:
        Draft202012Validator.check_schema(s)
        assert s["type"] == "object"


def test_schemas_validate_arguments():
    schemas = {t["name"]: Draft202012Validator(t["inputSchema"]) for t in load()["tools"]}
    assert schemas["port_in_use"].is_valid({"port": 3000})
    assert not schemas["port_in_use"].is_valid({"port": 70000})
    assert not schemas["port_in_use"].is_valid({})
    assert schemas["organize_folder"].is_valid({"path": "Downloads", "strategy": "by_date"})
    assert not schemas["organize_folder"].is_valid({"path": "Downloads", "strategy": "by_size"})
    assert schemas["search_files"].is_valid({"query": "cv", "folder": "Documents", "extension": None})


def test_compact_keeps_property_named_title():
    note = next(t for t in openai_tools() if t["function"]["name"] == "create_note")["function"]["parameters"]
    assert set(note["properties"]) == {"title", "content"}
    assert "anyOf" not in str(openai_tools()) and "'title': 'Query'" not in str(openai_tools())


def test_prompt_is_deterministic_and_date_only():
    a = render_system_prompt(FOLDERS, datetime(2026, 10, 22, 9, 1, 5))
    assert a == render_system_prompt(FOLDERS, datetime(2026, 10, 22, 23, 59))  # time of day never changes it
    assert a == render_system_prompt(dict(FOLDERS), date(2026, 10, 22))
    assert "2026-10-22 (Thursday)" in a and r"- Downloads: C:\Users\asha\Downloads" in a
    assert a != render_system_prompt({"Documents": r"C:\Users\ravi\Documents"}, date(2026, 10, 22))


def test_prompt_token_count():
    tokenizers = pytest.importorskip("tokenizers")
    from huggingface_hub import hf_hub_download
    try:
        tok = tokenizers.Tokenizer.from_file(hf_hub_download("Qwen/Qwen3.5-2B", "tokenizer.json"))
    except Exception as e:
        pytest.skip(f"tokenizer unavailable offline: {e}")
    import json
    system = len(tok.encode(render_system_prompt(FOLDERS, date(2026, 10, 22))).ids)
    tools = len(tok.encode(json.dumps(openai_tools(), ensure_ascii=False)).ids)
    print(f"\nprompt tokens: system {system} + tools {tools} = {system + tools} (before chat-template wrapping)")
    assert system + tools < 2400  # guard against growth; prefix is cached by llama-server


def test_data_formats():
    call = Message(role="assistant", tool_calls=[ToolCall(name="recall", arguments={"query": "resume folder"})])
    result = Message(role="tool", name="recall", content="Resume folder is D:\\docs\\resume")
    item = TestItem(id="t1", messages=[Message(role="user", content="zip my resume folder"), call, result],
                    expected_decision="tool_call",
                    expected_calls=[ToolCall(name="zip_folder", arguments={"source": "D:\\docs\\resume"})],
                    arg_rules={"source": "path"})
    assert TestItem.model_validate_json(item.model_dump_json()) == item
    Example(id="e1", source="synthetic", category="multi_step", tools=openai_tools(),
            messages=[*item.messages, Message(role="assistant", tool_calls=item.expected_calls)])
    with pytest.raises(ValidationError):
        TestItem(id="t2", messages=item.messages[:1], expected_decision="tool_call")  # no expected call
    with pytest.raises(ValidationError):
        TestItem(id="t3", messages=item.messages[:1], expected_decision="direct", expected_calls=item.expected_calls)
    with pytest.raises(ValidationError):
        Message(role="tool", content="x")  # tool result without the tool's name
    with pytest.raises(ValidationError):
        Example(id="e2", source="x", category="direct", tools=[], messages=item.messages[:1])  # no assistant turn
