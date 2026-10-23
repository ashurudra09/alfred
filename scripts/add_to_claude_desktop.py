"""Register Alfred's MCP server with Claude Desktop. Run it while Claude Desktop is fully closed (it rewrites its
config while running and would undo the change):

    uv run python scripts/add_to_claude_desktop.py

Finds claude_desktop_config.json (classic path, Store-app path, or the moved Claude-Data folder), backs it up,
adds an "alfred" entry under "mcpServers" and leaves every other key as it was.
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UV = shutil.which("uv") or str(Path(os.environ["LOCALAPPDATA"]) / "Microsoft/WinGet/Links/uv.exe")
ENTRY = {"command": UV.replace("\\", "/"),
         "args": ["--directory", str(ROOT).replace("\\", "/"), "run", "python", "-m", "alfred.tools.server"]}


def candidates():
    local, roaming = Path(os.environ["LOCALAPPDATA"]), Path(os.environ["APPDATA"])
    yield from (local / "Claude-Data").glob("*/claude_desktop_config.json")
    yield roaming / "Claude" / "claude_desktop_config.json"
    yield from (local / "Packages").glob("Claude_*/LocalCache/Roaming/Claude/claude_desktop_config.json")


def claude_running() -> bool:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq claude.exe", "/NH"], capture_output=True, text=True).stdout
    return "claude.exe" in out.lower()


def main():
    if claude_running():
        sys.exit("Claude Desktop is still running. Quit it from the tray icon (right-click > Quit), then run this again.")
    path = next((p for p in candidates() if p.exists()), None)
    if path is None:
        sys.exit("No claude_desktop_config.json found. Open Claude Desktop > Settings > Developer > Edit Config once.")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    backup = path.with_name(f"claude_desktop_config.backup-{datetime.now():%Y%m%d-%H%M%S}.json")
    shutil.copy2(path, backup)
    cfg["mcpServers"] = {**cfg.get("mcpServers", {}), "alfred": ENTRY}
    path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    json.loads(path.read_text(encoding="utf-8"))  # still valid
    print(f"Added 'alfred' to {path}\nBackup: {backup}\nNow start Claude Desktop; Settings > Developer should show "
          f"alfred as running.")


if __name__ == "__main__":
    main()
