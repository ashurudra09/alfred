"""The held-out tools (eval/unseen/specs.py) as a real MCP server over stdio (track 4F, step F2), so the unseen-tools
evaluation can check outcomes and not just the call. Listed with exactly the frozen schemas.

State (clipboard, to-do list) lives in a JSON file under Alfred's home (ALFRED_HOME), so each e2e sandbox gets its
own and the real clipboard is never touched. File arguments go through Alfred's own path guards.

Run: uv run python -m eval.unseen.server     (add to config.json: "mcp_servers": {"unseen": {"command": "<python>",
                                                "args": ["-m", "eval.unseen.server"]}})
"""

import asyncio
import colorsys
import difflib
import hashlib
import json
import re

from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.server.fastmcp.exceptions import ToolError

from alfred.tools.guards import home, resolve_safe
from eval.unseen.specs import HELD_OUT


def _state() -> dict:
    p = home() / "unseen_state.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"clipboard": "", "todos": []}


def _save(s: dict):
    (home() / "unseen_state.json").write_text(json.dumps(s, indent=1, ensure_ascii=False), encoding="utf-8")


def clipboard_get():
    return _state()["clipboard"] or "The clipboard is empty."


def clipboard_set(text):
    s = _state()
    s["clipboard"] = text
    _save(s)
    return f"Copied {len(text)} characters to the clipboard."


# factor to the base unit (m, kg, l); temperatures are handled apart
UNITS = {"mm": .001, "cm": .01, "m": 1, "km": 1000, "in": .0254, "ft": .3048, "yd": .9144, "mi": 1609.344,
         "mg": 1e-6, "g": .001, "kg": 1, "oz": .028349523125, "lb": .45359237, "st": 6.35029318,
         "ml": .001, "l": 1, "tsp": .00492892159375, "tbsp": .01478676478125, "cup": .2365882365,
         "pt": .473176473, "qt": .946352946, "gal": 3.785411784}
KIND = {**dict.fromkeys(["mm", "cm", "m", "km", "in", "ft", "yd", "mi"], "length"),
        **dict.fromkeys(["mg", "g", "kg", "oz", "lb", "st"], "weight"),
        **dict.fromkeys(["ml", "l", "tsp", "tbsp", "cup", "pt", "qt", "gal"], "volume"),
        **dict.fromkeys(["c", "f", "k"], "temperature")}
ALIASES = {"miles": "mi", "mile": "mi", "kilometres": "km", "kilometers": "km", "metres": "m", "meters": "m",
           "feet": "ft", "foot": "ft", "inches": "in", "inch": "in", "pounds": "lb", "pound": "lb", "lbs": "lb",
           "kilograms": "kg", "grams": "g", "ounces": "oz", "litres": "l", "liters": "l", "gallons": "gal",
           "celsius": "c", "fahrenheit": "f", "kelvin": "k", "°c": "c", "°f": "f"}


def _unit(u: str) -> str:
    u = u.strip().casefold()
    u = ALIASES.get(u, u)
    if u not in KIND:
        raise ToolError(f"Unknown unit '{u}'.")
    return u


def convertUnits(value, from_unit, to_unit):
    a, b = _unit(from_unit), _unit(to_unit)
    if KIND[a] != KIND[b]:
        raise ToolError(f"Can't convert {KIND[a]} to {KIND[b]}.")
    if KIND[a] == "temperature":
        c = {"c": value, "f": (value - 32) * 5 / 9, "k": value - 273.15}[a]
        out = {"c": c, "f": c * 9 / 5 + 32, "k": c + 273.15}[b]
    else:
        out = value * UNITS[a] / UNITS[b]
    return f"{value:g} {from_unit} = {round(out, 4):g} {to_unit}"


def countWords(file):
    text = resolve_safe(file).read_text(encoding="utf-8", errors="replace")
    return f"{len(text.split())} words, {len(text.splitlines())} lines, {len(text)} characters"


def hashFile(file, algorithm="sha256"):
    p = resolve_safe(file)
    return f"{algorithm} {hashlib.new(algorithm, p.read_bytes()).hexdigest()}  {p.name}"


def files_differ(first, second):
    a, b = (resolve_safe(f).read_text(encoding="utf-8", errors="replace").splitlines() for f in (first, second))
    lines = [x for x in difflib.unified_diff(a, b, first, second, lineterm="", n=0) if not x.startswith("@@")]
    return "\n".join(lines) if lines else "The files are identical."


def todo_add(item, priority="normal", due=None):
    if due and not re.fullmatch(r"\d{4}-\d\d-\d\d", due):
        raise ToolError("due must be YYYY-MM-DD.")
    s = _state()
    s["todos"].append({"item": item, "priority": priority, "due": due, "done": False})
    _save(s)
    return f"Added to-do {len(s['todos'])}: {item}"


def todo_list(show="open"):
    rows = [f"{i}. [{'x' if t['done'] else ' '}] {t['item']} ({t['priority']}{', due ' + t['due'] if t['due'] else ''})"
            for i, t in enumerate(_state()["todos"], 1) if show == "all" or t["done"] == (show == "done")]
    return "\n".join(rows) if rows else f"No {show} to-do items."


def todo_done(number):
    s = _state()
    if not 1 <= number <= len(s["todos"]):
        raise ToolError(f"There is no to-do item {number}.")
    s["todos"][number - 1]["done"] = True
    _save(s)
    return f"Marked to-do {number} as done: {s['todos'][number - 1]['item']}"


def colorConvert(color, to):
    c = color.strip().casefold()
    if m := re.fullmatch(r"#?([0-9a-f]{6})", c):
        rgb = tuple(int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4))
    elif m := re.fullmatch(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", c):
        rgb = tuple(int(x) for x in m.groups())
    elif m := re.fullmatch(r"hsl\(\s*(\d+)\s*,\s*(\d+)%\s*,\s*(\d+)%\s*\)", c):
        h, s, l = (int(x) for x in m.groups())
        rgb = tuple(round(v * 255) for v in colorsys.hls_to_rgb(h / 360, l / 100, s / 100))
    else:
        raise ToolError(f"Can't read the colour '{color}'.")
    if to == "hex":
        return "#" + "".join(f"{v:02x}" for v in rgb)
    if to == "rgb":
        return f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"
    h, l, s = colorsys.rgb_to_hls(*(v / 255 for v in rgb))
    return f"hsl({round(h * 360)}, {round(s * 100)}%, {round(l * 100)}%)"


IMPLS = {"clipboard_get": clipboard_get, "clipboard_set": clipboard_set, "convertUnits": convertUnits,
         "countWords": countWords, "hashFile": hashFile, "files-differ": files_differ, "todo_add": todo_add,
         "todo_list": todo_list, "todo_done": todo_done, "colorConvert": colorConvert}
assert set(IMPLS) == {t["function"]["name"] for t in HELD_OUT}

server = Server("alfred-unseen")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [types.Tool(name=t["function"]["name"], description=t["function"]["description"],
                       inputSchema=t["function"]["parameters"],
                       annotations=types.ToolAnnotations(readOnlyHint=t["read_only"])) for t in HELD_OUT]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        text = str(IMPLS[name](**arguments))
    except ToolError as e:
        raise ValueError(str(e)) from None  # the low-level server turns it into an isError result
    return [types.TextContent(type="text", text=text)]


async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
