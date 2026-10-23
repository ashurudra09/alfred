"""System tools (contracts 13-16): open_app, system_info, top_processes, network_status."""

import difflib
import os
import platform
import re
import socket
import subprocess
import time
from pathlib import Path

import psutil
from mcp.server.fastmcp.exceptions import ToolError

from alfred.tools.files import size

START_MENUS = [Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / r"Microsoft\Windows\Start Menu\Programs",
               Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs"]
BUILTIN = {"calculator": "calc", "notepad": "notepad", "paint": "mspaint", "settings": "ms-settings:",
           "file explorer": "explorer", "explorer": "explorer", "task manager": "taskmgr", "snipping tool": "snippingtool"}
SKIP_LNK = re.compile(r"uninstall|readme|help|documentation|release notes|website", re.I)


def start_menu_apps() -> dict[str, Path]:
    """App name (lowercase) -> its Start Menu shortcut. Only these (and a few Windows built-ins) can be launched."""
    apps = {}
    for root in START_MENUS:
        if root.is_dir():
            for lnk in root.rglob("*.lnk"):
                if not SKIP_LNK.search(lnk.stem):
                    apps.setdefault(lnk.stem.casefold(), lnk)
    return apps


def open_app(name):
    want = name.strip().casefold().removesuffix(" app").removesuffix(".exe")
    apps = start_menu_apps()
    match = apps.get(want) or next((p for k, p in apps.items() if k.startswith(want) or want in k.split()), None)
    if match is None and want in BUILTIN:
        os.startfile(BUILTIN[want])
        return f"Launched {name.strip().title()}."
    if match is None:
        close = difflib.get_close_matches(want, list(apps), n=3, cutoff=0.6)
        if len(close) == 1:
            match = apps[close[0]]
        else:
            hint = f" Did you mean: {', '.join(apps[c].stem for c in close)}?" if close else ""
            raise ToolError(f"No app called '{name}' in the Start Menu.{hint}")
    os.startfile(str(match))
    return f"Launched {match.stem}."


def system_info():
    cpu = platform.processor() or "CPU"
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).Name"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
        cpu = out.splitlines()[0] if out else cpu
    except (OSError, subprocess.SubprocessError):
        pass
    mem = psutil.virtual_memory()
    bat = psutil.sensors_battery()
    battery = f"Battery: {bat.percent:.0f}%, {'charging' if bat.power_plugged else 'not charging'}." if bat \
        else "Battery: none (desktop)."
    release, version = platform.release(), platform.version()
    win = f"Windows {'11' if int(version.split('.')[-1]) >= 22000 else release} (build {version})"
    return (f"CPU: {cpu} ({psutil.cpu_count()} threads), {psutil.cpu_percent(interval=0.5):.0f}% busy. "
            f"RAM: {mem.used / 2**30:.1f} of {mem.total / 2**30:.1f} GB used. {battery} {win}.")


def top_processes(sort_by="cpu", n=5):
    procs = list(psutil.process_iter(["name", "memory_info"]))
    for p in procs:
        try:
            p.cpu_percent(None)
        except psutil.Error:
            pass
    time.sleep(0.5)
    rows = []
    for p in procs:
        try:
            rows.append((p.info["name"] or "?", p.cpu_percent(None) / psutil.cpu_count(),
                         p.info["memory_info"].rss if p.info["memory_info"] else 0))
        except psutil.Error:
            pass
    rows = [r for r in rows if r[0] not in ("System Idle Process",)]
    rows.sort(key=lambda r: r[1] if sort_by == "cpu" else r[2], reverse=True)
    lines = [f"{name} {cpu:.0f}% CPU, {size(rss)}" for name, cpu, rss in rows[:n]]
    return f"Top {n} by {'CPU' if sort_by == 'cpu' else 'memory'}:\n" + "\n".join(lines)


def _wifi() -> tuple[str | None, str | None]:
    try:
        out = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return None, None
    ssid = re.search(r"^\s*SSID\s*:\s*(.+)$", out, re.M)
    signal = re.search(r"^\s*Signal\s*:\s*(\d+%)", out, re.M)
    return ssid and ssid.group(1).strip(), signal and signal.group(1)


WIRELESS = re.compile(r"wi-?fi|wlan|wireless|802\.11", re.I)
VIRTUAL = re.compile(r"loopback|vethernet|virtual|vmware|vbox|hyper-v|bluetooth|tailscale|wireguard|zerotier", re.I)


def _route_ip() -> str | None:
    """The local address the OS would use for internet traffic (a UDP connect sends no packets)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("1.1.1.1", 53))
            return s.getsockname()[0]
    except OSError:
        return None


def active_interfaces() -> list[tuple[str, str, bool]]:
    """(interface name, IPv4, is_wireless) for interfaces that are up, the default-route one first."""
    stats, route, out = psutil.net_if_stats(), _route_ip(), []
    for name, addrs in psutil.net_if_addrs().items():
        if not (stats.get(name) and stats[name].isup) or VIRTUAL.search(name):
            continue
        for a in addrs:
            if a.family == socket.AF_INET and not a.address.startswith(("127.", "169.254.")):
                out.append((name, a.address, bool(WIRELESS.search(name))))
    return sorted(out, key=lambda x: x[1] != route)


def network_status():
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=1.5).close()
        online = True
    except OSError:
        online = False
    ifaces = active_interfaces()
    if not ifaces:
        return f"{'Online' if online else 'Offline'}. Not connected to any network."
    name, ip, wireless = ifaces[0]
    if wireless:
        ssid, signal = _wifi()
        conn = f"Wi-Fi: {ssid or name}" + (f" (signal {signal})" if signal else "")
    else:
        conn = f"Wired: {name}"
        wifi_ssid, signal = _wifi()
        if wifi_ssid:
            conn += f" (Wi-Fi {wifi_ssid} also connected)"
    return f"{'Online' if online else 'Offline'}. {conn}. Local IP: {ip}."
