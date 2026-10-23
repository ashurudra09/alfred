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
