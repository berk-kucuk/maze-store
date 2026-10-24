"""Where the catalogue comes from.

Three sources, freshest first:

1. the published db, fetched over HTTPS by the GUI into the user's cache
   (`fetch_url()` / `save_cache()`);
2. that cache, when the network is down;
3. pacman's own /var/lib/pacman/sync copy, which is always there on a Maze
   system but only as fresh as the last `pacman -Sy`.

None of these needs root. Integrity is pacman's job, not ours: the store only
*shows* what the db says; the packages themselves are signature-checked by
pacman when the user installs them in the terminal.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from mazestore.core.dbparse import MAX_DB_BYTES, RepoPackage, read_db

REPO = "mazelinux"
DEFAULT_SERVER = "https://mazerepo.berkkucukk.com.tr/packages"
SYNC_DB = Path("/var/lib/pacman/sync") / f"{REPO}.db"


def cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "maze-store"


def cache_db() -> Path:
    return cache_dir() / f"{REPO}.db"


def server_url() -> str:
    """The [mazelinux] Server from pacman.conf, so a mirror change applies here too.

    Only https is accepted: the db is fetched by an unprivileged GUI and shown
    as fact, so it must at least not be trivially rewritable on the wire.
    """
    try:
        out = subprocess.run(["pacman-conf", "-r", REPO, "Server"],
                             capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        out = ""
    for line in out.splitlines():
        url = line.strip().replace("$repo", REPO).replace("$arch", os.uname().machine)
        if url.startswith("https://"):
            return url.rstrip("/")
    return DEFAULT_SERVER


def fetch_url() -> str:
    return f"{server_url()}/{REPO}.db"


def save_cache(data: bytes) -> None:
    """Validate, then atomically replace the cached db."""
    read_db(data)  # raises ValueError — a broken download never replaces a good cache
    d = cache_dir()
    d.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".db.")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, cache_db())
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


@dataclass
class Catalogue:
    packages: dict[str, RepoPackage]
    source: str          # "network" | "cache" | "system" | "none"
    mtime: float         # when that copy was written
    error: str = ""


def _load(path: Path) -> dict[str, RepoPackage] | None:
    try:
        if path.stat().st_size > MAX_DB_BYTES:
            return None
        return read_db(path.read_bytes())
    except (OSError, ValueError):
        return None


def load_local(prefer_cache: bool = True) -> Catalogue:
    """The best copy already on disk. Never touches the network."""
    candidates = [(cache_db(), "cache"), (SYNC_DB, "system")]
    loaded = []
    for path, source in candidates:
        pkgs = _load(path)
        if pkgs is not None:
            loaded.append(Catalogue(pkgs, source, path.stat().st_mtime))
    if not loaded:
        return Catalogue({}, "none", 0.0, error="no database")
    # Whichever is newer wins: a user who just ran `pacman -Syu` has a fresher
    # system db than a week-old cache.
    return max(loaded, key=lambda c: c.mtime)


def age_seconds(cat: Catalogue) -> float:
    return max(0.0, time.time() - cat.mtime) if cat.mtime else 0.0
