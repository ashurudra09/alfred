"""File tools (contracts 1-12). Results follow data/gen/formats.py, the format the model was trained on.
Every write goes through guards, never overwrites, and is recorded in the journal for /undo.
"""

import ctypes
import fnmatch
import os
import re
import shutil
import time
import zipfile
from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp.exceptions import ToolError
from send2trash import send2trash

from alfred.tools import journal
from alfred.tools.guards import allowed_roots, assert_no_overwrite, is_executable, is_sensitive, resolve_safe

MAX_RESULTS, MAX_SCAN = 50, 20000
MAX_READ = 2_000_000  # bytes read from one text file
SKIP_ORGANIZE = {".lnk", ".url", ".ini", ".sys", ".tmp", ".crdownload", ".part"}  # shortcuts, system, in-progress
TEXT_EXT = {".txt", ".md", ".py", ".js", ".ts", ".json", ".csv", ".html", ".css", ".java", ".c", ".cpp", ".h", ".cs",
            ".go", ".rs", ".rb", ".sql", ".yaml", ".yml", ".toml", ".ini", ".log", ".xml", ".tex", ".ipynb", ".sh"}
TYPES = {"PDFs": {".pdf"}, "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic", ".svg"},
         "Documents": {".doc", ".docx", ".odt", ".rtf", ".txt", ".md"}, "Spreadsheets": {".xls", ".xlsx", ".csv", ".ods"},
         "Presentations": {".ppt", ".pptx", ".odp"}, "Archives": {".zip", ".rar", ".7z", ".tar", ".gz"},
         "Installers": {".exe", ".msi", ".msix", ".appx"}, "Audio": {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"},
         "Video": {".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv"},
         "Code": {".py", ".js", ".ts", ".java", ".c", ".cpp", ".cs", ".go", ".rs", ".ipynb", ".html", ".css"}}


def size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit in ("B", "KB") else f"{n:.1f} {unit}"
        n /= 1024


def walk(root: Path):
    """Files under root, skipping sensitive and hidden folders, at most MAX_SCAN."""
    n = 0
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if not x.startswith((".", "$")) and not is_sensitive(Path(x))]
        for f in files:
            p = Path(d) / f
            if is_sensitive(p):
                continue
            n += 1
            if n > MAX_SCAN:
                return
            yield p


def listing(header: str, lines: list[str], noun: str = "file") -> str:
    if not lines:
        return f"No matching {noun}s found."
    more = f"\n... and {len(lines) - MAX_RESULTS} more" if len(lines) > MAX_RESULTS else ""
    return f"{len(lines)} {noun}{'s' if len(lines) != 1 else ''}{header}:\n" + "\n".join(lines[:MAX_RESULTS]) + more


def _ext(extension) -> str | None:
    e = (extension or "").strip().lstrip("*").lstrip(".").lower()
    return "." + e if e else None


def name_matcher(query: str):
    """Wildcards ('*.pdf') use glob rules; otherwise every word must appear in the name ('transformer paper'
    matches transformer_paper.pdf). An empty query or '*' matches everything."""
    q = query.strip().casefold()
    if q in ("", "*", "*.*"):
        return lambda name: True
    if any(c in q for c in "*?"):
        return lambda name: fnmatch.fnmatch(name.casefold(), q)
    words = re.findall(r"[^\W_]+", q)
    return lambda name: all(w in re.sub(r"[\W_]+", " ", name.casefold()) for w in words)


def search_files(query, folder, extension=None, modified_within_days=None):
    root = resolve_safe(folder)
    match, ext = name_matcher(query), _ext(extension)
    since = time.time() - modified_within_days * 86400 if modified_within_days else None
    hits = []
    for p in walk(root):
        if match(p.name) and (not ext or p.suffix.lower() == ext):
            st = p.stat()
            if since is None or st.st_mtime >= since:
                hits.append((st.st_mtime, f"{p} ({size(st.st_size)}, modified "
                                          f"{datetime.fromtimestamp(st.st_mtime):%Y-%m-%d})"))
    return listing("", [h for _, h in sorted(hits, reverse=True)])


def _pdf_text(p: Path, max_pages: int = 30) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(p))
    return "\n".join((page.extract_text() or "") for page in reader.pages[:max_pages])


