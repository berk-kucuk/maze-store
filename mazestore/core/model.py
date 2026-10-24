"""Catalogue + local state → the list of apps the window draws."""
from __future__ import annotations

from dataclasses import dataclass

from mazestore.core.catalog import CATEGORIES, Entry, entry_for, is_hidden
from mazestore.core.dbparse import RepoPackage
from mazestore.core.local import vercmp


@dataclass
class App:
    name: str
    entry: Entry
    pkg: RepoPackage
    installed: str | None = None   # installed version, if any

    @property
    def state(self) -> str:
        if self.installed is None:
            return "available"
        c = vercmp(self.installed, self.pkg.version)
        if c < 0:
            return "update"
        if c > 0:
            return "local"      # a newer local build than the repo carries
        return "installed"

    def tagline(self, lang: str) -> str:
        text = self.entry.tagline_tr if lang == "tr" else self.entry.tagline_en
        return text or self.pkg.desc

    def matches(self, query: str) -> bool:
        q = query.casefold().strip()
        if not q:
            return True
        hay = " ".join([self.name, self.entry.title, self.entry.tagline_en,
                        self.entry.tagline_tr, self.pkg.desc]).casefold()
        return all(word in hay for word in q.split())


def build(packages: dict[str, RepoPackage], installed: dict[str, str]) -> list[App]:
    apps = [App(name, entry_for(name, pkg.desc), pkg, installed.get(name))
            for name, pkg in packages.items() if not is_hidden(name)]
    order = {c: i for i, c in enumerate(CATEGORIES)}
    apps.sort(key=lambda a: (order.get(a.entry.category, 99), a.entry.title.casefold()))
    return apps


def select(apps: list[App], view: str, query: str = "") -> list[App]:
    """view: a category from CATEGORIES, or "installed" / "updates"."""
    if view == "installed":
        out = [a for a in apps if a.installed is not None]
    elif view == "updates":
        out = [a for a in apps if a.state == "update"]
    elif view == "all":
        out = list(apps)
    else:
        out = [a for a in apps if a.entry.category == view]
    return [a for a in out if a.matches(query)]
