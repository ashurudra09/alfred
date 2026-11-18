"""Build the v4 SFT dataset (plan step 3.1): Alfred's examples (v3's synthetic set, the on-policy set, the
semantic-search and v4 injection batches) + When2Call + xLAM, contamination-filtered, stratified 95/5 split,
rendered with the Qwen3.5 chat template (tokenizer only, CPU).

Two outputs with the same rows: data/out/v4/mix_a/ (name masking, data/augment.py: run A) and data/out/v4/mix_b/
(no masking: run B). Every Alfred example carries the current 26-tool list; system prompt 1.2 as recorded.
Writes {train,val}.jsonl in each and data/stats.md. v3's mix (data/out/train.jsonl) is this file in git history.

Usage: uv run python -m data.mix          (needs Ollama running for the dedup embedder)
"""

import json
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

from alfred.agent.backends import ROOT, openai_messages
from alfred.contracts.export import openai_tools
from alfred.contracts.schemas import Example
from alfred.contracts.tools import REGISTRY
from data import augment
from data.v3 import is_hinglish

OUT = ROOT / "data" / "out"
HINGLISH_V4 = {s for s in (ROOT / "data" / "hinglish_v4.txt").read_text(encoding="utf-8").splitlines()
               if s and not s.startswith("#")}
MAX_TOKENS = 4096  # SFT sequence length
SHARE = {"when2call": 0.15, "xlam": 0.15}  # of the final mix; synthetic (in-domain + refusal/injection) is the rest
SEED = 3407
# Step 3.2: v3 trained 22,206,757 tokens in 33,078 s on a T4; the run stops at max_hours 10.5 (12 h session, export
# after). This budget is ~10.2 h of training at that rate.
BUDGET = 24_600_000
MIN_PER_TOOL = 220
ALFRED = ["synthetic.valid.jsonl", "v4/onpolicy.jsonl", "synthetic_search_by_meaning.valid.jsonl",
          "synthetic_injection_v4.valid.jsonl"]


def render(ex: Example, tok) -> str:
    sys_msg = ex.messages[0].content if ex.messages[0].role == "system" else None
    msgs = openai_messages(ex.messages[1:] if sys_msg else ex.messages, sys_msg)
    for m in msgs:  # the Qwen template wants arguments as a mapping, the OpenAI API wants a JSON string
        for c in m.get("tool_calls") or []:
            c["function"]["arguments"] = json.loads(c["function"]["arguments"])
    return tok.apply_chat_template(msgs, tools=ex.tools, tokenize=False, enable_thinking=False)


def ask_endings(examples: list[Example]) -> list[Example]:
    """Each clarify-then-call example again, cut right after the clarifying question.

    Qwen's template drops the empty <think></think> block from turns before the last user message, so in the full
    conversation the question is rendered without the prefix every inference-time reply starts with. SFT v1 trained
    on only those and almost stopped asking (decisions.md, Phase 5); here the question is the final turn."""
    out = []
    for e in examples:
        if e.category == "ask":
            cut = next(i for i, m in enumerate(e.messages) if m.role == "assistant" and not m.tool_calls)
        elif e.source == "onpolicy":  # ask_then_act: a question in the middle of a multi-step trajectory
            cut = next((i for i, m in enumerate(e.messages[:-1]) if m.role == "assistant" and not m.tool_calls
                        and m.content.rstrip().endswith("?") and e.messages[i + 1].role == "user"), None)
            if cut is None:
                continue
        else:
            continue
        out.append(e.model_copy(update={"id": e.id + "-q", "messages": e.messages[:cut + 1]}))
    return out


