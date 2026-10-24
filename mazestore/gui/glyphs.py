"""Monochrome line glyphs for the chrome (sidebar, search, buttons).

Drawn here as tiny SVGs on a 24-unit grid with one stroke weight, so every
glyph matches and recolours cleanly; no icon theme is consulted, because a
user's Breeze/Papirus colours would break the black-and-white look.
"""
from __future__ import annotations

from functools import lru_cache

from PyQt6.QtCore import QByteArray, QRectF, Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

_PATHS: dict[str, str] = {
    "all": '<circle cx="12" cy="12" r="9"/><path d="M15.5 8.5 13.6 13.6 8.5 15.5 10.4 10.4Z"/>',
    "privacy": '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z"/>'
               '<circle cx="12" cy="12" r="3"/><path d="M4 4 20 20"/>',
    "security": '<path d="M12 3 19 6v5.5c0 4.4-3 8-7 9.5-4-1.5-7-5.1-7-9.5V6Z"/><path d="m9 12 2 2 4-4"/>',
    "ai": '<path d="M11 4 12.8 9.2 18 11 12.8 12.8 11 18 9.2 12.8 4 11 9.2 9.2Z"/><path d="M18.5 3v4M16.5 5h4"/>',
    "crypto": '<ellipse cx="12" cy="6" rx="7" ry="2.8"/><path d="M5 6v6c0 1.5 3.1 2.8 7 2.8s7-1.3 7-2.8V6"/>'
              '<path d="M5 12v6c0 1.5 3.1 2.8 7 2.8s7-1.3 7-2.8v-6"/>',
    "desktop": '<rect x="3" y="4" width="18" height="12" rx="2.5"/><path d="M8.5 20h7M12 16v4"/>',
    "system": '<path d="M4 7h9M19 7h1M4 17h3M13 17h7"/><circle cx="16" cy="7" r="2.5"/><circle cx="10" cy="17" r="2.5"/>',
    "other": '<rect x="4" y="4" width="6.5" height="6.5" rx="1.8"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="1.8"/>'
             '<rect x="4" y="13.5" width="6.5" height="6.5" rx="1.8"/><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1.8"/>',
    "installed": '<path d="M4 14v3.5A2.5 2.5 0 0 0 6.5 20h11a2.5 2.5 0 0 0 2.5-2.5V14"/><path d="M12 4v10.5M7.5 10 12 14.5 16.5 10"/>',
    "updates": '<path d="M19.5 10.5A7.5 7.5 0 0 0 6 7.2L4.5 9"/><path d="M4.5 4.5V9H9"/>'
               '<path d="M4.5 13.5A7.5 7.5 0 0 0 18 16.8l1.5-1.8"/><path d="M19.5 19.5V15H15"/>',
    "search": '<circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/>',
    "back": '<path d="M15 5 8 12l7 7"/>',
    "external": '<path d="M14 4h6v6M20 4l-8.5 8.5"/><path d="M18 14v4.5a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 4 18.5v-11A1.5 1.5 0 0 1 5.5 6H10"/>',
    "copy": '<rect x="8.5" y="8.5" width="11.5" height="11.5" rx="2.2"/><path d="M15.5 8.5V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v7.5a2 2 0 0 0 2 2h2.5"/>',
    "win_min": '<path d="M6.5 12h11"/>',
    "win_max": '<rect x="6.5" y="6.5" width="11" height="11" rx="1"/>',
    "win_restore": '<rect x="5.5" y="8.5" width="10" height="10" rx="1"/><path d="M8.5 8.5V6.5a1 1 0 0 1 1-1h8a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1h-2"/>',
    "win_close": '<path d="m6.5 6.5 11 11M17.5 6.5l-11 11"/>',
    "terminal": '<rect x="3" y="4.5" width="18" height="15" rx="2.5"/><path d="m7.5 9.5 3 2.5-3 2.5M12.5 15h4"/>',
}


@lru_cache(maxsize=128)
def glyph_pixmap(name: str, size: int, color: str = "#f2f2f4", dpr: float = 2.0) -> QPixmap:
    body = _PATHS.get(name, _PATHS["other"])
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
           f'stroke="{color}" stroke-width="1.7" stroke-linecap="round" '
           f'stroke-linejoin="round">{body}</svg>')
    px = int(size * dpr)
    pm = QPixmap(px, px)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    QSvgRenderer(QByteArray(svg.encode())).render(p, QRectF(0, 0, px, px))
    p.end()
    pm.setDevicePixelRatio(dpr)
    return pm


def glyph(name: str, size: int = 18, color: str = "#f2f2f4") -> QIcon:
    return QIcon(glyph_pixmap(name, size, color))
