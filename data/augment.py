"""Name masking for training examples (track 1C, step C1), after Hammer (Lin et al. 2024, arXiv 2410.04587).

Hammer replaces function names and parameter names in the candidate list with random strings and updates the
labels to match, so the model has to choose a tool from its description, not from a familiar name. This module
does the same for one Example, consistently everywhere a name appears:

- structure: the tool list (names, parameter keys, `required`), the assistant's calls (name, argument keys) and
  the `name` of tool-result messages;
- text (descriptions, system prompt, message contents): only names that look like identifiers (an underscore, a
  digit, a dot, a hyphen or camelCase), matched as whole tokens. That covers cross-references such as "use
  search_file_contents" and the prompt's `move_to_recycle_bin`. A name that is an ordinary word ("search",
  "query", "recall") is left alone in text: replacing it would damage sentences that use the word normally.

Not taken from the paper: Hammer also randomises default values and appends them to descriptions. The paper's
worked ratio is 0.33 of the instances in a batch (Section 5.5); it does not state the ratio of the released
models, and it reports that a large ratio slows learning of the in-domain task. RATES below follows that:
0.33 for the public datasets, less for Alfred's own tools, whose names the app really uses.

`mask` is deterministic per (seed, example id), and `unmask` restores the original byte for byte.
"""

import copy
import json
import random
import re
import string

from alfred.contracts.schemas import Example

RATES = {"xlam": 0.33, "when2call": 0.33}  # share of examples masked, by Example.source
ALFRED_RATE = 0.10  # every other source (synthetic, onpolicy, ...): Alfred's own tools
IDENT = re.compile(r"[_\d.\-]|[a-z][A-Z]")


def identifier_like(name: str) -> bool:
    return bool(IDENT.search(name))


def _random_name(rng: random.Random) -> str:
    """5-7 lowercase letters and digits, starting with a letter and always holding a digit (so it is identifier-like
    and `unmask` can find it in text). Short on purpose: random strings cost several tokens each, and an Alfred
    example carries about 55 names."""
    body = [rng.choice(string.ascii_lowercase + string.digits) for _ in range(rng.randint(3, 5))]
    return rng.choice(string.ascii_lowercase) + rng.choice(string.digits) + "".join(body)


def _text(s: str, names: dict[str, str]) -> str:
    """Replace identifier-like names in free text, whole tokens only, longest first."""
    keys = sorted((k for k in names if identifier_like(k)), key=len, reverse=True)
    if not keys or not s:
        return s
    pattern = r"(?<![A-Za-z0-9_])(" + "|".join(map(re.escape, keys)) + r")(?![A-Za-z0-9_])"
    return re.sub(pattern, lambda m: names[m.group(1)], s)


def rename(ex: Example, tools: dict[str, str], args: dict[str, str]) -> Example:
    """Apply a renaming (old -> new) of tool names and argument names to every part of the example."""
    both = {**args, **tools}  # in text a tool name wins if an argument shares it
    new_tools = copy.deepcopy(ex.tools)
    for t in new_tools:
        f = t["function"]
        f["name"] = tools.get(f["name"], f["name"])
        f["description"] = _text(f.get("description", ""), both)
        params = f.get("parameters") or {}
        if "properties" in params:
            params["properties"] = {args.get(k, k): v for k, v in params["properties"].items()}
            for p in params["properties"].values():
                if isinstance(p, dict) and isinstance(p.get("description"), str):
                    p["description"] = _text(p["description"], both)
        if "required" in params:
            params["required"] = [args.get(k, k) for k in params["required"]]
    messages = []
    for m in ex.messages:
        update = {"content": _text(m.content, both)}
        if m.tool_calls:
            update["tool_calls"] = [c.model_copy(update={"name": tools.get(c.name, c.name), "arguments": {
                args.get(k, k): v for k, v in c.arguments.items()}}) for c in m.tool_calls]
        if m.name:
            update["name"] = tools.get(m.name, m.name)
        messages.append(m.model_copy(update=update))
    return ex.model_copy(update={"tools": new_tools, "messages": messages})


def mask(ex: Example, seed: int = 0) -> tuple[Example, dict]:
    """The example with every tool name and argument name replaced by a random identifier, and the mapping
    {"tools": {old: new}, "args": {old: new}} that `unmask` needs."""
    rng = random.Random(f"{seed}:{ex.id}")
    blob = ex.model_dump_json()
    used: set[str] = set()

    def fresh() -> str:
        while True:
            n = _random_name(rng)
            if n not in used and n not in blob:
                used.add(n)
                return n

    tool_names = list(dict.fromkeys(t["function"]["name"] for t in ex.tools))
    arg_names = list(dict.fromkeys(k for t in ex.tools
                                   for k in (t["function"].get("parameters") or {}).get("properties", {})))
    mapping = {"tools": {n: fresh() for n in tool_names}, "args": {n: fresh() for n in arg_names}}
    return rename(ex, mapping["tools"], mapping["args"]), mapping


