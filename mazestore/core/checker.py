"""Background update check — `maze-store --check-updates`.

Run by a systemd *user* timer (maze-store-updates.timer): as the user, never
root, a few times a day. It downloads the [mazelinux] db exactly as the store
window does, compares it with `pacman -Q`, and posts one desktop notification
when Maze apps have updates. It installs nothing — the notification's button
opens the store on its Updates page, and the user takes it from there.

Each update is announced once: the `name=version` pairs already notified are
remembered, so a user who ignores an update is not nagged about it every six
hours, but hears about the next version when it lands.

No Qt is imported here, so the check stays a few MB of memory and a fraction of
a second of CPU.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from mazestore import __version__
from mazestore.core import local, model, repo, settings
from mazestore.core.dbparse import MAX_DB_BYTES

_TIMEOUT = 20


def state_file() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "maze-store" / "notified.json"


def fetch() -> bool:
    """Refresh the cached db. False if offline or the answer was not a db."""
    url = repo.fetch_url()
    if not url.startswith("https://"):
        return False
    req = urllib.request.Request(url, headers={"User-Agent": f"maze-store/{__version__}"})
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = resp.read(MAX_DB_BYTES + 1)
        if len(data) > MAX_DB_BYTES:
            return False
        repo.save_cache(data)
        return True
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return False


def pending_updates() -> list[model.App]:
    cat = repo.load_local()
    apps = model.build(cat.packages, local.installed())
    return [a for a in apps if a.state == "update"]


def _load_seen() -> set[str]:
    try:
        data = json.loads(state_file().read_text())
        return {str(x) for x in data.get("notified", [])}
    except (OSError, ValueError, AttributeError):
        return set()


def _save_seen(keys: set[str]) -> None:
    path = state_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"notified": sorted(keys)}, indent=1))
        os.replace(tmp, path)
    except OSError:
        pass


def _lang() -> str:
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        v = os.environ.get(var, "")
        if v:
            return "tr" if v.lower().startswith("tr") else "en"
    return "en"


def message(apps: list[model.App], lang: str) -> tuple[str, str, str]:
    """(title, body, button) for the notification."""
    names = [a.entry.title for a in apps]
    shown = ", ".join(names[:4]) + (f" +{len(names) - 4}" if len(names) > 4 else "")
    if lang == "tr":
        title = ("1 Maze güncellemesi hazır" if len(apps) == 1
                 else f"{len(apps)} Maze güncellemesi hazır")
        return title, shown, "Maze Store'da aç"
    title = "1 Maze update available" if len(apps) == 1 else f"{len(apps)} Maze updates available"
    return title, shown, "Open in Maze Store"


def notify(apps: list[model.App]) -> None:
    if not shutil.which("notify-send"):
        return
    title, body, button = message(apps, _lang())
    try:
        # --action implies --wait: notify-send returns when the notification is
        # closed or acted on, printing the action's name. Bounded so a
        # notification server that never answers cannot hold the unit forever.
        out = subprocess.run(
            ["notify-send", "--app-name=Maze Store", "--icon=maze-store",
             "--urgency=normal", "--action=open=" + button, title, body],
            capture_output=True, text=True, timeout=600).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return
    if out == "open":
        try:
            subprocess.Popen(["maze-store", "--view=updates"], start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass


def run(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if os.geteuid() == 0:
        print("maze-store --check-updates: run as your user, not root", file=sys.stderr)
        return 1
    if not settings.load()["notify_updates"] and "--print" not in argv:
        return 0  # switched off from the store's sidebar
    fetch()  # offline is fine: fall back to whatever db is on disk
    updates = pending_updates()
    keys = {f"{a.name}={a.pkg.version}" for a in updates}
    seen = _load_seen()
    new = [a for a in updates if f"{a.name}={a.pkg.version}" not in seen]
    if "--print" in argv:
        for a in updates:
            print(f"{a.name} {a.installed} -> {a.pkg.version}")
    announced = set()
    if new and "--no-notify" not in argv:
        notify(updates)
        announced = keys
    # Forget versions that are no longer pending (installed, or superseded), so
    # the file never grows and a re-published version is announced again.
    _save_seen((seen | announced) & keys)
    return 0
