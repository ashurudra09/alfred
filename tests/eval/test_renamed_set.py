"""Track 4F (iii): the in-domain set with every tool and argument renamed, mapped back before scoring."""
import json

from alfred.agent.backends import RawCall
from alfred.contracts.export import load, openai_tools
from alfred.contracts.prompt import render_system_prompt
from alfred.contracts.schemas import Message
from eval.run import load_set, renamer
from eval.score import EVAL_DATE, EVAL_FOLDERS, score_item

TOOLS, SYSTEM = openai_tools(load("1.2")), render_system_prompt(EVAL_FOLDERS, EVAL_DATE, "1.2")
ITEMS = load_set("indomain")


def test_seed_0_is_the_plain_run():
    tools, system, same, back = renamer(TOOLS, SYSTEM, 0)
    assert tools == TOOLS and system == SYSTEM
    assert all(same(it.messages) == it.messages for it in ITEMS)


def test_renamed_names_map_back():
    tools, system, same, back = renamer(TOOLS, SYSTEM, 1)
    names = {t["function"]["name"] for t in TOOLS}
    assert not names & {t["function"]["name"] for t in tools}
    assert "move_to_recycle_bin" in SYSTEM and "move_to_recycle_bin" not in system
    for it in ITEMS:
        if it.expected_decision != "tool_call":
            continue
        # the gold calls written with the renamed names, as a model reading the renamed list would write them
        renamed = same([Message(role="assistant", content="", tool_calls=it.expected_calls)])[0].tool_calls
        assert {c.name for c in renamed}.isdisjoint(names)
        calls = [back(RawCall(c.name, c.arguments, json.dumps(c.arguments))) for c in renamed]
        out = {"content": "", "tool_calls": [{"name": n, "arguments": a} for n, a in calls]}
        assert score_item(it, out)["ok"], it.id
