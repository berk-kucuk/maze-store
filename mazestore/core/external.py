"""Searching beyond [mazelinux]: the Arch repositories and the AUR.

The Maze catalogue is the store's front page; these two are extra shelves the
user opens and searches. Neither needs root:

* Arch — `pacman -Ss` over the sync databases pacman already has on disk
  (core, extra, multilib, …). They are only as fresh as the last `pacman -Sy`,
  which is fine: installing runs `pacman -Syu --needed`, which refreshes them.
* AUR — the official RPC (`/rpc/v5/search`) over HTTPS. AUR packages are user
  submitted and not vetted by anyone; they are built by an AUR helper (paru,
  which Maze ships) running as the user, which shows the PKGBUILD and
  asks for sudo itself only for the final install.

No Qt here: the GUI runs the search process / request and hands the raw
output to these parsers, so the parsing is testable without a display.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import quote

from mazestore.core.actions import aur_helper, valid_name  # noqa: F401  (re-exported)
from mazestore.core.local import vercmp
from mazestore.core.repo import REPO

AUR_RPC = "https://aur.archlinux.org/rpc/v5/search/"
AUR_PAGE = "https://aur.archlinux.org/packages/"
AUR_INFO = "https://aur.archlinux.org/rpc/v5/info"
# Names per info request; keeps the URL well under any server limit.
AUR_INFO_CHUNK = 100
# The AUR answers with at most 5000 results and refuses shorter terms.
AUR_MIN_TERM = 2
MAX_QUERY = 100
MAX_AUR_BYTES = 8 * 1024 * 1024

_SS_HEAD = re.compile(r"^(?P<repo>[A-Za-z0-9._-]+)/(?P<name>\S+) (?P<ver>\S+)(?P<rest>.*)$")


@dataclass
class ExtPackage:
    name: str
    version: str
    desc: str
    source: str               # "arch" | "aur"
    repo: str = ""            # core / extra / multilib … ("aur" for the AUR)
    url: str = ""
    votes: int = 0
    popularity: float = 0.0
    maintainer: str = ""      # "" = orphaned (AUR)
    out_of_date: bool = False
    installed: str | None = None

    @property
    def state(self) -> str:
        if self.installed is None:
            return "available"
        c = vercmp(self.installed, self.version)
        if c < 0:
            return "update"
        if c > 0:
            return "local"
        return "installed"


def clean_query(query: str) -> list[str]:
    """Search words, lower-cased. A word is never an option: each is passed
    after `--` to pacman, and it only ever lands in a URL path quoted."""
    return query.strip()[:MAX_QUERY].lower().split()


# ── Arch repositories ──────────────────────────────────────────────────────
def pacman_search_argv(words: list[str]) -> list[str]:
    # -Ss terms are regexes, ANDed. `--` keeps a word like "-x" a term.
    return ["pacman", "-Ss", "--", *words]


def parse_pacman_ss(text: str) -> list[ExtPackage]:
    """`repo/name ver (groups) [installed]` + an indented description line.

    [mazelinux] is left out: those packages are on the store's own pages.
    """
    out: list[ExtPackage] = []
    cur: ExtPackage | None = None
    for line in text.splitlines():
        if line.startswith((" ", "\t")):
            if cur is not None:
                cur.desc = (cur.desc + " " + line.strip()).strip()
            continue
        m = _SS_HEAD.match(line)
        if not m or m["repo"] == REPO or not valid_name(m["name"]):
            cur = None
            continue
        cur = ExtPackage(m["name"], m["ver"], "", "arch", repo=m["repo"])
        out.append(cur)
    return out


def rank(pkgs: list[ExtPackage], words: list[str]) -> list[ExtPackage]:
    """Exact name first, then names that start with the query, then the rest
    (by AUR popularity where there is one)."""
    q = "-".join(words)

    def key(p: ExtPackage) -> tuple:
        return (p.name != q, not p.name.startswith(words[0]) if words else True,
                -p.popularity, -p.votes, p.name)
    return sorted(pkgs, key=key)


# ── AUR ────────────────────────────────────────────────────────────────────
def aur_term(words: list[str]) -> str:
    """The RPC takes one term; send the longest word and filter on the rest."""
    return max(words, key=len) if words else ""


def aur_search_url(words: list[str]) -> str:
    return AUR_RPC + quote(aur_term(words), safe="") + "?by=name-desc"


def parse_aur(data: bytes, words: list[str]) -> list[ExtPackage]:
    """The RPC's JSON → packages. Raises ValueError on an error answer."""
    if len(data) > MAX_AUR_BYTES:
        raise ValueError("answer too large")
    try:
        doc = json.loads(data.decode("utf-8", "replace"))
    except ValueError as exc:
        raise ValueError(f"not an AUR answer: {exc}") from exc
    if not isinstance(doc, dict):
        raise ValueError("not an AUR answer")
    if doc.get("type") == "error":
        raise ValueError(str(doc.get("error") or "AUR error"))
    out: list[ExtPackage] = []
    for r in doc.get("results") or []:
        if not isinstance(r, dict):
            continue
        name, ver = str(r.get("Name") or ""), str(r.get("Version") or "")
        if not ver or not valid_name(name):
            continue
        desc = str(r.get("Description") or "")
        hay = f"{name} {desc}".lower()
        if not all(w in hay for w in words):
            continue
        try:
            votes = int(r.get("NumVotes") or 0)
            pop = float(r.get("Popularity") or 0.0)
        except (TypeError, ValueError):
            votes, pop = 0, 0.0
        out.append(ExtPackage(
            name, ver, desc, "aur", repo="aur", url=str(r.get("URL") or ""),
            votes=votes, popularity=pop, maintainer=str(r.get("Maintainer") or ""),
            out_of_date=bool(r.get("OutOfDate"))))
    return out


def foreign_argv() -> list[str]:
    """Installed packages no sync database knows: AUR builds, mostly."""
    return ["pacman", "-Qm"]


def parse_foreign(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2 and valid_name(parts[0]):
            out[parts[0]] = parts[1]
    return out


def aur_info_urls(names: list[str]) -> list[str]:
    names = sorted(n for n in names if valid_name(n))
    return [AUR_INFO + "?" + "&".join("arg[]=" + quote(n, safe="") for n in chunk)
            for chunk in (names[i:i + AUR_INFO_CHUNK]
                          for i in range(0, len(names), AUR_INFO_CHUNK))]


def aur_updates(info: list[ExtPackage], foreign: dict[str, str]) -> list[ExtPackage]:
    """The foreign packages the AUR has a newer version of."""
    mark_installed(info, foreign)
    return sorted((p for p in info if p.state == "update"), key=lambda p: p.name)


def aur_page(name: str) -> str:
    return AUR_PAGE + quote(name, safe="")


def mark_installed(pkgs: list[ExtPackage], installed: dict[str, str]) -> None:
    for p in pkgs:
        p.installed = installed.get(p.name)
