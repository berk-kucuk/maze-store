"""What is installed on this machine, read through pacman as the user."""
from __future__ import annotations

import os
import shlex
import subprocess
from functools import cmp_to_key
from pathlib import Path

LOCAL_DB = Path("/var/lib/pacman/local")


def installed() -> dict[str, str]:
    """{name: version} for every installed package (`pacman -Q`)."""
    try:
        out = subprocess.run(["pacman", "-Q"], capture_output=True, text=True,
                             timeout=15, env={**os.environ, "LC_ALL": "C"}).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    result = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2:
            result[parts[0]] = parts[1]
    return result


# ── version comparison (port of libalpm's rpmvercmp / alpm_pkg_vercmp) ─────
def _isalnum(c: str) -> bool:
    return c.isascii() and c.isalnum()


def _rpmvercmp(a: str, b: str) -> int:
    if a == b:
        return 0
    one = two = 0          # start of the current segment
    p1 = p2 = 0            # end of the previous segment
    while one < len(a) and two < len(b):
        while one < len(a) and not _isalnum(a[one]):
            one += 1
        while two < len(b) and not _isalnum(b[two]):
            two += 1
        if one >= len(a) or two >= len(b):
            break
        # Different separator lengths ("1.0" vs "1..0") decide on their own.
        if one - p1 != two - p2:
            return -1 if one - p1 < two - p2 else 1
        p1, p2 = one, two
        isnum = a[p1].isdigit()
        if isnum:
            while p1 < len(a) and a[p1].isascii() and a[p1].isdigit():
                p1 += 1
            while p2 < len(b) and b[p2].isascii() and b[p2].isdigit():
                p2 += 1
        else:
            while p1 < len(a) and a[p1].isascii() and a[p1].isalpha():
                p1 += 1
            while p2 < len(b) and b[p2].isascii() and b[p2].isalpha():
                p2 += 1
        if two == p2:
            # Segments of different types: numeric is always newer.
            return 1 if isnum else -1
        sa, sb = a[one:p1], b[two:p2]
        if isnum:
            sa, sb = sa.lstrip("0"), sb.lstrip("0")
            if len(sa) != len(sb):
                return 1 if len(sa) > len(sb) else -1
        if sa != sb:
            return 1 if sa > sb else -1
        one, two = p1, p2
    rest_a, rest_b = a[one:], b[two:]
    if not rest_a and not rest_b:
        return 0
    # A leftover alpha segment never beats an empty one: 1.0alpha < 1.0.
    if (not rest_a and not (rest_b[0].isascii() and rest_b[0].isalpha())) or \
            (rest_a and rest_a[0].isascii() and rest_a[0].isalpha()):
        return -1
    return 1


def _split_evr(v: str) -> tuple[str, str, str]:
    epoch, rest = v.split(":", 1) if ":" in v else ("0", v)
    ver, rel = rest.rsplit("-", 1) if "-" in rest else (rest, "")
    return epoch or "0", ver, rel


def vercmp(a: str, b: str) -> int:
    """<0 if a is older than b, 0 if equal, >0 if newer — like `vercmp(8)`."""
    if a == b:
        return 0
    ea, va, ra = _split_evr(a)
    eb, vb, rb = _split_evr(b)
    r = _rpmvercmp(ea, eb) or _rpmvercmp(va, vb)
    if r == 0 and ra and rb:
        r = _rpmvercmp(ra, rb)
    return r


version_key = cmp_to_key(vercmp)


# ── launching an installed app ──────────────────────────────────────────────
def desktop_entries(pkg: str) -> list[Path]:
    """The menu entries a package installed, read from its local `files` list."""
    for d in LOCAL_DB.glob(f"{pkg}-*"):
        # `<name>-<ver>-<rel>`: make sure the prefix really is this package and
        # not e.g. `maze-cloak-extra` when asked for `maze-cloak`.
        if d.name.rsplit("-", 2)[0] != pkg:
            continue
        try:
            text = (d / "files").read_text(errors="replace")
        except OSError:
            continue
        return [Path("/" + line) for line in text.splitlines()
                if line.startswith("usr/share/applications/") and line.endswith(".desktop")]
    return []


def exec_argv(desktop: Path) -> list[str] | None:
    """argv from a .desktop Exec= line, field codes (%U, %f, …) dropped."""
    try:
        lines = desktop.read_text(errors="replace").splitlines()
    except OSError:
        return None
    in_main = False
    for line in lines:
        s = line.strip()
        if s.startswith("["):
            in_main = s == "[Desktop Entry]"
        elif in_main and s.startswith("Exec="):
            try:
                argv = [p for p in shlex.split(s[5:]) if not (len(p) == 2 and p[0] == "%")]
            except ValueError:
                return None
            return argv or None
        elif in_main and s in ("NoDisplay=true", "Hidden=true"):
            return None
    return None
