"""Read a pacman sync database without pacman.

A sync db is a tar archive (gzip or zstd) holding one `<name>-<ver>/desc` file
per package, in pacman's `%FIELD%` / value-lines format. Reading it directly is
what lets the store show a *fresh* catalogue without root: the user's
/var/lib/pacman/sync copy only changes when someone runs `pacman -Sy`, and that
needs privileges this app deliberately never has.
"""
from __future__ import annotations

import io
import tarfile
from dataclasses import dataclass, field

# A real Maze repo db is ~15 KiB compressed. Anything wildly larger is not a
# package list, and parsing it would just burn memory.
MAX_DB_BYTES = 32 * 1024 * 1024
MAX_MEMBER_BYTES = 256 * 1024

_LIST_FIELDS = {"DEPENDS", "OPTDEPENDS", "LICENSE", "PROVIDES", "CONFLICTS",
                "REPLACES", "GROUPS", "MAKEDEPENDS", "CHECKDEPENDS"}


@dataclass
class RepoPackage:
    name: str
    version: str
    desc: str = ""
    url: str = ""
    csize: int = 0          # download size, bytes
    isize: int = 0          # installed size, bytes
    builddate: int = 0      # unix time
    arch: str = ""
    licenses: list[str] = field(default_factory=list)
    depends: list[str] = field(default_factory=list)
    optdepends: list[str] = field(default_factory=list)


def parse_desc(text: str) -> dict[str, list[str]]:
    """`%NAME%\\nvalue\\n\\n%VERSION%…` → {"NAME": ["value"], …}."""
    out: dict[str, list[str]] = {}
    key: str | None = None
    for line in text.splitlines():
        if line.startswith("%") and line.endswith("%") and len(line) > 2:
            key = line[1:-1]
            out[key] = []
        elif not line:
            key = None
        elif key is not None:
            out[key].append(line)
    return out


def _int(fields: dict[str, list[str]], key: str) -> int:
    try:
        return int(fields.get(key, ["0"])[0])
    except (ValueError, IndexError):
        return 0


def package_from_desc(fields: dict[str, list[str]]) -> RepoPackage | None:
    name = (fields.get("NAME") or [""])[0]
    version = (fields.get("VERSION") or [""])[0]
    if not name or not version:
        return None
    return RepoPackage(
        name=name,
        version=version,
        desc=" ".join(fields.get("DESC", [])),
        url=(fields.get("URL") or [""])[0],
        csize=_int(fields, "CSIZE"),
        isize=_int(fields, "ISIZE"),
        builddate=_int(fields, "BUILDDATE"),
        arch=(fields.get("ARCH") or [""])[0],
        licenses=list(fields.get("LICENSE", [])),
        depends=list(fields.get("DEPENDS", [])),
        optdepends=list(fields.get("OPTDEPENDS", [])),
    )


def read_db(data: bytes) -> dict[str, RepoPackage]:
    """Parse a whole sync db. Raises ValueError on anything that is not one."""
    if len(data) > MAX_DB_BYTES:
        raise ValueError("database too large")
    try:
        # mode "r" auto-detects gzip, and zstd on Python ≥ 3.14 — the two
        # compressions repo-add produces.
        tar = tarfile.open(fileobj=io.BytesIO(data), mode="r")
    except (tarfile.TarError, OSError, EOFError) as exc:
        raise ValueError(f"not a pacman database: {exc}") from exc

    packages: dict[str, RepoPackage] = {}
    with tar:
        for member in tar:
            # Only regular `*/desc` files are read, and they are only read into
            # memory — nothing from the archive ever touches the filesystem.
            if not member.isfile() or not member.name.endswith("/desc"):
                continue
            if member.size > MAX_MEMBER_BYTES:
                continue
            fh = tar.extractfile(member)
            if fh is None:
                continue
            pkg = package_from_desc(parse_desc(fh.read().decode("utf-8", "replace")))
            if pkg is not None:
                packages[pkg.name] = pkg
    if not packages:
        raise ValueError("database holds no packages")
    return packages
