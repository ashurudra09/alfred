"""Hard suite (v4 track 1A): the generator is deterministic and leak-free; the checkers are validated with no model."""

import pytest

from alfred.agent import loop
from alfred.tools import memory
from data.dedup import ngrams
from eval.e2e import hard
from eval.e2e.__main__ import run_task

TEST, TRAIN = hard.tasks("test"), hard.tasks("train", 20)



def test_same_seed_same_fixture():
    assert hard.frozen_text() == hard.frozen_text()
    # the committed test file is what the generator produces; after an intended change: python -m eval.e2e.hard --write
    assert hard.FROZEN.read_text(encoding="utf-8") == hard.frozen_text()


def test_pools_share_nothing():
    held = {f.__name__ for f in hard.HELD_OUT}
    assert len(TEST) == 149 and sum('new_capability' not in t.tags for t in TEST) == 124 and held <= {t.family for t in TEST} and not held & {t.family for t in TRAIN}
    assert not {t.seed for t in TEST} & {t.seed for t in TRAIN}
    names = lambda ts: {part.casefold() for t in ts for f in t.files for part in f.split("/")[1:]}
    assert not names(TEST) & names(TRAIN)  # file and subfolder names
    said = lambda ts: {s.text for t in ts for s in t.steps}
    assert not said(TEST) & said(TRAIN)
    assert not set().union(*map(ngrams, said(TEST))) & set().union(*map(ngrams, said(TRAIN)))  # the dedup guard's rule


def test_facts():
    assert hard.has_fact("It comes to 16,350.50 in total.", 16350.5) and hard.has_fact("535KB together", (535, 0.52))
    assert not hard.has_fact("see lease_2024.pdf, due 2026-11-20", 2024) and not hard.has_fact("due 2026-11-20", 11)
    assert hard.has_fact("It's called Maple_Notes.md", "maple_notes.md") and not hard.has_fact("4 files", 5)


@pytest.fixture
def run(tmp_path, monkeypatch):
    for k in ("ALFRED_HOME", "ALFRED_NO_LAUNCH", "ALFRED_TODAY", "ALFRED_TRASH", "ALFRED_EMBED_CACHE"):
        monkeypatch.setenv(k, "")  # run_task sets these; registering them here restores them afterwards
    monkeypatch.setattr(loop, "log_turn", lambda rec: None)
    monkeypatch.setattr(memory, "embed_many", lambda *a, **k: 1 / 0)  # keyword recall and search: no Ollama needed
    return lambda t, mode: run_task(t, hard.Scripted(t.script(mode)), tmp_path, scripted=True)


def test_oracle_passes(run):
    for t in TEST + TRAIN[::7]:
        r = run(t, "oracle")
        assert r["ok"] and not any(r["invariants"].values()), (t.id, r["reason"], r["invariants"])
        assert 1 <= t.n_calls <= 5 and len(r["calls"]) == t.n_calls


@pytest.mark.parametrize("mode", ["null", "wrong", "extra"])
def test_bad_agents_fail(run, mode):
    """null does nothing, wrong leaves the job half done or acts where it should ask, extra adds an unrequested delete."""
    for t in TEST:
        if t.seed < 4:  # every variant of every family; all 124 run with: python -m eval.e2e --suite hard --system <mode>
            assert not run(t, mode)["ok"], t.id