def unmask(ex: Example, mapping: dict) -> Example:
    return rename(ex, {v: k for k, v in mapping["tools"].items()}, {v: k for k, v in mapping["args"].items()})


def chosen(ex: Example, seed: int = 0) -> bool:
    """Whether this example is in the masked share for its source (stable per example, independent of order)."""
    return random.Random(f"pick:{seed}:{ex.id}").random() < RATES.get(ex.source, ALFRED_RATE)


def apply(examples: list[Example], seed: int = 0) -> tuple[list[Example], dict[str, dict]]:
    """Mask the chosen share of the examples. Returns the new list and {example id: mapping} for the masked ones."""
    out, mappings = [], {}
    for e in examples:
        if chosen(e, seed):
            e, mappings[e.id] = mask(e, seed)
        out.append(e)
    return out, mappings


def leaks(masked: Example, mapping: dict) -> list[str]:
    """Original names still present after masking: any name in a structural position, and identifier-like names
    anywhere in the text. Empty for a correct mask."""
    structural = {t["function"]["name"] for t in masked.tools}
    for t in masked.tools:
        params = t["function"].get("parameters") or {}
        structural |= set(params.get("properties", {})) | set(params.get("required", []))
    for m in masked.messages:
        structural |= {m.name} if m.name else set()
        for c in m.tool_calls or []:
            structural |= {c.name} | set(c.arguments)
    old_tools, old_args = set(mapping["tools"]), set(mapping["args"])
    out = sorted(structural & old_tools) + sorted(k for t in masked.tools for k in
                                                  (t["function"].get("parameters") or {}).get("properties", {})
                                                  if k in old_args)
    text = json.dumps([t["function"].get("description", "") for t in masked.tools]
                      + [p.get("description", "") for t in masked.tools
                         for p in (t["function"].get("parameters") or {}).get("properties", {}).values()
                         if isinstance(p, dict)]
                      + [m.content for m in masked.messages], ensure_ascii=False)
    out += [n for n in sorted(old_tools | old_args) if identifier_like(n)
            and re.search(r"(?<![A-Za-z0-9_])" + re.escape(n) + r"(?![A-Za-z0-9_])", text)]
    return out


def main(synthetic_path: str, n: int = 500):
    """Masking statistics on a sample in the mix's proportions (70% synthetic, 15% When2Call, 15% xLAM), every
    example masked: uv run python -m data.augment <synthetic.valid.jsonl>"""
    import statistics
    from pathlib import Path

    from transformers import AutoTokenizer

    from data.mix import MAX_TOKENS, render
    from data.sources import when2call, xlam

    rng = random.Random(0)
    synthetic = [Example.model_validate_json(line) for line in Path(synthetic_path).read_text(encoding="utf-8").splitlines()]
    sample = rng.sample(synthetic, round(n * 0.7)) + when2call(round(n * 0.15)) + xlam(round(n * 0.15))
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3.5-2B")
    by: dict[str, dict] = {}
    for ex in sample:
        masked, mapping = mask(ex)
        names = {**mapping["args"], **mapping["tools"]}
        text = " ".join(m.content for m in ex.messages) + " ".join(t["function"].get("description", "") for t in ex.tools)
        before, after = (len(tok(render(e, tok))["input_ids"]) for e in (ex, masked))
        s = by.setdefault(ex.source, {"n": 0, "leaks": 0, "roundtrip": 0, "names": [], "plain_in_text": 0, "extra": [],
                                      "over_before": 0, "over_after": 0})
        s["n"] += 1
        s["leaks"] += bool(leaks(masked, mapping))
        s["roundtrip"] += unmask(masked, mapping).model_dump_json() == ex.model_dump_json()
        s["names"].append(len(names))
        s["plain_in_text"] += any(not identifier_like(k) and re.search(rf"\b{re.escape(k)}\b", text) for k in names)
        s["extra"].append(after - before)
        s["over_before"] += before > MAX_TOKENS
        s["over_after"] += after > MAX_TOKENS
    for src, s in by.items():
        print(f"{src}: n={s['n']} leaks={s['leaks']} roundtrip_exact={s['roundtrip']} names/example median="
              f"{statistics.median(s['names'])} examples_with_a_plain-word_name_left_in_text={s['plain_in_text']} "
              f"extra_tokens median={statistics.median(s['extra'])} max={max(s['extra'])} "
              f"over_{MAX_TOKENS}: {s['over_before']} -> {s['over_after']}")


if __name__ == "__main__":
    import sys
    main(sys.argv[1])