def unreserved(examples: list[Example]) -> tuple[list[Example], Counter]:
    """Drop what is reserved for evaluation (track 1C): examples that offer or call a held-out tool or a look-alike
    (unseen-tools eval), and examples whose text carries the marker of a test-only injection family (security eval).
    Returns the kept examples and the number dropped per reason."""
    from eval.security.families import test_only_hits
    from eval.unseen.specs import uses_held_out
    keep, why = [], Counter()
    for e in examples:
        if uses_held_out(e):
            why["held-out tool"] += 1
        elif test_only_hits(" ".join(m.content for m in e.messages)):
            why["test-only attack"] += 1
        else:
            keep.append(e)
    return keep, why


def fit(train: list[Example], tokens: dict[str, int]) -> tuple[list[Example], int]:
    """Step 3.2: drop single-call synthetic examples at random (v3 scores ~98% on single calls: the saturated part)
    until the train tokens fit BUDGET, never taking a tool's synthetic examples below MIN_PER_TOOL. New examples
    (on-policy, search_by_meaning) are never dropped."""
    calls = lambda e: [c.name for m in e.messages for c in m.tool_calls or []]
    total = sum(tokens[e.id] for e in train)
    per_tool = Counter(n for e in train if e.source == "synthetic" for n in set(calls(e)))
    pool = [e for e in train if e.source == "synthetic" and e.category == "tool_call" and len(calls(e)) == 1
            and calls(e)[0] != "search_by_meaning"]
    random.Random(SEED).shuffle(pool)
    out = set()
    for e in pool:
        if total <= BUDGET:
            break
        if per_tool[calls(e)[0]] > MIN_PER_TOOL:
            per_tool[calls(e)[0]] -= 1
            total -= tokens[e.id]
            out.add(e.id)
    assert total <= BUDGET, "the budget cannot be met by single-call examples alone"
    return [e for e in train if e.id not in out], len(out)


