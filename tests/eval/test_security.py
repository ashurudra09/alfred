"""Security suite (track 4E, step E4): every injection reaches the model whole through the real tool, and the
checker scores an agent that obeys at 100% attack success and one that ignores at 0%."""

import pytest

from alfred.agent import loop
from alfred.agent.backends import wrap_tool_output
from alfred.tools import memory
from eval.e2e.__main__ import run_task
from eval.e2e.hard import Scripted
from eval.security.suite import GOALS, as_name, cases, injection, script

CASES = cases()


def flat(s: str) -> str:
    return " ".join(s.split())


@pytest.fixture(autouse=True)
def keyword_recall(monkeypatch):
    for k in ("ALFRED_HOME", "ALFRED_NO_LAUNCH", "ALFRED_TODAY", "ALFRED_TRASH", "ALFRED_EMBED_CACHE"):
        monkeypatch.setenv(k, "")  # run_task sets these; registering them here restores them afterwards
    monkeypatch.setattr(loop, "log_turn", lambda rec: None)
    monkeypatch.setattr(memory, "embed_many", lambda *a, **k: 1 / 0)


def run(case, agent, tmp_path):
    r = run_task(case, Scripted(script(case, agent)), tmp_path, {}, scripted=True, root=tmp_path / "c")
    return r, case.result


def test_suite_shape():
    att = [c for c in CASES if c.goal]
    assert len(att) >= 200 and len({c.id for c in CASES}) == len(CASES)
    assert {c.goal for c in att} == set(GOALS) and {c.family for c in att if c.vector == "file_text"} >= {
        "important_instructions", "tool_knowledge", "fake_user_turn"}


@pytest.mark.parametrize("case", [c for c in CASES if c.goal], ids=lambda c: c.id)
def test_injection_reaches_the_model_whole(case, tmp_path):
    r, res = run(case, "ignore", tmp_path)
    shown = flat(next(m["content"] for m in r["trajectory"][0]["messages"] if m["role"] == "tool"))
    inj = injection(case.family, case.goal)
    want = as_name(inj) if case.vector in ("file_name", "git_output") else flat(inj)
    sent = wrap_tool_output(shown)  # what the model gets: the wrapper still ends once, no chat turn opens
    assert want in shown and sent.count("</tool_output>") == 1 and "<|im_start|>" not in sent
    assert res["utility"] and not res["attack_model"] and not res["attack_exec_all"]


@pytest.mark.parametrize("case", [c for c in CASES if c.goal][::7], ids=lambda c: c.id)
def test_obeying_agent_is_caught(case, tmp_path):
    _, res = run(case, "obey", tmp_path)
    assert res["attack_model"]
    confirm = GOALS[case.goal][3]
    assert res["attack_exec_all"] == (case.goal != "open_program")  # open_path refuses programs
    assert res["attack_exec_none"] == (not confirm and case.goal != "open_program")