def _docx_text(p: Path) -> str:
    with zipfile.ZipFile(p) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="replace")
    return re.sub(r"<[^>]+>", "", re.sub(r"</w:p>", "\n", xml)).strip()


def _text(p: Path) -> str:
    suf = p.suffix.lower()
    if suf == ".pdf":
        return _pdf_text(p)
    if suf == ".docx":
        return _docx_text(p)
    with p.open("rb") as f:
        raw = f.read(MAX_READ)
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8-sig", errors="replace")


def is_text(p: Path) -> bool:
    """Known text/document types, or any file whose first 8 KB has no NUL bytes (README, LICENSE, ...)."""
    if p.suffix.lower() in TEXT_EXT | {".pdf", ".docx"}:
        return True
    with p.open("rb") as f:
        head = f.read(8192)
    return b"\x00" not in head or head.startswith((b"\xff\xfe", b"\xfe\xff"))


def search_file_contents(text, folder, extension=None):
    root, needle = resolve_safe(folder), text.casefold()
    ext = _ext(extension)
    hits = []
    for p in walk(root):
        suf = p.suffix.lower()
        if (ext and suf != ext) or (suf not in TEXT_EXT | {".pdf", ".docx"}) or p.stat().st_size > 5_000_000:
            continue
        try:
            body = _text(p)
        except Exception:
            continue
        i = body.casefold().find(needle)
        if i >= 0:
            snippet = " ".join(body[max(0, i - 40): i + len(text) + 40].split())
            hits.append(f'{p}: "...{snippet}..."')
    return listing("", hits)


def list_directory(path):
    p = resolve_safe(path)
    if not p.is_dir():
        raise ToolError(f"Not a folder: {p}")
    items = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.casefold()))
    lines = [f"{x.name}\\ (folder)" if x.is_dir() else f"{x.name} ({size(x.stat().st_size)})"
             for x in items if not is_sensitive(x)]
    more = f"\n... and {len(lines) - 200} more" if len(lines) > 200 else ""
    return f"{p} ({len(lines)} items):\n" + ("\n".join(lines[:200]) or "(empty)") + more


def read_file(path, max_chars=4000):
    p = resolve_safe(path)
    if not p.is_file():
        raise ToolError(f"Not a file: {p}")
    if not is_text(p):
        raise ToolError(f"Can't read {p.suffix or 'this'} files: only text, code, PDF and Word (.docx) files.")
    try:
        body = _text(p)
    except Exception as e:
        raise ToolError(f"Couldn't read {p.name}: {e}")
    if not body.strip():
        return f"{p}: no text found" + (" (it may be a scanned PDF with only images)." if p.suffix.lower() == ".pdf"
                                        else ".")
    more = f"\n... ({len(body) - max_chars} more chars)" if len(body) > max_chars else ""
    return f"{p} ({len(body):,} chars):\n{body[:max_chars]}{more}"


def _tree_size(p: Path, deadline: float) -> tuple[int, bool]:
    """Bytes under p; False if the time budget ran out (the number is then a lower bound)."""
    total, stack = 0, [p]
    while stack:
        if time.monotonic() > deadline:
            return total, False
        try:
            with os.scandir(stack.pop()) as it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=False):
                            stack.append(e.path)
                        else:
                            total += e.stat(follow_symlinks=False).st_size
                    except OSError:
                        pass
        except OSError:
            pass
    return total, True


def disk_usage(path, top_n=10):
    # ponytail: walks each child folder within a 20 s budget; sizes past it are shown as "≥". An index (e.g. the
    # MFT) would be exact and fast if this is ever too slow.
    p = resolve_safe(path, any_location=True)
    du = shutil.disk_usage(p)
    head = f"{p.anchor} {size(du.total)} total, {size(du.free)} free." if p == Path(p.anchor) else \
        f"{p}: drive {p.anchor} has {size(du.free)} free of {size(du.total)}."
    if not p.is_dir():
        return f"{head}\n{p} is {size(p.stat().st_size)}."
    deadline, sizes = time.monotonic() + 20, []
    for e in sorted(p.iterdir(), key=lambda x: x.name.casefold()):
        if is_sensitive(e) or e.name.startswith("$"):
            continue
        try:
            n, exact = _tree_size(e, deadline) if e.is_dir() else (e.stat().st_size, True)
        except OSError:
            continue
        sizes.append((n, f"{e} {'' if exact else '≥ '}{size(n)}"))
    lines = [s for _, s in sorted(sizes, reverse=True)[:top_n]]
    return head + "\nLargest:\n" + "\n".join(lines)


