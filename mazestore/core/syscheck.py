"""Every pending repository update — found without root.

Run as `maze-store --pending-upgrades` in a child process (so the window never
waits on the network), it prints JSON: for each package `pacman -Syu` would
upgrade, its versions, the repository it comes from, the URL of the new
package file and its dependencies. The window uses that to list Arch updates
next to Maze ones, and to update a single package with `pacman -U <url>`
without refreshing the system's databases.

Done the way pacman-contrib's `checkupdates` does it: refresh a *copy* of the
sync databases under the user's cache with fakeroot, then `pacman -Qu`
against that copy. The system's own databases are never touched.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from mazestore.core import repo
from mazestore.core.dbparse import MAX_DB_BYTES, read_db

_TIMEOUT = 90
SYSTEM_SYNC = Path("/var/lib/pacman/sync")
_FILE_RE = re.compile(r"^[A-Za-z0-9@_+][A-Za-z0-9@._+:-]*\.pkg\.tar\.(zst|xz|gz)$")


def db_dir() -> Path:
    return repo.cache_dir() / "checkup-db"


def parse_qu(text: str) -> list[tuple[str, str, str]]:
    """`name old -> new [ignored]` lines → (name, old, new)."""
    out = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[2] == "->":
            out.append((parts[0], parts[1], parts[3]))
    return out


def dep_name(dep: str) -> str:
    """`qt6-base>=6.8` / `libfoo.so=1-64` → the name pacman resolves."""
    return re.split(r"[<>=]", dep, maxsplit=1)[0].strip()


def _run(argv: list[str], timeout: int = _TIMEOUT) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                          env={**os.environ, "LC_ALL": "C"})


def refresh() -> Path | None:
    """Bring the private copy of the sync dbs up to date. Its path, or None."""
    if not shutil.which("fakeroot"):
        return None
    db = db_dir()
    db.mkdir(parents=True, exist_ok=True)
    link = db / "local"
    if not link.is_symlink():
        if link.exists():
            return None
        link.symlink_to("/var/lib/pacman/local")
    # Start from the system's copies: pacman then only downloads what changed.
    sync = db / "sync"
    sync.mkdir(exist_ok=True)
    for src in SYSTEM_SYNC.glob("*.db*"):
        dst = sync / src.name
        if src.is_file() and not dst.exists():
            shutil.copy2(src, dst)
    r = _run(["fakeroot", "--", "pacman", "-Sy", "--dbpath", str(db), "--logfile", "/dev/null"])
    return db if r.returncode == 0 else None


def _server(repo_name: str) -> str:
    r = _run(["pacman-conf", "-r", repo_name, "Server"], timeout=10)
    for line in r.stdout.splitlines():
        if line.strip().startswith("https://"):
            return line.strip().rstrip("/")
    return ""


def pending() -> list[dict] | None:
    """Pending upgrades with repo, file URL and depends; None on failure."""
    try:
        db = refresh()
        if db is None:
            return None
        r = _run(["pacman", "-Qu", "--dbpath", str(db)], timeout=30)
        if r.returncode not in (0, 1):      # 1: nothing pending
            return None
        todo = {name: (old, new) for name, old, new in parse_qu(r.stdout)}
        out: list[dict] = []
        repos = _run(["pacman-conf", "--repo-list"], timeout=10).stdout.split()
        for repo_name in repos:             # pacman.conf order: first match wins
            if not todo:
                break
            path = db / "sync" / f"{repo_name}.db"
            try:
                if path.stat().st_size > MAX_DB_BYTES:
                    continue
                pkgs = read_db(path.read_bytes())
            except (OSError, ValueError):
                continue
            server = None
            for name in [n for n in todo if n in pkgs]:
                old, new = todo.pop(name)
                pkg = pkgs[name]
                if server is None:
                    server = _server(repo_name)
                url = (f"{server}/{pkg.filename}"
                       if server and _FILE_RE.match(pkg.filename) else "")
                out.append({"name": name, "old": old, "new": new, "repo": repo_name,
                            "url": url, "desc": pkg.desc,
                            "depends": [dep_name(d) for d in pkg.depends]})
        for name, (old, new) in todo.items():
            out.append({"name": name, "old": old, "new": new, "repo": "", "url": "",
                        "desc": "", "depends": []})
        return out
    except (OSError, subprocess.SubprocessError):
        return None


def parse_output(text: str) -> list[dict] | None:
    try:
        doc = json.loads(text)
    except ValueError:
        return None
    items = doc.get("pending") if isinstance(doc, dict) else None
    if not isinstance(items, list):
        return None
    return [i for i in items if isinstance(i, dict) and isinstance(i.get("name"), str)]


def run() -> int:
    if os.geteuid() == 0:
        print("maze-store --pending-upgrades: run as your user, not root", file=sys.stderr)
        return 1
    result = pending()
    if result is None:
        return 1
    print(json.dumps({"pending": result}))
    return 0
