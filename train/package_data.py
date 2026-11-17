"""Build data/out/kaggle/ (the private Kaggle dataset alfred-sft-data) and upload it.

Usage: uv run python -m train.package_data [--mix a|b] [--upload]   (first upload creates the dataset, later ones
add a version). --mix a|b packages v4's data/out/v4/mix_<a|b>/ with train/configs/sft_2b_v4.yaml (copied under the
name the kernel reads, sft_2b.yaml); without it, v3's data/out/{train,val}.jsonl and sft_2b.yaml.
"""

import json
import shutil
import subprocess
import sys
from datetime import date

from alfred.agent.backends import ROOT
from alfred.contracts.export import openai_tools
from alfred.contracts.prompt import render_system_prompt
from eval.score import EVAL_FOLDERS

SRC, DST = ROOT / "data" / "out", ROOT / "data" / "out" / "kaggle"
SLUG = "ashurudra09/alfred-sft-data"


def main():
    mix = sys.argv[sys.argv.index("--mix") + 1] if "--mix" in sys.argv else None
    src, config = (SRC / "v4" / f"mix_{mix}", "sft_2b_v4.yaml") if mix else (SRC, "sft_2b.yaml")
    DST.mkdir(parents=True, exist_ok=True)
    for name in ("train", "val"):
        with (src / f"{name}.jsonl").open(encoding="utf-8") as f, (DST / f"{name}.jsonl").open("w", encoding="utf-8") as g:
            for line in f:
                r = json.loads(line)
                g.write(json.dumps({"id": r["id"], "text": r["text"]}, ensure_ascii=False) + "\n")
    shutil.copy(ROOT / "train" / "configs" / config, DST / "sft_2b.yaml")
    kit = {"system": render_system_prompt(EVAL_FOLDERS, date(2026, 10, 22)), "tools": openai_tools()}
    (DST / "prompt_kit.json").write_text(json.dumps(kit, ensure_ascii=False, indent=1), encoding="utf-8")
    (DST / "dataset-metadata.json").write_text(json.dumps(
        {"title": "alfred-sft-data", "id": SLUG, "licenses": [{"name": "CC-BY-4.0"}]}, indent=1), encoding="utf-8")
    print("packaged", src, config, sorted(p.name for p in DST.iterdir()))
    if "--upload" in sys.argv:
        exists = subprocess.run(["kaggle", "datasets", "status", SLUG], capture_output=True, text=True).returncode == 0
        cmd = (["kaggle", "datasets", "version", "-p", str(DST), "-m", f"{'v4 mix ' + mix if mix else 'update'} {date.today()}"] if exists
               else ["kaggle", "datasets", "create", "-p", str(DST)])
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
