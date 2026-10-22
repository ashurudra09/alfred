"""Build the MCP tool definitions from the contracts and write `tools.json`.

Uses FastMCP's own `Tool.from_function`, so the schemas are exactly what the Phase 6 server will list.
Usage: uv run python -m alfred.contracts.export
"""

import json
from pathlib import Path

from mcp.server.fastmcp.tools import Tool
from mcp.types import ToolAnnotations

from alfred.contracts.tools import CONTRACTS_VERSION, REGISTRY

TOOLS_JSON = Path(__file__).with_name("tools.json")


def mcp_tool(name: str) -> Tool:
    """The FastMCP Tool for a contract. The Phase 6 server passes the same arguments with the real body."""
    r = REGISTRY[name]
    return Tool.from_function(
        r["fn"], name=name, description=r["fn"].__doc__,
        annotations=ToolAnnotations(readOnlyHint=r["read_only"], destructiveHint=r["destructive"],
                                    idempotentHint=r["read_only"], openWorldHint=False),
        meta={"alfred/group": r["group"], "alfred/needs_confirmation": r["needs_confirmation"]},
        structured_output=False,
    )


def build() -> dict:
    tools = []
    for name in REGISTRY:
        t = mcp_tool(name)
        tools.append({"name": t.name, "description": t.description, "inputSchema": t.parameters,
                      "annotations": t.annotations.model_dump(exclude_none=True), "_meta": t.meta})
    return {"version": CONTRACTS_VERSION, "tools": tools}


def render(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def load() -> dict:
    return json.loads(TOOLS_JSON.read_text(encoding="utf-8"))


def compact(schema: dict) -> dict:
    """Drop pydantic's `title`s and turn `anyOf: [X, null]` into X (optional = not in `required`). Saves prompt tokens."""
    if isinstance(schema, list):
        return [compact(s) for s in schema]
    if not isinstance(schema, dict):
        return schema
    out = {k: compact(v) for k, v in schema.items() if k != "title" or not isinstance(v, str)}
    if "properties" in schema:  # property names may be called "title"; don't drop those
        out["properties"] = {k: compact(v) for k, v in schema["properties"].items()}
    any_of = out.pop("anyOf", None)
    if any_of:
        non_null = [s for s in any_of if s != {"type": "null"}]
        if len(non_null) == 1:
            out = {**non_null[0], **out}
            if out.get("default", ...) is None:
                del out["default"]
        else:
            out["anyOf"] = any_of
    return out


def openai_tools(data: dict | None = None) -> list[dict]:
    """tools.json in the OpenAI / chat-template `tools=` shape used for prompts, training data and backends.
    Compacted; argument validation still uses the full inputSchema."""
    return [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                              "parameters": compact(t["inputSchema"])}}
            for t in (data or load())["tools"]]


if __name__ == "__main__":
    TOOLS_JSON.write_text(render(build()), encoding="utf-8")
    print(f"wrote {TOOLS_JSON} ({len(REGISTRY)} tools, v{CONTRACTS_VERSION})")
