"""Where the catalogue comes from.

Three sources, freshest first:

1. the published db, fetched over HTTPS by the GUI into the user's cache
   (`fetch_url()` / `save_cache()`);
2. that cache, when the network is down;
3. pacman's own /var/lib/pacman/sync copy, which is always there on a Maze
   system but only as fresh as the last `pacman -Sy`.

None of these needs root. The packages themselves are signature-checked by
pacman when the user installs them. The db the store fetches itself is
checked here too (audit ST1): what it says — descriptions, versions, "an
update is waiting" — is shown as fact, and HTTPS alone trusts whoever holds
the server or the CDN. The db must carry Maze's signature (`mazelinux.db.sig`,
checked with gpgv against the pacman keyring and the trusted fingerprint) or
it is not cached, and a cached copy is checked again whenever it is read.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from functools import lru_cache
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


KEYRING = Path("/usr/share/pacman/keyrings") / f"{REPO}.gpg"
TRUSTED = Path("/usr/share/pacman/keyrings") / f"{REPO}-trusted"


def _trusted_fingerprints() -> set[str]:
    try:
        lines = TRUSTED.read_text().splitlines()
    except OSError:
        return set()
    return {ln.split(":", 1)[0].strip().upper() for ln in lines if ln.strip() and not ln.startswith("#")}


def verify(data: bytes, sig: bytes) -> bool:
    """True when ``sig`` is a good signature over ``data`` by a key listed in
    the Maze keyring's trusted file. gpgv runs with a throwaway home, so the
    user's own GnuPG setup plays no part."""
    trusted = _trusted_fingerprints()
    if not trusted or not KEYRING.is_file() or not sig or len(sig) > 64 * 1024:
        return False
    with tempfile.TemporaryDirectory(prefix="maze-store-gpgv-") as home:
        dpath, spath = Path(home, "db"), Path(home, "db.sig")
        dpath.write_bytes(data)
        spath.write_bytes(sig)
        try:
            r = subprocess.run(["gpgv", "--homedir", home, "--keyring", str(KEYRING),
                                "--status-fd", "1", str(spath), str(dpath)],
                               capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.SubprocessError):
            return False
    if r.returncode != 0:
        return False
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[:2] == ["[GNUPG:]", "VALIDSIG"]:
            if parts[2].upper() in trusted or parts[-1].upper() in trusted:
                return True
    return False


@lru_cache(maxsize=1)
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


def package_url(filename: str) -> str:
    return f"{server_url()}/{filename}"


def sig_url() -> str:
    return fetch_url() + ".sig"


def _write_atomic(d: Path, target: Path, data: bytes) -> None:
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".db.")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, target)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def save_cache(data: bytes, sig: bytes) -> None:
    """Validate and verify, then atomically replace the cached db (and its
    signature, which load_local checks again on every read)."""
    read_db(data)  # raises ValueError — a broken download never replaces a good cache
    if not verify(data, sig):
        raise ValueError("the database is not signed by the Maze key")
    d = cache_dir()
    d.mkdir(parents=True, exist_ok=True)
    _write_atomic(d, cache_db().with_name(cache_db().name + ".sig"), sig)
    _write_atomic(d, cache_db(), data)


@dataclass
class Catalogue:
    packages: dict[str, RepoPackage]
    source: str          # "network" | "cache" | "system" | "none"
    mtime: float         # when that copy was written
    error: str = ""


def _load(path: Path, require_sig: bool) -> dict[str, RepoPackage] | None:
    """Read a db, checking its .sig when there is one. ``require_sig``: the
    store's own cache must have one; pacman's copy was verified by pacman
    (SigLevel) when it was downloaded, so there a missing .sig is pacman's
    call, but a present one that does not verify is not used."""
    try:
        if path.stat().st_size > MAX_DB_BYTES:
            return None
        data = path.read_bytes()
        sig_path = path.with_name(path.name + ".sig")
        if sig_path.exists():
            if not verify(data, sig_path.read_bytes()):
                return None
        elif require_sig:
            return None
        return read_db(data)
    except (OSError, ValueError):
        return None


def load_local(prefer_cache: bool = True) -> Catalogue:
    """The best copy already on disk. Never touches the network."""
    candidates = [(cache_db(), "cache", True), (SYNC_DB, "system", False)]
    loaded = []
    for path, source, require_sig in candidates:
        pkgs = _load(path, require_sig)
        if pkgs is not None:
            loaded.append(Catalogue(pkgs, source, path.stat().st_mtime))
    if not loaded:
        return Catalogue({}, "none", 0.0, error="no database")
    # Whichever is newer wins: a user who just ran `pacman -Syu` has a fresher
    # system db than a week-old cache.
    return max(loaded, key=lambda c: c.mtime)


def age_seconds(cat: Catalogue) -> float:
    return max(0.0, time.time() - cat.mtime) if cat.mtime else 0.0
