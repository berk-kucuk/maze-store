"""Turning a click into a command the user runs — and authorises — themselves.

The store never holds privileges. It does not call pkexec, it ships no polkit
rule and it never sees a password: every change to the system is a pacman
command started *in a terminal window*, behind `sudo -k`, so the user reads the
exact command and pacman's transaction summary and types their password into
sudo, not into us. `-k` makes sudo ignore a cached timestamp, so a password is
asked every time, even if the user ran sudo a minute ago in another tab.

Updating one package is `pacman -U --needed <url of its file>`: just that
package, and the system's sync databases are not refreshed — refreshing them
(-Sy) and then installing one package is the partial upgrade that breaks Arch
systems. pacman checks the file's signature (RemoteFileSigLevel) and resolves
its dependencies from the databases the system already has. `install` keeps
the full `pacman -Syu --needed <pkg>` for when the user picks the whole
system, and `install-only` (`-S --needed`, no -y) installs a new Arch package
from the databases as they are.

AUR packages are the one exception to `sudo -k`: they are built by an AUR
helper — paru, which Maze Linux ships — that must run as the user — building as root is what
makepkg refuses — and that calls sudo itself for the final install. It shows
the PKGBUILD for review first and, like pacman, waits for confirmation.
"""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

# pacman's own package-name rules: lowercase alnum and @._+-, not starting with
# a hyphen or dot. Checked again in the runner script, because the name ends up
# on a root command line.
_NAME_RE = re.compile(r"^[a-z0-9@_+][a-z0-9@._+-]{0,127}$")

ACTIONS = ("install", "install-only", "install-file", "remove", "upgrade",
           "aur-install", "full-upgrade")

# A package file on an https server, as the runner script checks it again.
_URL_RE = re.compile(r"^https://[A-Za-z0-9.-]+(:[0-9]+)?(/[A-Za-z0-9._~@+:-]+)*"
                     r"/[A-Za-z0-9@_+][A-Za-z0-9@._+:-]*\.pkg\.tar\.(zst|xz|gz)$")

# The AUR helper: paru, which Maze Linux ships by default (it is in
# [mazelinux]). The runner script uses it too.
AUR_HELPERS = ("paru",)

RUNNER_CANDIDATES = [
    Path("/opt/maze-store/maze-store-run"),
    Path(__file__).resolve().parents[2] / "maze-store-run",   # source checkout
]


def valid_name(name: str) -> bool:
    return bool(_NAME_RE.match(name))


def valid_url(url: str) -> bool:
    return bool(_URL_RE.match(url)) and ".." not in url


def aur_helper() -> str | None:
    for h in AUR_HELPERS:
        if shutil.which(h):
            return h
    return None


def pacman_argv(action: str, packages: list[str]) -> list[str]:
    """The exact command shown to the user and run by maze-store-run."""
    if action not in ACTIONS:
        raise ValueError(f"unknown action {action!r}")
    check = valid_url if action == "install-file" else valid_name
    bad = [p for p in packages if not check(p)]
    if bad:
        raise ValueError(f"invalid package name(s): {bad}")
    if action == "install":
        if not packages:
            raise ValueError("nothing to install")
        return ["sudo", "-k", "pacman", "-Syu", "--needed", "--", *packages]
    if action == "install-only":
        if not packages:
            raise ValueError("nothing to install")
        return ["sudo", "-k", "pacman", "-S", "--needed", "--", *packages]
    if action == "install-file":
        if not packages:
            raise ValueError("nothing to install")
        return ["sudo", "-k", "pacman", "-U", "--needed", "--", *packages]
    if action == "full-upgrade":
        # Repositories and AUR in one go, as the user; the helper calls sudo.
        return [aur_helper() or AUR_HELPERS[0], "-Syu"]
    if action == "remove":
        if not packages:
            raise ValueError("nothing to remove")
        return ["sudo", "-k", "pacman", "-Rns", "--", *packages]
    if action == "aur-install":
        if not packages:
            raise ValueError("nothing to install")
        # No `--`: not every helper's parser takes it, and the names were
        # just checked not to start with a hyphen.
        return [aur_helper() or AUR_HELPERS[0], "-S", "--needed", *packages]
    return ["sudo", "-k", "pacman", "-Syu"]


def display_command(action: str, packages: list[str]) -> str:
    argv = pacman_argv(action, packages)
    # `-k` and `--` are implementation detail; show what a person would type.
    return " ".join(a for a in argv if a not in ("-k", "--"))


def runner() -> Path | None:
    for p in RUNNER_CANDIDATES:
        if p.is_file() and os.access(p, os.X_OK):
            return p
    return None


# (binary, args placed before the command). Maze Terminal first: it is
# Maze's terminal (one process per window, so it stays until the window
# closes), then Konsole. The rest cover a user who swapped desktops.
_TERMINALS: list[tuple[str, list[str]]] = [
    ("maze-terminal", ["-e"]),
    ("konsole", ["--separate", "-p", "tabtitle=Maze Store", "-e"]),
    ("kgx", ["--"]),
    ("gnome-terminal", ["--wait", "--"]),
    ("xfce4-terminal", ["--disable-server", "-x"]),
    ("alacritty", ["-e"]),
    ("kitty", ["--"]),
    ("foot", []),
    ("wezterm", ["start", "--"]),
    ("xterm", ["-e"]),
]


def find_terminal() -> tuple[str, list[str]] | None:
    for binary, prefix in _TERMINALS:
        path = shutil.which(binary)
        if path:
            return path, prefix
    return None


def terminal_argv(action: str, packages: list[str]) -> list[str]:
    """Full argv that opens a terminal running the action. Raises RuntimeError."""
    pacman_argv(action, packages)  # validate before anything else
    run = runner()
    if run is None:
        raise RuntimeError("maze-store-run is missing")
    term = find_terminal()
    if term is None:
        raise RuntimeError("no terminal emulator found")
    binary, prefix = term
    # Each package is its own argv element all the way down: no shell ever sees
    # a name, so nothing in one can be interpreted as syntax.
    return [binary, *prefix, str(run), action, *packages]
