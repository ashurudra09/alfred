"""Phase 9a on Kaggle (2x T4): the BFCL v4 subset for base vs. SFT v2, both as Q8_0 GGUFs on llama.cpp (CUDA).

Pushed with: kaggle kernels push -p eval/bfcl/kernel
Inputs: alfred-adapters (the v2 LoRA adapter), alfred-bfcl-kit (eval/bfcl/run.py + qwen3.5-tokenizer/).
1. Unsloth converts base and base+adapter to Q8_0 the same way (the shipped GGUFs came from the same code).
2. llama.cpp (fresh clone) is built with CUDA; base serves on GPU 0 (:8080), SFT on GPU 1 (:8081).
3. Pinned bfcl-eval in its own venv generates and evaluates both in parallel through eval/bfcl/run.py.
Outputs: /kaggle/working/bfcl/{result,score}/<system>/...
"""

import glob
import os
import shutil
import subprocess
import sys
import time
import urllib.request

OUT, WORK = "/kaggle/working", "/tmp/alfred"  # big intermediates stay out of the output
T0 = time.time()
SYSTEMS = {"base-2b-q8": ("unsloth/Qwen3.5-2B", 0, 8080), "alfred-2b-v2-q8": ("adapter", 1, 8081)}


def log(msg):
    print(f"[{(time.time() - T0) / 60:.1f} min] {msg}", flush=True)


def export(system: str):
    """One model to Q8_0 GGUF (runs in its own process so GPU memory is freed after)."""
    import torch
    from unsloth import FastLanguageModel
    source = SYSTEMS[system][0]
    if source == "adapter":
        source = os.path.dirname(glob.glob("/kaggle/input/**/adapter_config.json", recursive=True)[0])
    model, tok = FastLanguageModel.from_pretrained(model_name=source, max_seq_length=4096, dtype=torch.float32,
                                                   load_in_4bit=False)
    model.save_pretrained_gguf(f"{WORK}/{system}", tok, quantization_method="q8_0")


def run(cmd, **kw):
    log("$ " + (cmd if isinstance(cmd, str) else " ".join(cmd)))
    subprocess.run(cmd, check=True, **kw)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        export(sys.argv[1])
        sys.exit()
    os.makedirs(WORK, exist_ok=True)
    run([sys.executable, "-m", "pip", "install", "-q", "unsloth"])
    ggufs = {}
    for system in SYSTEMS:
        run([sys.executable, __file__, system])
        ggufs[system] = max(glob.glob(f"{WORK}/{system}*/**/*.gguf", recursive=True), key=os.path.getsize)
        log(f"{system}: {ggufs[system]} {os.path.getsize(ggufs[system]) / 1e9:.2f} GB")

    src = f"{WORK}/llama.cpp"  # Unsloth's copy is prebuilt (no sources), so build our own
    run(["git", "clone", "-q", "--depth", "1", "--branch", "b11804", "https://github.com/ggml-org/llama.cpp", src])  # = the laptop's build
    run(["cmake", "-S", src, "-B", f"{WORK}/lcpp", "-DGGML_CUDA=ON", "-DCMAKE_CUDA_ARCHITECTURES=75",
         "-DLLAMA_CURL=OFF", "-DCMAKE_BUILD_TYPE=Release",
         "-DCMAKE_LIBRARY_PATH=/usr/local/nvidia/lib64"],  # where Kaggle keeps libcuda
        stdout=subprocess.DEVNULL)
    run(["cmake", "--build", f"{WORK}/lcpp", "--target", "llama-server", "-j", "4"], stdout=subprocess.DEVNULL)
    server = glob.glob(f"{WORK}/lcpp/**/llama-server", recursive=True)[0]

    servers = []
    for system, (_, gpu, port) in SYSTEMS.items():
        servers.append(subprocess.Popen(
            [server, "-m", ggufs[system], "-ngl", "99", "-c", "32768", "-np", "8", "--port", str(port)],
            env={**os.environ, "CUDA_VISIBLE_DEVICES": str(gpu)}, stdout=open(f"{OUT}/server_{system}.log", "w"),
            stderr=subprocess.STDOUT))
    for _, _, port in SYSTEMS.values():
        for _ in range(300):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2)
                break
            except OSError:
                time.sleep(2)
    log("servers up")

    venv = f"{WORK}/bfclenv"
    run([sys.executable, "-m", "pip", "install", "-q", "uv"])  # Kaggle's Python 3.13 has no ensurepip
    run(["uv", "venv", "-q", "--python", "3.12", venv])  # bfcl-eval pins numpy 1.26.4: no 3.13 wheels
    run(["uv", "pip", "install", "-q", "--python", f"{venv}/bin/python", "bfcl-eval==2026.3.23", "soundfile"])
    kit = os.path.dirname(glob.glob("/kaggle/input/**/run.py", recursive=True)[0])
    shutil.copytree(kit, f"{WORK}/kit")  # the dataset mount is read-only
    env = {**os.environ, "BFCL_PROJECT_ROOT": f"{OUT}/bfcl", "BFCL_THREADS": "8", "PYTHONIOENCODING": "utf-8"}
    gens = [subprocess.Popen([f"{venv}/bin/python", f"{WORK}/kit/run.py", "generate", system],
                             env={**env, "LOCAL_SERVER_PORT": str(port)}) for system, (_, _, port) in SYSTEMS.items()]
    log(f"generate exit codes {[g.wait() for g in gens]}")
    for system in SYSTEMS:
        run([f"{venv}/bin/python", f"{WORK}/kit/run.py", "evaluate", system], env=env)
    for s in servers:
        s.terminate()
    log("done")
