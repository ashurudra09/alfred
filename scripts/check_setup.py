"""Phase 0 gate: verify every tool, account and key Alfred needs. Read-only checks only.

Usage: uv run python scripts/check_setup.py   (exit code 1 if any required check fails)
"""

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

MIN_FREE_GB = 25
GATED = [  # (repo_id, repo_type) whose terms must be accepted on Hugging Face
    ("Salesforce/xlam-function-calling-60k", "dataset"),
    ("google/functiongemma-270m-it", "model"),
]


def run(cmd: list[str]) -> str:
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=ROOT)
    if out.returncode != 0:
        raise RuntimeError((out.stderr or out.stdout).strip().splitlines()[-1][:200])
    return out.stdout.strip()


def get_json(url: str, headers: dict | None = None) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "alfred-setup-check", **(headers or {})})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def key(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is empty in .env")
    return value


def check_git():
    return run(["git", "--version"])


def check_github_remote():
    run(["git", "ls-remote", "origin"])
    return run(["git", "remote", "get-url", "origin"])


def check_uv():
    return run(["uv", "--version"])


def check_ollama():
    return "Ollama " + get_json("http://127.0.0.1:11434/api/version")["version"]


def check_hf_token():
    from huggingface_hub import whoami

    info = whoami(token=key("HF_TOKEN"))
    role = info.get("auth", {}).get("accessToken", {}).get("role", "?")
    if role not in ("write", "fineGrained", "?"):
        raise RuntimeError(f"token role is '{role}', need a write token")
    return f"logged in as {info['name']} (token role: {role})"


def check_hf_gated():
    from huggingface_hub import auth_check

    for repo_id, repo_type in GATED:
        try:
            auth_check(repo_id, repo_type=repo_type, token=key("HF_TOKEN"))
        except Exception as e:
            raise RuntimeError(f"no access to {repo_id}: accept its terms on huggingface.co ({type(e).__name__})")
    return "access to " + ", ".join(r for r, _ in GATED)


def check_kaggle():
    if not (Path.home() / ".kaggle" / "access_token").exists() and not os.getenv("KAGGLE_API_TOKEN"):
        raise RuntimeError("no %USERPROFILE%\\.kaggle\\access_token")
    run(["kaggle", "datasets", "list", "--mine"])
    return "Kaggle API reachable with your token"


def check_groq():
    n = len(get_json("https://api.groq.com/openai/v1/models", {"Authorization": f"Bearer {key('GROQ_API_KEY')}"})["data"])
    return f"Groq key works ({n} models)"


def check_backup_teacher():
    endpoints = {
        "CEREBRAS_API_KEY": "https://api.cerebras.ai/v1/models",
        "OPENROUTER_API_KEY": "https://openrouter.ai/api/v1/key",
    }
    errors = []
    for name, url in endpoints.items():
        if not os.getenv(name, "").strip():
            continue
        try:
            get_json(url, {"Authorization": f"Bearer {key(name)}"})
            return f"{name.split('_')[0].title()} key works"
        except Exception as e:
            errors.append(f"{name}: {e}")
    raise RuntimeError("; ".join(errors) or "fill CEREBRAS_API_KEY or OPENROUTER_API_KEY")


def check_gemini():
    n = len(get_json("https://generativelanguage.googleapis.com/v1beta/models", {"x-goog-api-key": key("GEMINI_API_KEY")})["models"])
    return f"Gemini key works ({n} models)"


def check_disk():
    free_gb = shutil.disk_usage(ROOT).free / 1e9
    if free_gb < MIN_FREE_GB:
        raise RuntimeError(f"{free_gb:.0f} GB free, need {MIN_FREE_GB}")
    return f"{free_gb:.0f} GB free"


def check_node():
    return "Node " + run(["node", "--version"])


def check_claude_desktop():
    path = Path(os.getenv("APPDATA", "")) / "Claude"
    if not path.exists():
        raise RuntimeError(f"{path} not found")
    return "Claude Desktop installed"


REQUIRED = [check_git, check_github_remote, check_uv, check_ollama, check_hf_token, check_hf_gated,
            check_kaggle, check_groq, check_backup_teacher, check_disk]
OPTIONAL = [check_gemini, check_node, check_claude_desktop]


def main() -> int:
    failed = 0
    for checks, bad in ((REQUIRED, "FAIL"), (OPTIONAL, "WARN")):
        for check in checks:
            name = check.__name__.removeprefix("check_")
            try:
                print(f"[ OK ] {name:16} {check()}")
            except (Exception, urllib.error.URLError) as e:
                failed += bad == "FAIL"
                print(f"[{bad}] {name:16} {e}")
    print(f"\n{'All required checks passed.' if not failed else f'{failed} required check(s) failed.'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
