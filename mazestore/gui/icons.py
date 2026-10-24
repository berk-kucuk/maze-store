"""App icons: bundled artwork, then the icon theme, then a drawn Maze tile.

Bundled first because most of the point of a store is showing apps that are
*not* installed yet — and an uninstalled app has no icon in the theme.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PyQt6.QtCore import QByteArray, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets" / "apps"
APP_LOGO_CANDIDATES = [ROOT / "MAZE-STORE.png", ROOT / "maze-store-logo.svg"]
LOGO_SVG_CANDIDATES = [ROOT / "maze-store-logo.svg",
                       Path("/usr/share/icons/hicolor/scalable/apps/maze-store.svg")]


def _screen_dpr() -> float:
    screen = QGuiApplication.primaryScreen()
    dpr = screen.devicePixelRatio() if screen else 1.0
    # Never below 2: fractional scales (1.25, 1.5) and a window moved to a
    # denser screen both look soft if the art was drawn at exactly 1x.
    return max(2.0, dpr)


@lru_cache(maxsize=16)
def logo_pixmap(size: int) -> QPixmap:
    """The mark drawn from its SVG at the screen's pixel density.

    A QIcon built from the 1024px PNG is scaled down with no regard for the
    device pixel ratio, which is what made the 24px header mark look pixelated.
    """
    dpr = _screen_dpr()
    px = int(round(size * dpr))
    for svg in LOGO_SVG_CANDIDATES:
        if svg.is_file():
            renderer = QSvgRenderer(QByteArray(svg.read_bytes()))
            if renderer.isValid():
                pm = QPixmap(px, px)
                pm.fill(Qt.GlobalColor.transparent)
                p = QPainter(pm)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                renderer.render(p, QRectF(0, 0, px, px))
                p.end()
                pm.setDevicePixelRatio(dpr)
                return pm
    pm = app_logo().pixmap(px, px)
    pm.setDevicePixelRatio(dpr)
    return pm


def app_logo() -> QIcon:
    themed = QIcon.fromTheme("maze-store")
    if not themed.isNull():
        return themed
    for p in APP_LOGO_CANDIDATES:
        if p.is_file():
            return QIcon(str(p))
    return QIcon(_tile("maze-store", 256))


def _initials(name: str) -> str:
    words = [w for w in name.replace("plasma6-applets-", "").split("-")
             if w and w not in ("maze", "linux")]
    if not words:
        words = name.split("-")
    if len(words) == 1:
        return words[0][:2].capitalize()
    return (words[0][0] + words[1][0]).upper()


def _tile(name: str, size: int) -> QPixmap:
    """Black tile, Maze frame open on the right, initials in the middle."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size / 1024.0
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size, size), 220 * s, 220 * s)
    p.fillPath(path, QColor("#000000"))
    p.setPen(QPen(QColor("#2c2c2c"), max(1.0, 3 * s)))
    p.drawPath(path)
    pen = QPen(QColor("#f2f2f4"), 44 * s)
    pen.setCapStyle(Qt.PenCapStyle.FlatCap)
    pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
    p.setPen(pen)
    frame = QPainterPath()
    frame.moveTo(812 * s, 330 * s)
    frame.lineTo(812 * s, 212 * s)
    frame.lineTo(212 * s, 212 * s)
    frame.lineTo(212 * s, 812 * s)
    frame.lineTo(812 * s, 812 * s)
    frame.lineTo(812 * s, 694 * s)
    p.drawPath(frame)
    f = QFont("Inter")
    f.setBold(True)
    f.setPixelSize(int(300 * s))
    p.setFont(f)
    p.setPen(QColor("#f2f2f4"))
    p.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, _initials(name))
    p.end()
    return pm


@lru_cache(maxsize=256)
def app_pixmap(name: str, size: int) -> QPixmap:
    bundled = ASSETS / f"{name}.png"
    if bundled.is_file():
        pm = QPixmap(str(bundled))
        if not pm.isNull():
            return pm.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
    if QIcon.hasThemeIcon(name):
        pm = QIcon.fromTheme(name).pixmap(size, size)
        if not pm.isNull():
            return pm
    return _tile(name, size)


@lru_cache(maxsize=256)
def tile_pixmap(name: str, size: int, dpr: float = 2.0) -> QPixmap:
    """The app icon on a uniform rounded tile with a hairline rim.

    Artwork arrives in every shape — full tiles, trimmed marks, round avatars.
    Seating all of it on the same black squircle is what makes a grid of
    different apps read as one store. Art that is not already a tile (its
    left edge is transparent) is inset so it does not touch the rim.
    """
    px = int(size * dpr)
    src = app_pixmap(name, px)
    img = src.toImage()
    is_tile = (not img.isNull() and img.width() > 4 and
               img.pixelColor(2, img.height() // 2).alpha() > 200)
    out = QPixmap(px, px)
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    radius = px * 0.235
    clip = QPainterPath()
    clip.addRoundedRect(QRectF(0, 0, px, px), radius, radius)
    p.fillPath(clip, QColor("#000000"))
    p.setClipPath(clip)
    inset = 0 if is_tile else int(px * 0.13)
    target = QRectF(inset, inset, px - 2 * inset, px - 2 * inset)
    p.drawPixmap(target, src, QRectF(src.rect()))
    p.setClipping(False)
    rim = QColor(255, 255, 255)
    rim.setAlphaF(0.16)
    p.setPen(QPen(rim, max(1.0, dpr)))
    p.drawRoundedRect(QRectF(0.5 * dpr, 0.5 * dpr, px - dpr, px - dpr), radius, radius)
    p.end()
    out.setDevicePixelRatio(dpr)
    return out
