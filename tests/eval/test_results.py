import json

from eval import results

NAMES = ["direct", "tool_call", "request_for_info", "cannot_answer"]


def row(gold, lls, lens=(10, 10, 10, 10), no_tools=False):
    return {"uuid": "u", "gold": gold, "names": NAMES, "no_tools": no_tools, "lls": list(lls), "lens": list(lens)}


def test_when2call_metrics(tmp_path, monkeypatch):
    monkeypatch.setattr(results, "REPORTS", tmp_path)
    rows = [row(1, (-9, -1, -9, -9)),  # right
            row(0, (-5, -9, -9, -9)),  # right
            row(3, (-9, -2, -9, -3), no_tools=True),  # wrong: a tool call with no tools = hallucination
            row(2, (-9, -9, -4, -1), lens=(10, 10, 100, 1))]  # wrong raw, right once normalised by length
    (tmp_path / "when2call_x.json").write_text(json.dumps(rows))
    m = results.when2call("x")
    assert m["n"] == 4 and m["acc"] == 0.5 and m["acc_norm"] == 0.75
    assert m["hallucination"] == 1.0
    # per-class F1 from the raw prediction: direct 1, tool_call 2/3, request 0, cannot 0 -> mean 5/12
    assert abs(m["macro_f1"] - 5 / 12) < 1e-9
    assert results.when2call("missing") is None


def test_wilson():
    lo, hi = results.wilson(265, 278)  # SFT v2 Q4 in-domain; reference values from statsmodels proportion_confint
    assert abs(lo - 0.9223) < 1e-3 and abs(hi - 0.9725) < 1e-3
    assert results.wilson(0, 10)[0] == 0.0 and results.wilson(10, 10)[1] > 0.9999
    assert results.wilson(0, 0) == (0.0, 1.0)


def test_mcnemar():
    # only-a = 3, only-b = 0: p = 2 * (1/2)^3 = 0.25; ties (both right / both wrong) are ignored
    a = [True, True, True, True, False]
    b = [False, False, False, True, False]
    assert results.mcnemar(a, b) == (3, 0, 0.25)
    assert results.mcnemar([True], [True]) == (0, 0, 1.0)
    assert results.mcnemar([True, False], [False, True])[2] == 1.0  # one each way -> capped at 1


def test_text_agreement():
    from eval.review import text_agreement
    a = text_agreement([{"human": "ask", "scorer": "ask"}, {"human": "ask", "scorer": "direct"},
                        {"human": "refuse", "scorer": "refuse"}])
    assert a["n"] == 3 and a["agree"] == 2
    assert a["per_class"]["ask"] == {"n": 2, "agree": 1} and a["per_class"]["cannot"] == {"n": 0, "agree": 0}


def test_look_first():
    items = [{"ok": False, "label": "list_directory", "expected_label": "move_file"},  # counts
             {"ok": False, "label": "search_files", "expected_label": "git_status"},  # read-only expected: no
             {"ok": True, "label": "list_directory", "expected_label": "list_directory"}]
    assert results.look_first(items) == items[:1]