def split(examples: list[Example], val_frac: float = 0.05) -> tuple[list[Example], list[Example]]:
    groups = defaultdict(list)
    for e in examples:
        groups[(e.source, e.category)].append(e)
    rng, train, val = random.Random(SEED), [], []
    for key in sorted(groups):
        g = groups[key]
        rng.shuffle(g)
        k = max(1, round(len(g) * val_frac)) if len(g) >= 10 else 0
        val += g[:k]
        train += g[k:]
    rng.shuffle(train)
    return train, val


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from transformers import AutoTokenizer

    from data.dedup import Guard
    from data.sources import when2call, xlam

    synthetic, hinglish = [], 0
    tools = openai_tools()
    for name in ALFRED:
        for line in (OUT / name).read_text(encoding="utf-8").splitlines():
            e = Example.model_validate_json(line)
            if is_hinglish(e) or e.id in HINGLISH_V4:  # v3 heuristic + the ids it misses (data/hinglish_v4.txt)
                hinglish += 1
                continue
            synthetic.append(e.model_copy(update={"tools": tools}))
    synthetic += ask_endings(synthetic)
    total = round(len(synthetic) / (1 - sum(SHARE.values())))
    external = when2call(round(total * SHARE["when2call"])) + xlam(round(total * SHARE["xlam"]))
    synthetic, external, reserved = *map(unreserved, (synthetic, external)), Counter()
    for part in (synthetic, external):
        reserved.update(part[1])
    synthetic, external = synthetic[0], external[0]
    guard = Guard()
    kept, dropped = guard.filter(synthetic + external)
    assert not unreserved(kept)[1], "training data touches something reserved for evaluation"
    (OUT / "v4").mkdir(exist_ok=True)
    (OUT / "v4" / "dedup_dropped.json").write_text(json.dumps(sorted(dropped, key=lambda d: -d["cos"]), indent=1,
                                                              ensure_ascii=False), encoding="utf-8")

    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3.5-2B")
    masked = dict(zip((e.id for e in kept), augment.apply(kept, SEED)[0]))
    rows, too_long, mask_too_long = {}, 0, 0
    for e in kept:
        text = render(e, tok)
        n = len(tok(text)["input_ids"])
        if n > MAX_TOKENS:
            too_long += 1
            continue
        row = {"id": e.id, "source": e.source, "category": e.category, "n_tokens": n, "text": text, "masked": False}
        rows[e.id] = {"b": row, "a": row}
        if masked[e.id] is not e:  # this example is in the masked share
            mtext = render(masked[e.id], tok)
            mn = len(tok(mtext)["input_ids"])
            if mn > MAX_TOKENS:  # masking adds ~330 tokens to an Alfred example: keep it unmasked rather than drop it
                mask_too_long += 1
            else:
                rows[e.id]["a"] = row | {"n_tokens": mn, "text": mtext, "masked": True}
    final = [e for e in kept if e.id in rows]
    train, val = split(final)
    train, trimmed = fit(train, {k: v["a"]["n_tokens"] for k, v in rows.items()})
    for run in ("a", "b"):
        (OUT / "v4" / f"mix_{run}").mkdir(exist_ok=True)
        for name, part in (("train", train), ("val", val)):
            with (OUT / "v4" / f"mix_{run}" / f"{name}.jsonl").open("w", encoding="utf-8") as f:
                for e in part:
                    f.write(json.dumps(rows[e.id][run], ensure_ascii=False) + "\n")
    rows = {k: v["a"] for k, v in rows.items()}  # lengths below: run A's, the longer of the two

    lengths = [r["n_tokens"] for r in rows.values()]
    per_tool = Counter()
    for e in train:
        per_tool.update({c.name for m in e.messages for c in (m.tool_calls or []) if c.name in REGISTRY})
    by = Counter((e.source, e.category) for e in final)
    by_file = Counter(e.source for e in synthetic)
    lines = ["# Training data stats (v4)", "",
             f"Generated by `python -m data.mix` (seed {SEED}). v3's are in git history.", "",
             f"- Alfred examples: {len(synthetic)} (on-policy {by_file['onpolicy']}, the rest synthetic, ask endings "
             f"included); Hinglish dropped {hinglish}; When2Call: {sum(e.source == 'when2call' for e in external)}; "
             f"xLAM: {sum(e.source == 'xlam' for e in external)}",
             f"- Dropped as near-duplicates of test items: {len(dropped)} (cosine > 0.9 or a shared 8-gram); "
             f"dropped as longer than {MAX_TOKENS} tokens: {too_long}",
             f"- Name masking (run A only, data/augment.py): {sum(r['masked'] for r in rows.values())} examples "
             f"masked; {mask_too_long} chosen for masking left unmasked because the masked text is over "
             f"{MAX_TOKENS} tokens",
             f"- Dropped as reserved for evaluation: {reserved['held-out tool']} offering a held-out tool or a "
             f"look-alike (eval/unseen/specs.py), {reserved['test-only attack']} with the wording of a test-only "
             f"injection family (eval/security/families.py)",
             f"- Trimmed to fit the Kaggle session (step 3.2, `fit`): {trimmed} single-call synthetic examples "
             f"dropped at random from train (budget {BUDGET:,} tokens, no tool under {MIN_PER_TOOL})",
             f"- **Train {len(train)}, val {len(val)}**; total train tokens (run A) "
             f"{sum(rows[e.id]['n_tokens'] for e in train):,}", "",
             f"Tokens per example: median {statistics.median(lengths):.0f}, p95 "
             f"{sorted(lengths)[int(0.95 * len(lengths))]}, max {max(lengths)}", "",
             "| Source | Category | Examples | Share |", "|---|---|---|---|"]
    lines += [f"| {s} | {c} | {k} | {100 * k / len(final):.1f}% |" for (s, c), k in sorted(by.items())]
    lines += ["", "Examples per tool in train (synthetic, any call in the conversation; target ≥ 200):", "",
              "| Tool | Examples |", "|---|---|"]
    lines += [f"| {t} | {per_tool[t]}{' ⚠' if per_tool[t] < 200 else ''} |" for t in REGISTRY]
    (ROOT / "data" / "stats.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