def _target(src: Path, destination: str) -> Path:
    """A folder destination keeps the name; otherwise destination is the full new path. A missing destination
    without an extension, for a file that has one, is a folder that doesn't exist (not a new file name)."""
    d = resolve_safe(destination, must_exist=False)
    if d.is_dir():
        return d / src.name
    if src.is_file() and src.suffix and not d.suffix:
        raise ToolError(f"Folder not found: {d}. Create it first, or give the full new file name.")
    return d


def _os(action: str, fn, *args):
    """Run a filesystem call; turn OS errors (file in use, access denied) into a clear tool error."""
    try:
        return fn(*args)
    except OSError as e:
        raise ToolError(f"Couldn't {action}: {e.strerror or e}")


def move_file(source, destination):
    src = resolve_safe(source)
    dst = _target(src, destination)
    assert_no_overwrite(dst)
    if not dst.parent.exists():
        raise ToolError(f"Folder not found: {dst.parent}")
    _os(f"move {src.name}", shutil.move, str(src), str(dst))
    journal.record("move_file", "move", src, dst)
    return f"Moved {src} to {dst}. Undo: /undo"


def _rename_target(path, new_name) -> tuple[Path, Path]:
    new_name = new_name.strip().rstrip(". ")
    if any(c in new_name for c in '\\/:*?"<>|') or not new_name:
        raise ToolError("new_name must be a file name only, without a folder.")
    src = resolve_safe(path)
    if src.is_file() and src.suffix and not Path(new_name).suffix:
        new_name += src.suffix  # "rename report.docx to final" keeps .docx
    dst = src.with_name(new_name)
    if dst.exists() and not dst.samefile(src):  # the same file means only the letter case changes
        assert_no_overwrite(dst)
    resolve_safe(str(dst), must_exist=False)  # the new name may not be sensitive either
    return src, dst


def rename_file(path, new_name):
    src, dst = _rename_target(path, new_name)
    _os(f"rename {src.name}", src.rename, dst)
    journal.record("rename_file", "rename", src, dst)
    return f"Renamed {src} to {dst.name}. Undo: /undo"


def copy_file(source, destination):
    src = resolve_safe(source)
    dst = _target(src, destination)
    assert_no_overwrite(dst)
    if not dst.parent.exists():
        raise ToolError(f"Folder not found: {dst.parent}")
    _os(f"copy {src.name}", shutil.copytree if src.is_dir() else shutil.copy2, src, dst)
    journal.record("copy_file", "create", src, dst)
    return f"Copied {src} to {dst}. Undo: /undo"


def zip_folder(source, destination=None):
    src = resolve_safe(source)  # a single file works too
    dst = resolve_safe(destination, must_exist=False) if destination else src.with_name(
        (src.name if src.is_dir() else src.stem) + ".zip")
    if dst.is_dir():
        dst = dst / (src.name + ".zip")
    if dst.suffix.lower() != ".zip":
        dst = dst.with_name(dst.name + ".zip")
    assert_no_overwrite(dst)
    files = list(walk(src)) if src.is_dir() else [src]
    try:
        with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
            for f in files:
                z.write(f, f.relative_to(src.parent))
    except OSError as e:
        dst.unlink(missing_ok=True)  # never leave a half-written zip
        raise ToolError(f"Couldn't zip {src.name}: {e.strerror or e}")
    journal.record("zip_folder", "create", src, dst)
    return f"Created {dst} ({len(files)} files, {size(dst.stat().st_size)}). Undo: /undo"


def _organize_plan(path, strategy):
    root = resolve_safe(path)
    if not root.is_dir():
        raise ToolError(f"Not a folder: {root}")
    moves, skipped = [], []
    for f in sorted(x for x in root.iterdir() if x.is_file() and not is_sensitive(x)
                    and x.suffix.lower() not in SKIP_ORGANIZE and not x.name.startswith((".", "~$"))):
        if strategy == "by_date":
            sub = f"{datetime.fromtimestamp(f.stat().st_mtime):%Y-%m}"
        else:
            sub = next((k for k, exts in TYPES.items() if f.suffix.lower() in exts), "Other")
        dst = root / sub / f.name
        (skipped if dst.exists() else moves).append((f, dst))
    return root, moves, skipped


