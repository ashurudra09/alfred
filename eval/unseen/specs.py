"""Held-out tools for the unseen-tools evaluation (track 4F), frozen in track 1C before any v4 training data
is mixed. No training example may use any of these names: `data/mix.py` drops public-dataset examples that do and
asserts none is left (`uses_held_out`).

Ten tools a plug-in MCP server could plausibly offer next to Alfred's own, chosen so that:
- each can be implemented for real and its outcome checked (track 4F step F2);
- several sit next to a built-in tool, so the description has to be read (todo_* vs reminders and notes,
  countWords vs read_file, convertUnits vs calculate, compare-files vs search_file_contents);
- naming styles differ from Alfred's snake_case verb_noun (camelCase, noun-first, a hyphen).

Written by Claude, like the other test sets, and disclosed as such. The shape is the OpenAI tool list the chat
template takes, plus the two flags the agent loop needs for tools from other servers.
"""

SPECS_VERSION = "1.0"


def _tool(name: str, description: str, properties: dict, required: list[str], read_only: bool) -> dict:
    return {"type": "function", "read_only": read_only,
            "function": {"name": name, "description": description,
                         "parameters": {"type": "object", "properties": properties, "required": required}}}


S, I, N = {"type": "string"}, {"type": "integer"}, {"type": "number"}

HELD_OUT = [
    _tool("clipboard_get", "Return the text currently on the clipboard.", {}, [], True),
    _tool("clipboard_set", "Put text on the clipboard, replacing what is there.",
          {"text": {**S, "description": "The text to copy"}}, ["text"], False),
    _tool("convertUnits", "Convert a quantity between units of length, weight, temperature or volume "
                          "(e.g. miles to km, F to C). Not for arithmetic or file sizes.",
          {"value": {**N, "description": "The amount to convert"},
           "from_unit": {**S, "description": "Unit of the value, e.g. 'mi', 'lb', 'F'"},
           "to_unit": {**S, "description": "Unit wanted, e.g. 'km', 'kg', 'C'"}},
          ["value", "from_unit", "to_unit"], True),
    _tool("countWords", "Count the words, lines and characters in a text file without returning its text.",
          {"file": {**S, "description": "Path of the file"}}, ["file"], True),
    _tool("hashFile", "Compute a checksum of a file, to verify a download or compare copies.",
          {"file": {**S, "description": "Path of the file"},
           "algorithm": {**S, "enum": ["sha256", "sha1", "md5"], "description": "Default sha256"}}, ["file"], True),
    _tool("files-differ", "Compare two text files and list the lines that differ.",
          {"first": {**S, "description": "Path of one file"}, "second": {**S, "description": "Path of the other file"}},
          ["first", "second"], True),
    _tool("todo_add", "Add an item to the to-do list. For something that must alert at a time, a reminder fits "
                      "better.",
          {"item": {**S, "description": "What needs doing"},
           "priority": {**S, "enum": ["low", "normal", "high"], "description": "Default normal"},
           "due": {**S, "description": "Optional due date, YYYY-MM-DD"}}, ["item"], False),
    _tool("todo_list", "Show the to-do list.",
          {"show": {**S, "enum": ["open", "done", "all"], "description": "Which items; default open"}}, [], True),
    _tool("todo_done", "Mark a to-do item as done, by its number in the list.",
          {"number": {**I, "minimum": 1, "description": "The item's number as shown by todo_list"}}, ["number"], False),
    _tool("colorConvert", "Convert a colour between hex, RGB and HSL notation.",
          {"color": {**S, "description": "The colour, e.g. '#1e90ff' or 'rgb(30, 144, 255)'"},
           "to": {**S, "enum": ["hex", "rgb", "hsl"], "description": "Notation wanted"}}, ["color", "to"], True),
]
NAMES = frozenset(t["function"]["name"] for t in HELD_OUT)


# Tools in the xLAM-60k training source that do the same job as a held-out tool under another name (found by
# listing its 3,605 tool names, 2026-11-16; about 840 of 60,000 examples use one). Examples offering or calling
# them are kept out of training too, so the held-out tools are new in function, not only in name.
LOOKALIKES = frozenset({
    "convert_hex", "convert_hsl", "convert_rgb", "hex_to_cmyk", "hex_to_hsv", "hex_to_rgb", "hsl_to_hex", "hsl_to_rgb",
    "rgb_to_cmyk", "rgb_to_hsl", "rgb_to_hsv",  # colorConvert
    "convert_a_unit", "convert_cooking_measurements", "convert_from_one_unit_to_another",
    "transform_units_using_the_get_method",  # convertUnits
    "md5_text_hash", "sha_text_hash",  # hashFile
})


def openai_tools() -> list[dict]:
    """The specs in the plain chat-template shape (without the read_only flag)."""
    return [{"type": "function", "function": t["function"]} for t in HELD_OUT]


def uses_held_out(example) -> set[str]:
    """Held-out tool names (case-insensitive, so `convertunits` counts too) and look-alike tools that an Example
    offers, calls or has results from."""
    low = {n.casefold(): n for n in NAMES | LOOKALIKES}
    seen = {t["function"]["name"] for t in example.tools} | {c.name for m in example.messages for c in m.tool_calls or []}
    seen |= {m.name for m in example.messages if m.name}
    return {low[s.casefold()] for s in seen if s.casefold() in low}
