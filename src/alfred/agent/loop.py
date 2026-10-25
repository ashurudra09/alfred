"""The agent loop (Phase 7): one user turn -> model calls -> tools -> answer, as a stream of events.

`run_turn` is the only interface the CLI and the UI use. It is a generator: a write tool yields `confirm_required`
and waits for the caller to `send(True/False)`; a caller that just iterates sends None, which counts as "no".

Events (`Event.kind`): token, retry, tool_call_proposed, confirm_required, tool_result, error, timing, done.
"""

import json
import time
from dataclasses import dataclass, field
from datetime import date

from jsonschema import Draft202012Validator
from mcp.server.fastmcp.exceptions import ToolError

from alfred.agent import chats
from alfred.agent.backends import openai_messages
from alfred.agent.timing import TurnTimer, log_turn
from alfred.contracts.export import openai_tools
from alfred.contracts.prompt import render_system_prompt
from alfred.contracts.schemas import Message, ToolCall
from alfred.tools.guards import config, known_folders

MAX_CALLS = 8  # per user turn (FR4); 3 blocked "do X to every file" past 2 files
DECLINED = "The user declined this change. Nothing was changed."  # the exact text the model was trained on


@dataclass
class Event:
    kind: str
    data: dict = field(default_factory=dict)


def problems(call, specs, validators, off=()) -> str | None:
    if call.name in off:
        return f"Tool '{call.name}' is disabled in Alfred's settings."
    if call.name not in specs:
        return f"Unknown tool '{call.name}'. Available: {', '.join(specs)}."
    if not isinstance(call.arguments, dict):
        return "The arguments were not valid JSON."
    errs = sorted(validators[call.name].iter_errors(call.arguments), key=str)
    return "Invalid arguments: " + "; ".join(e.message for e in errs[:3]) if errs else None


def preview(name: str, args: dict) -> str:
    from alfred.tools.files import preview as file_preview
    return file_preview(name, args)


def run_turn(chat_id: int, user_text: str, backend, tools, max_calls: int | None = None):
    cfg = config()  # settings tab: read once per turn, so changes apply from the next message
    max_calls = max_calls or cfg.get("max_calls", MAX_CALLS)
    off = set(cfg.get("disabled_tools", []))
    timer = TurnTimer()
    system = render_system_prompt(known_folders(), date.today())
    history, new = chats.context(chat_id, cfg.get("context_chars", chats.CONTEXT_CHARS)), [Message(role="user", content=user_text)]
    validators = {n: Draft202012Validator(s["schema"]) for n, s in tools.specs.items()}
    tool_defs = [t for t in openai_tools() if t["function"]["name"] not in off]
    calls_made, retried, final, log_calls = 0, False, "", []
    failed = {}  # (name, args) -> result of a call that failed or was declined this turn: never run it again

    while True:
        res = None
        for kind, value in backend.stream(openai_messages(history + new, system), tool_defs, cfg.get("temperature", 0.0)):
            if kind == "token":
                yield Event("token", {"text": value})
            else:
                res = value
        timer.llm(res)
        if res.error:
            final = "Sorry, the model backend failed. Is llama-server running?"
            yield Event("error", {"message": res.error})
            new.append(Message(role="assistant", content=final))
            break
        if not res.tool_calls:
            final = res.content.strip()
            new.append(Message(role="assistant", content=final))
            break

        issues = [problems(c, tools.specs, validators, off) for c in res.tool_calls]
        if any(issues):  # FR2: reject, tell the model why, one retry
            calls = [ToolCall(name=c.name, arguments=c.arguments if isinstance(c.arguments, dict) else {})
                     for c in res.tool_calls]
            new.append(Message(role="assistant", content=res.content, tool_calls=calls))
            new += [Message(role="tool", name=c.name, content=f"Error: {p}" if p else
                            "Not run: another call in the same message was invalid.") for c, p in zip(calls, issues)]
            if retried:
                final = "I couldn't make a valid tool call for that. Could you rephrase?"
                yield Event("error", {"message": "invalid tool call after a retry", "issues": issues})
                new.append(Message(role="assistant", content=final))
                break
            retried = True
            yield Event("retry", {"issues": [p for p in issues if p]})
            continue

        if calls_made + len(res.tool_calls) > max_calls:
            final = f"I stopped after {max_calls} tool calls for one request. Tell me how you'd like to continue."
            yield Event("error", {"message": "tool-call limit reached"})
            new.append(Message(role="assistant", content=final))
            break

        calls = [ToolCall(name=c.name, arguments=c.arguments) for c in res.tool_calls]
        new.append(Message(role="assistant", content=res.content, tool_calls=calls))
        for call in calls:
            calls_made += 1
            yield Event("tool_call_proposed", {"name": call.name, "args": call.arguments})
            text, is_error, approved = None, False, None
            key = (call.name, json.dumps(call.arguments, sort_keys=True))
            if key in failed:  # a model retrying the same failing call loops until the call limit
                text, is_error = f"Not run: this exact call already failed in this request ({failed[key][:200]}). " \
                                 "Answer the user with what you have.", True
            elif tools.specs[call.name]["needs_confirmation"]:  # FR8: writes run only after the user says yes
                try:
                    plan = preview(call.name, call.arguments)
                except ToolError as e:
                    text, is_error = str(e), True
                else:
                    t_wait = time.perf_counter()
                    approved = bool((yield Event("confirm_required", {"name": call.name, "args": call.arguments,
                                                                     "preview": plan})))
                    timer.t0 += time.perf_counter() - t_wait  # the user's thinking time isn't Alfred's latency
                    if not approved:
                        text = DECLINED
            if text is None:
                t0 = time.perf_counter()
                text, is_error = tools.call(call.name, call.arguments)
                timer.tool(call.name, time.perf_counter() - t0)
            if is_error or approved is False:
                failed.setdefault(key, text)
            yield Event("tool_result", {"name": call.name, "text": text, "is_error": is_error,
                                        "declined": approved is False})
            log_calls.append({"name": call.name, "args": call.arguments, "approved": approved,
                              "is_error": is_error, "result": text[:500]})
            new.append(Message(role="tool", name=call.name, content=text))

    chats.append(chat_id, new)
    t = timer.summary()
    log_turn({"chat": chat_id, "request": user_text, "calls": log_calls, "answer": final, "timing": t,
              "model": getattr(backend, "model", "?")})
    yield Event("timing", t)
    yield Event("done", {"text": final})


def drive(gen, confirm=lambda data: False, on_event=lambda e: None) -> list[Event]:
    """Run a turn to the end, answering confirmations with `confirm(data) -> bool`. Returns all events."""
    events, reply = [], None
    while True:
        try:
            e = gen.send(reply)
        except StopIteration:
            return events
        events.append(e)
        on_event(e)
        reply = confirm(e.data) if e.kind == "confirm_required" else None
