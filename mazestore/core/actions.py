"""Turning a click into a command the user runs — and authorises — themselves.

The store never holds privileges. It does not call pkexec, it ships no polkit
rule and it never sees a password: every change to the system is a pacman
command started *in a terminal window*, behind `sudo -k`, so the user reads the
exact command and pacman's transaction summary and types their password into
sudo, not into us. `-k` makes sudo ignore a cached timestamp, so a password is
asked every time, even if the user ran sudo a minute ago in another tab.

Install is `pacman -Syu --needed <pkg>`, not `pacman -S <pkg>`: the catalogue
may come from a db fresher than the system's, and on Arch installing against a
newer db without upgrading the rest is the partial upgrade that breaks systems.
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

ACTIONS = ("install", "remove", "upgrade")

RUNNER_CANDIDATES = [
    Path("/opt/maze-store/maze-store-run"),
    Path(__file__).resolve().parents[2] / "maze-store-run",   # source checkout
]


def valid_name(name: str) -> bool:
    return bool(_NAME_RE.match(name))


def pacman_argv(action: str, packages: list[str]) -> list[str]:
    """The exact command shown to the user and run by maze-store-run."""
    if action not in ACTIONS:
        raise ValueError(f"unknown action {action!r}")
    bad = [p for p in packages if not valid_name(p)]
    if bad:
        raise ValueError(f"invalid package name(s): {bad}")
    if action == "install":
        if not packages:
            raise ValueError("nothing to install")
        return ["sudo", "-k", "pacman", "-Syu", "--needed", "--", *packages]
    if action == "remove":
        if not packages:
            raise ValueError("nothing to remove")
        return ["sudo", "-k", "pacman", "-Rns", "--", *packages]
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


# (binary, args placed before the command). Konsole first: it is Maze's
# terminal. The rest cover a user who swapped desktops.
_TERMINALS: list[tuple[str, list[str]]] = [
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