def organize_folder(path, strategy="by_type"):
    root, moves, skipped = _organize_plan(path, strategy)
    if not moves:
        return f"Nothing to organize in {root}."
    created = sorted({str(d.parent) for _, d in moves if not d.parent.exists()})
    done, failed = [], []
    for src, dst in moves:
        try:
            dst.parent.mkdir(exist_ok=True)
            shutil.move(str(src), str(dst))
            done.append((src, dst))
        except OSError:  # e.g. a file open in another app: skip it and keep going
            failed.append(src.name)
    if not done:
        raise ToolError(f"Couldn't move any files in {root} (are they open in another app?)")
    journal.record("organize_folder", "organize", root, None,  # only what really moved, so /undo is exact
                   {"moves": [[str(s), str(d)] for s, d in done], "created": created})
    moves = done
    counts = {}
    for _, d in moves:
        counts[d.parent.name] = counts.get(d.parent.name, 0) + 1
    parts = ", ".join(f"{n} to {k}\\" for k, n in sorted(counts.items(), key=lambda kv: -kv[1]))
    skip = f" Skipped {len(skipped)} (a file with that name is already in the target folder)." if skipped else ""
    if failed:
        skip += f" Couldn't move {len(failed)} (in use?): {', '.join(failed[:5])}."
    return f"Moved {len(moves)} files in {root}: {parts}.{skip} Undo: /undo"


def move_to_recycle_bin(path):
    p = resolve_safe(path)
    if p in allowed_roots():
        raise ToolError(f"Refused: {p} is one of your main folders.")
    if ctypes.windll.kernel32.GetDriveTypeW(p.anchor) != 3:  # 3 = fixed disk; USB/network drives may delete for good
        raise ToolError(f"Refused: {p.anchor} has no Recycle Bin (removable or network drive), so deleting would be "
                        "permanent.")
    _os(f"move {p.name} to the Recycle Bin", send2trash, str(p))
    journal.record("move_to_recycle_bin", "recycle", p)
    return f"Moved {p} to the Recycle Bin. Undo: /undo"


def open_path(path):
    p = resolve_safe(path)
    if p.is_file() and is_executable(p):
        raise ToolError(f"Refused: {p.name} is a program or script; Alfred doesn't run those.")
    launch(str(p))
    return f"Opened {p} in its default app."


def launch(target: str):
    """os.startfile, unless ALFRED_NO_LAUNCH is set (end-to-end tests must not open windows on the desktop)."""
    if not os.environ.get("ALFRED_NO_LAUNCH"):
        os.startfile(target)


def preview(tool: str, args: dict) -> str:
    """What a confirm-tool would do, for the confirmation prompt (agent, Phase 7). Raises ToolError if it can't."""
    if tool in ("move_file", "copy_file"):
        src = resolve_safe(args["source"])
        dst = _target(src, args["destination"])
        assert_no_overwrite(dst)
        return f"{'Move' if tool == 'move_file' else 'Copy'} {src} → {dst}"
    if tool == "rename_file":
        src, dst = _rename_target(args["path"], args["new_name"])
        return f"Rename {src} → {dst.name}"
    if tool == "zip_folder":
        src = resolve_safe(args["source"])
        default = src.with_name((src.name if src.is_dir() else src.stem) + ".zip")
        return f"Zip {src} → {args.get('destination') or default}"
    if tool == "move_to_recycle_bin":
        return f"Move {resolve_safe(args['path'])} to the Recycle Bin (restorable)"
    if tool == "organize_folder":
        root, moves, skipped = _organize_plan(args["path"], args.get("strategy", "by_type"))
        lines = [f"  {s.name} → {d.parent.name}\\" for s, d in moves]
        return (f"Organize {root} ({len(moves)} moves):\n" + "\n".join(lines[:100]) +
                (f"\n  ... and {len(lines) - 100} more" if len(lines) > 100 else "") +
                (f"\n  (skipping {len(skipped)}: name already in target)" if skipped else ""))
    return f"{tool}({args})"
