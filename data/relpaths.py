"""Rewrite an Alfred example's paths to the form the tools now print (run A finding 1, docs/v4/run_a_findings.md).

The tools print a path relative to its known folder ('Desktop\\shared\\x.xlsx', alfred.tools.guards.show) and
list_directory gives every item its whole relative path, so the model copies paths instead of joining a long root
with a name. This applies the same to existing training data, deterministically: tool results, the assistant's
call arguments and its text. The system prompt (it states the roots) and the user's words stay as they are.
"""

import re

from alfred.contracts.schemas import Example

FOLDER_LINE = re.compile(r"^- ([^:\n]+): (.+)$", re.M)
HEADER = re.compile(r"^(.+?) \(\d+ items?\):$")
ITEM = re.compile(r"^(?!\.\.\.|\()[^\\]+\\? \([^)]*\)$")  # "photos\ (folder)", "a.pdf (1.2 MB)"


def roots(ex: Example) -> list[tuple[str, str]]:
    """(name, root) from the system prompt's known-folder list, deepest root first."""
    sys = ex.messages[0].content if ex.messages and ex.messages[0].role == "system" else ""
    found = [(n.strip(), r.strip().rstrip("\\")) for n, r in FOLDER_LINE.findall(sys.split("Known folders:")[-1])
             if re.match(r"[A-Za-z]:\\", r.strip())] if "Known folders:" in sys else []
    return sorted(found, key=lambda x: -len(x[1]))


def text(s: str, rs: list[tuple[str, str]]) -> str:
    for name, root in rs:
        s = re.sub(re.escape(root) + r"(?=\\|[^\w\\]|$)", lambda _: name, s, flags=re.I)
    return s


def listing(s: str) -> str:
    """list_directory's result: prefix every item line with the folder in the header."""
    lines = s.split("\n")
    m = HEADER.match(lines[0]) if lines else None
    if not m:
        return s
    base = m.group(1).rstrip("\\")
    return "\n".join([lines[0]] + [f"{base}\\{x}" if ITEM.match(x) else x for x in lines[1:]])


def _arg(v, rs):
    if isinstance(v, str):
        return text(v, rs)
    if isinstance(v, list):
        return [_arg(x, rs) for x in v]
    return v


def apply(ex: Example) -> Example:
    rs = roots(ex)
    if not rs:
        return ex
    msgs = []
    for m in ex.messages:
        if m.role == "tool":
            c = text(m.content, rs)
            m = m.model_copy(update={"content": listing(c) if m.name == "list_directory" else c})
        elif m.role == "assistant":
            calls = [c.model_copy(update={"arguments": {k: _arg(v, rs) for k, v in c.arguments.items()}})
                     for c in m.tool_calls] if m.tool_calls else m.tool_calls
            m = m.model_copy(update={"content": text(m.content, rs), "tool_calls": calls})
        msgs.append(m)
    return ex.model_copy(update={"messages": msgs})
