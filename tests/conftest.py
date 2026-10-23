import hashlib
import json

import pytest


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Known folders + Alfred's home inside tmp_path, with a few files. Returns the folder map."""
    home = tmp_path / "home"
    home.mkdir()
    folders = {n: tmp_path / n for n in ("Documents", "Downloads", "Desktop")}
    for p in folders.values():
        p.mkdir()
    (home / "config.json").write_text(json.dumps({"folders": {n: str(p) for n, p in folders.items()}}))
    monkeypatch.setenv("ALFRED_HOME", str(home))
    d = folders["Downloads"]
    (d / "attention_transformer.pdf").write_bytes(b"%PDF-1.4 fake")
    (d / "notes.txt").write_text("LoRA adds low-rank adapters. Try r=16.")
    (d / "budget.xlsx").write_bytes(bytes([0x50, 0x4B, 3, 4, 20, 0, 0, 0]) + b" xlsx")  # a zip: binary
    (d / "photo.jpg").write_bytes(b"jpg")
    (d / "setup.exe").write_bytes(b"MZ")
    (d / "photos").mkdir()
    (d / "photos" / "a.jpg").write_bytes(b"a")
    (folders["Documents"] / "resume").mkdir()
    (folders["Documents"] / "resume" / "cv.md").write_text("# CV")
    (folders["Documents"] / ".env").write_text("API_KEY=secret")
    (folders["Documents"] / ".ssh").mkdir()
    (folders["Documents"] / ".ssh" / "id_rsa").write_text("PRIVATE")
    (tmp_path / "outside").mkdir()
    (tmp_path / "outside" / "x.txt").write_text("outside")
    return {**folders, "home": home, "root": tmp_path}


def snapshot(*roots):
    """{relative path: content hash} for every file under the roots (dirs as None)."""
    out = {}
    for root in roots:
        for p in sorted(root.rglob("*")):
            out[str(p)] = hashlib.sha1(p.read_bytes()).hexdigest() if p.is_file() else None
    return out
