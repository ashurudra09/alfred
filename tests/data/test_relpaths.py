from datetime import date

from alfred.contracts.export import openai_tools
from alfred.contracts.prompt import render_system_prompt
from alfred.contracts.schemas import Example, Message, ToolCall
from data import relpaths

FOLDERS = {"Documents": r"C:\Users\asha\Documents", "Docs2": r"C:\Users\asha\Documents2",
           "Work": r"C:\Users\asha\Documents\work"}


def test_paths_become_relative_to_their_known_folder():
    sys = render_system_prompt(FOLDERS, date(2026, 10, 22))
    ex = Example(id="x", source="synthetic", category="multi_step", tools=openai_tools(), messages=[
        Message(role="system", content=sys),
        Message(role="user", content=r"tidy C:\Users\asha\Documents\work"),
        Message(role="assistant", tool_calls=[ToolCall(name="list_directory", arguments={"path": r"C:\Users\asha\Documents\work"})]),
        Message(role="tool", name="list_directory",
                content="C:\\Users\\asha\\Documents\\work (3 items):\nold\\ (folder)\na.pdf (1.2 MB)\n..."),
        Message(role="assistant", tool_calls=[ToolCall(name="zip_folder", arguments={
            "source": r"c:\users\asha\documents2\x", "extra_files": [r"C:\Users\asha\Documents\b.txt"]})]),
        Message(role="assistant", content=r"Zipped C:\Users\asha\Documents\b.txt; D:\other stays.")])
    out = relpaths.apply(ex).messages
    assert out[0].content == sys and out[1].content == ex.messages[1].content  # prompt and user untouched
    assert out[2].tool_calls[0].arguments == {"path": "Work"}
    assert out[3].content == "Work (3 items):\nWork\\old\\ (folder)\nWork\\a.pdf (1.2 MB)\n..."
    assert out[4].tool_calls[0].arguments == {"source": "Docs2\\x", "extra_files": ["Documents\\b.txt"]}
    assert out[5].content == r"Zipped Documents\b.txt; D:\other stays."
