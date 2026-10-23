"""Developer tools (contracts 17-18): port_in_use, git_status."""

import subprocess

import psutil
from mcp.server.fastmcp.exceptions import ToolError

from alfred.tools.guards import resolve_safe


def port_in_use(port):
    found = []
    for c in psutil.net_connections(kind="tcp"):
        if c.laddr and c.laddr.port == port and c.status == psutil.CONN_LISTEN:
            try:
                name = psutil.Process(c.pid).name() if c.pid else "unknown"
            except psutil.Error:
                name = "unknown (access denied)"
            found.append(f"{name} (PID {c.pid})")
    if not found:
        return f"Nothing is listening on port {port}."
    return f"Port {port}: {', '.join(dict.fromkeys(found))}."


def git_status(repo_path):
    repo = resolve_safe(repo_path)
    try:
        r = subprocess.run(["git", "-C", str(repo), "status", "--porcelain=v2", "--branch"], capture_output=True,
                           stdin=subprocess.DEVNULL,
                           text=True, timeout=20)
    except FileNotFoundError:
        raise ToolError("git is not installed.")
    if r.returncode != 0:
        raise ToolError(f"Not a git repository: {repo}")
    head, upstream, ahead, behind, changed = "(detached)", None, 0, 0, []
    for line in r.stdout.splitlines():
        if line.startswith("# branch.head "):
            head = line.split(" ", 2)[2]
        elif line.startswith("# branch.upstream "):
            upstream = line.split(" ", 2)[2]
        elif line.startswith("# branch.ab "):
            a, b = line.split()[2:4]
            ahead, behind = int(a), -int(b)
        elif line.startswith("1 "):  # 1 XY sub mH mI mW hH hI path
            parts = line.split(" ", 8)
            changed.append(f"{parts[1].replace('.', '')} {parts[8]}")
        elif line.startswith("2 "):  # 2 XY sub mH mI mW hH hI Xscore path<TAB>orig (a rename)
            parts = line.split(" ", 9)
            new, _, old = parts[9].partition("\t")
            changed.append(f"{parts[1].replace('.', '')} {old} -> {new}")
        elif line.startswith("? "):
            changed.append(f"?? {line[2:]}")
        elif line.startswith("u "):
            changed.append(f"UU {line.split(' ')[-1]}")
    track = f", {ahead} ahead / {behind} behind {upstream}" if upstream else ", no upstream"
    files = ", ".join(changed[:30]) + (f" (+{len(changed) - 30} more)" if len(changed) > 30 else "")
    return f"Branch {head}{track}.\n" + (f"Changed: {files}" if changed else "Working tree clean.")
