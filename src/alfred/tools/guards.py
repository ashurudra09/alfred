"""Guardrails every file tool goes through (requirements FR9, FR12-FR14).

- Known folders: the user's real Windows folders (OneDrive redirects included), plus extra folders from
  <home>/config.json, e.g. {"extra_folders": {"Projects": "D:\\projects"}}. Tests replace them all with
  {"folders": {...}}. They are the allow-list, and the same names appear in the system prompt.
- Sensitive paths are refused even inside allowed folders.
"""

import ctypes
import json
import os
import re
import uuid
from pathlib import Path

from mcp.server.fastmcp.exceptions import ToolError

KNOWN = {  # Windows known-folder GUIDs
    "Documents": "FDD39AD0-238F-46AF-ADB4-6C85480369C7", "Downloads": "374DE290-123F-4565-9164-39C4925E467B",
    "Desktop": "B4BFCC3A-DB2C-424C-B029-7FE99A87C641", "Pictures": "33E28130-4E1E-4676-835A-98395C3BC3BB",
    "Music": "4BD8D571-6D19-48D3-BE97-422220080E43", "Videos": "18989B1D-99B5-455B-841C-AB7C74E4DDFC",
}
SENSITIVE = re.compile(  # matched against each path part, case-insensitive
    r"^(\.ssh|\.gnupg|\.aws|\.azure|\.kube|\.docker|\.env.*|.*\.kdbx|.*\.kdb|.*\.pem|.*\.ppk|.*\.pfx|.*\.p12|"
    r"id_rsa.*|id_ed25519.*|id_ecdsa.*|\.git-credentials|\.netrc|\.npmrc|\.pypirc|credentials.*|"
    r"login data|cookies|web data|user data|local state|key[34]\.db|logins\.json|wallet\.dat|"
    r"protect|vault|.*password.*\.(csv|txt|xlsx?|json))$", re.I)
EXECUTABLE = {".exe", ".bat", ".cmd", ".com", ".ps1", ".psm1", ".vbs", ".vbe", ".js", ".jse", ".wsf", ".wsh",
              ".msi", ".msp", ".scr", ".lnk", ".url", ".hta", ".cpl", ".reg", ".jar", ".pif", ".appx", ".msix"}


def home() -> Path:
    """Alfred's own folder: notes, reminders, memory, journal, config."""
    h = Path(os.environ.get("ALFRED_HOME") or Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Alfred")
    h.mkdir(parents=True, exist_ok=True)
    return h


def _config() -> dict:
    p = home() / "config.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _windows_folder(guid: str) -> str | None:
    class GUID(ctypes.Structure):
        _fields_ = [("d1", ctypes.c_ulong), ("d2", ctypes.c_ushort), ("d3", ctypes.c_ushort), ("d4", ctypes.c_ubyte * 8)]

    u = uuid.UUID(guid)
    g = GUID(u.time_low, u.time_mid, u.time_hi_version, (ctypes.c_ubyte * 8)(*u.bytes[8:]))
    out = ctypes.c_wchar_p()
    try:
        if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(g), 0, None, ctypes.byref(out)) != 0:
            return None
        path = out.value
        ctypes.windll.ole32.CoTaskMemFree(out)
        return path
    except (AttributeError, OSError):
        return None


def known_folders() -> dict[str, str]:
    """Name -> path, in a stable order. These are the folders file tools may touch (plus Alfred's home)."""
    cfg = _config()
    if "folders" in cfg:
        folders = dict(cfg["folders"])
    else:
        folders = {n: p for n, g in KNOWN.items() if (p := _windows_folder(g)) and Path(p).is_dir()}
    folders.update(cfg.get("extra_folders", {}))
    return folders


def allowed_roots() -> list[Path]:
    return [Path(p).resolve() for p in known_folders().values()] + [home().resolve()]


def expand(path: str) -> Path:
    """'Downloads\\old' -> <Downloads>\\old; env vars and ~ expanded; relative paths are not allowed."""
    p = os.path.expandvars(os.path.expanduser(str(path).strip().strip('"').strip("'"))).replace("/", "\\")
    drive = re.fullmatch(r"(?:drive\s+)?([A-Za-z])(?::)?(?:\s+drive)?\\?", p, re.I)  # "C", "C drive", "drive C"
    if drive:
        p = drive.group(1).upper() + ":\\"
    elif p in ("\\", ""):  # "/" means the Windows drive
        p = os.environ.get("SystemDrive", "C:") + "\\"
    head, _, rest = p.partition("\\")
    for name, full in known_folders().items():
        if head.casefold() == name.casefold():
            p = full + ("\\" + rest if rest else "")
            break
    if re.fullmatch(r"[A-Za-z]:", p):
        p += "\\"
    path = Path(p)
    if not path.is_absolute():
        raise ToolError(f"Use a full path or a known folder name ({', '.join(known_folders())}): {path}")
    return path


def is_sensitive(path: Path) -> bool:
    return any(SENSITIVE.match(part) for part in path.parts)


def resolve_safe(path: str, must_exist: bool = True, any_location: bool = False) -> Path:
    """The real (junction-resolved) path, if it's allowed. `any_location` lifts the allow-list for read-only size
    checks (disk_usage on C:\\); the sensitive-path block always applies."""
    p = expand(path).resolve()
    if is_sensitive(p):
        raise ToolError(f"Refused: {p} is a sensitive location (keys, credentials or secrets).")
    if not any_location and not any(p == r or r in p.parents for r in allowed_roots()):
        raise ToolError(f"Refused: {p} is outside the allowed folders ({', '.join(known_folders())}).")
    if must_exist and not p.exists():
        raise ToolError(f"Not found: {p}")
    return p


def assert_no_overwrite(dst: Path):
    if dst.exists():
        raise ToolError(f"Refused: {dst} already exists, and Alfred never overwrites files.")


def is_executable(path: Path) -> bool:
    return path.suffix.casefold() in EXECUTABLE
