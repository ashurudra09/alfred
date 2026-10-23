"""BFCL v4 subset (Phase 9a) for Qwen3.5 models served by llama-server, run in eval/bfcl/.venv (pinned bfcl-eval).

bfcl-eval 2026.3.23 has no Qwen3.5 handler, so this registers one: BFCL's Qwen3 FC handler, but the prompt is the
model's own Qwen3.5 chat template (tools, non-thinking) and tool calls are read from Qwen3.5's XML format
(<tool_call><function=f><parameter=p>value</parameter></function></tool_call>), each value typed by the function's
schema as vLLM's qwen3_coder parser does, then rewritten as the JSON calls BFCL's Qwen decoder reads.
The model is whatever llama-server serves on 127.0.0.1:$LOCAL_SERVER_PORT (default 8080; start it first).
On Kaggle (2x T4, llama.cpp CUDA) it runs via kernel/bfcl_kernel.py; locally the CPU takes ~6 h per model.

Setup: uv venv .venv --python 3.12 && uv pip install bfcl-eval==2026.3.23 soundfile; qwen3.5-tokenizer/ = the
tokenizer files + chat_template.jinja from runs/sft_2b_v2/alfred-2b-lora and config.json from unsloth/Qwen3.5-2B.

    .venv/Scripts/python run.py generate alfred-2b-v2-q8
    .venv/Scripts/python run.py evaluate alfred-2b-v2-q8
"""

import ast
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault("BFCL_PROJECT_ROOT", str(HERE))  # result/ and score/ live here
os.environ.setdefault("LOCAL_SERVER_ENDPOINT", "127.0.0.1")
os.environ.setdefault("LOCAL_SERVER_PORT", "8080")

from bfcl_eval.constants import model_config  # noqa: E402
from bfcl_eval.model_handler.local_inference.qwen_fc import QwenFCHandler  # noqa: E402
from overrides import override  # noqa: E402

CATEGORIES = "simple_python,multiple,parallel,irrelevance,live_relevance"
SYSTEMS = ("base-2b-q8", "alfred-2b-v2-q8")  # names match eval/reports
TOKENIZER = HERE / "qwen3.5-tokenizer"  # the training tokenizer + chat template, and the base config.json

XML_CALL = re.compile(r"<tool_call>\s*<function=([\w.-]+)>(.*?)</function>\s*</tool_call>", re.S)
XML_PARAM = re.compile(r"<parameter=([\w.-]+)>\n?(.*?)\n?</parameter>", re.S)


def typed(value: str, prop: dict):
    """A parameter's text as the type its schema declares, like vLLM's qwen3_coder tool parser (Qwen3.5's)."""
    kind = str(prop.get("type", "")).lower()
    try:
        if kind in ("string", "str", "text", "enum"):
            return value
        if kind in ("integer", "int"):
            return int(value)
        if kind in ("number", "float", "double"):
            f = float(value)
            return f if "." in value or "e" in value.lower() else int(f)
        if kind in ("boolean", "bool"):
            return value.strip().lower() == "true"
    except ValueError:
        return value
    try:  # dict, array, tuple, any, or no schema
        return json.loads(value)
    except ValueError:
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return value


def xml_to_json_calls(text: str, functions: list[dict]) -> str:
    """Rewrite Qwen3.5 XML calls as the JSON <tool_call> blocks BFCL's Qwen handler decodes."""
    props = {f["name"]: f.get("parameters", {}).get("properties", {}) for f in functions}

    def one(m):
        name, body = m.groups()
        args = {k: typed(v, props.get(name, {}).get(k, {})) for k, v in XML_PARAM.findall(body)}
        return "<tool_call>\n" + json.dumps({"name": name, "arguments": args}) + "\n</tool_call>"
    return XML_CALL.sub(one, text)


class Qwen35FCHandler(QwenFCHandler):
    @override
    def _format_prompt(self, messages, function):
        return self.tokenizer.apply_chat_template(messages, tools=function or None, add_generation_prompt=True,
                                                  enable_thinking=False, tokenize=False)

    @override
    def _query_prompting(self, inference_data: dict):
        response, latency = super()._query_prompting(inference_data)
        response.choices[0].text = xml_to_json_calls(response.choices[0].text, inference_data["function"])
        return response, latency


for name in SYSTEMS:
    model_config.MODEL_CONFIG_MAPPING[name] = model_config.ModelConfig(
        model_name=str(TOKENIZER), display_name=name, url="https://huggingface.co/Qwen/Qwen3.5-2B", org="Qwen",
        license="apache-2.0", model_handler=Qwen35FCHandler, input_price=None, output_price=None, is_fc_model=True,
        underscore_to_dot=False)

if __name__ == "__main__":
    from bfcl_eval.__main__ import cli

    step, system = sys.argv[1], sys.argv[2]
    args = [step, "--model", system, "--test-category", CATEGORIES]
    if step == "generate":
        args += ["--skip-server-setup", "--local-model-path", str(TOKENIZER),
                 "--num-threads", os.environ.get("BFCL_THREADS", "4")]
    cli(args)
