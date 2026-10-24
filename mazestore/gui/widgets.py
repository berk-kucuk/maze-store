"""Cards, the detail page and the small pieces they share."""
from __future__ import annotations

import time

from PyQt6.QtCore import QSize, QTimer, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QGuiApplication, QMouseEvent
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
                             QSizePolicy, QVBoxLayout, QWidget)

from mazestore.core.actions import display_command
from mazestore.core.model import App
from mazestore.gui.glass import GlassFrame
from mazestore.gui.glyphs import glyph
from mazestore.gui.i18n import language, t
from mazestore.gui.icons import tile_pixmap
from mazestore.gui.pill import Pill


def human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if size < 1024 or unit == "GiB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{n} B"


def label(text: str, name: str, wrap: bool = False) -> QLabel:
    lb = QLabel(text)
    lb.setObjectName(name)
    lb.setWordWrap(wrap)
    return lb


def icon_label(name: str, size: int) -> QLabel:
    lb = QLabel()
    lb.setPixmap(tile_pixmap(name, size))
    lb.setFixedSize(size, size)
    return lb


def pill_for(app: App, busy: bool) -> Pill | None:
    if busy:
        return Pill(t("pill_busy"), "busy")
    return {
        "update": lambda: Pill(t("pill_update"), "update"),
        "installed": lambda: Pill(t("pill_installed"), "installed"),
        "local": lambda: Pill(t("pill_local"), "local"),
    }.get(app.state, lambda: None)()


def action_button(app: App, busy: bool, can_open: bool, large: bool = False) -> tuple[QPushButton | None, str]:
    """The one button a card offers, and the action it triggers."""
    if app.state in ("available", "update"):
        text = t("btn_get") if app.state == "available" else t("btn_update")
        btn = QPushButton(text, objectName="get_lg" if large else "get")
        act = "install"
    elif can_open:
        btn = QPushButton(t("btn_open"), objectName="open_lg" if large else "open")
        act = "open"
    else:
        return None, ""
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setEnabled(not busy)
    return btn, act


class _Clickable:
    """Click anywhere on the card (outside its button) to open the details."""

    def mouseReleaseEvent(self, ev: QMouseEvent) -> None:  # type: ignore[override]
        if ev.button() == Qt.MouseButton.LeftButton and self.rect().contains(ev.position().toPoint()):
            self.opened.emit(self._name)
        super().mouseReleaseEvent(ev)


class AppRow(_Clickable, GlassFrame):
    """Compact list card: icon, name, one line of pitch, pill button."""
    opened = pyqtSignal(str)
    action = pyqtSignal(str, str)

    def __init__(self, app: App, busy: bool, can_open: bool):
        GlassFrame.__init__(self, radius=18, interactive=True)
        self._name = app.name
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(96)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(14)
        lay.addWidget(icon_label(app.name, 60), 0, Qt.AlignmentFlag.AlignVCenter)

        col = QVBoxLayout()
        col.setSpacing(3)
        col.addStretch(1)
        top = QHBoxLayout()
        top.setSpacing(8)
        top.addWidget(label(app.entry.title, "title"))
        pill = pill_for(app, busy)
        if pill is not None:
            top.addWidget(pill, 0, Qt.AlignmentFlag.AlignVCenter)
        top.addStretch(1)
        col.addLayout(top)
        tag = label(app.tagline(language()), "tagline", wrap=True)
        tag.setMaximumHeight(34)
        col.addWidget(tag)
        col.addStretch(1)
        lay.addLayout(col, 1)

        btn, act = action_button(app, busy, can_open)
        if btn is not None:
            btn.clicked.connect(lambda: self.action.emit(act, self._name))
            lay.addWidget(btn, 0, Qt.AlignmentFlag.AlignVCenter)


class FeaturedCard(_Clickable, GlassFrame):
    """Shop-window card: large icon, category, name, pitch, button."""
    opened = pyqtSignal(str)
    action = pyqtSignal(str, str)

    def __init__(self, app: App, busy: bool, can_open: bool):
        GlassFrame.__init__(self, radius=24, interactive=True, strength=1.15)
        self._name = app.name
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(176)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(22, 22, 22, 22)
        lay.setSpacing(20)
        lay.addWidget(icon_label(app.name, 88), 0, Qt.AlignmentFlag.AlignTop)

        col = QVBoxLayout()
        col.setSpacing(4)
        col.addWidget(label(t(f"cat_{app.entry.category}").upper(), "eyebrow"))
        top = QHBoxLayout()
        top.setSpacing(8)
        top.addWidget(label(app.entry.title, "feature_title"))
        pill = pill_for(app, busy)
        if pill is not None:
            top.addWidget(pill, 0, Qt.AlignmentFlag.AlignVCenter)
        top.addStretch(1)
        col.addLayout(top)
        tag = label(app.tagline(language()), "tagline_lg", wrap=True)
        tag.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        col.addWidget(tag, 1)
        bottom = QHBoxLayout()
        bottom.setSpacing(12)
        btn, act = action_button(app, busy, can_open)
        if btn is not None:
            btn.clicked.connect(lambda: self.action.emit(act, self._name))
            bottom.addWidget(btn)
        bottom.addWidget(label(f"{app.pkg.version}  ·  {human_size(app.pkg.csize)}", "meta"))
        bottom.addStretch(1)
        col.addLayout(bottom)
        lay.addLayout(col, 1)


class SectionHeader(QWidget):
    def __init__(self, title: str, sub: str = ""):
        super().__init__()
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 14, 0, 2)
        v.setSpacing(2)
        v.addWidget(label(title, "h2"))
        if sub:
            v.addWidget(label(sub, "h2_sub"))


class StatsBar(GlassFrame):
    """Facts in one strip, separated by hairlines — reads as a single unit."""

    def __init__(self, stats: list[tuple[str, str]]):
        super().__init__(radius=18)
        h = QHBoxLayout(self)
        h.setContentsMargins(6, 14, 6, 14)
        h.setSpacing(0)
        for i, (k, v) in enumerate(stats):
            if i:
                line = QFrame()
                line.setObjectName("vline")
                line.setFixedWidth(1)
                h.addWidget(line)
            cell = QVBoxLayout()
            cell.setSpacing(5)
            kl = label(k, "section")
            kl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vl = label(v, "stat")
            vl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            cell.addWidget(kl)
            cell.addWidget(vl)
            h.addLayout(cell, 1)


class DetailPage(QScrollArea):
    back = pyqtSignal()
    action = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.viewport().setAutoFillBackground(False)
        self._app: App | None = None

    def show_app(self, app: App, busy: bool, can_open: bool) -> None:
        self._app = app
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(36, 22, 36, 36)
        outer.setSpacing(18)

        back = QPushButton(t("btn_back"), objectName="ghost")
        back.setIcon(glyph("back", 16, "#bdbdc2"))
        back.setIconSize(QSize(16, 16))
        back.setCursor(Qt.CursorShape.PointingHandCursor)
        back.clicked.connect(self.back.emit)
        outer.addWidget(back, 0, Qt.AlignmentFlag.AlignLeft)

        # ── head ─────────────────────────────────────────────────────────
        head_frame = GlassFrame(radius=28, tint="#ffffff", strength=0.9)
        head = QHBoxLayout(head_frame)
        head.setContentsMargins(30, 28, 30, 28)
        head.setSpacing(26)
        head.addWidget(icon_label(app.name, 128), 0, Qt.AlignmentFlag.AlignTop)
        info = QVBoxLayout()
        info.setSpacing(6)
        info.addWidget(label(t(f"cat_{app.entry.category}").upper(), "eyebrow"))
        title_row = QHBoxLayout()
        title_row.setSpacing(12)
        title_row.addWidget(label(app.entry.title, "big_title"))
        pill = pill_for(app, busy)
        if pill is not None:
            title_row.addWidget(pill, 0, Qt.AlignmentFlag.AlignVCenter)
        title_row.addStretch(1)
        info.addLayout(title_row)
        info.addWidget(label(app.tagline(language()), "detail_tagline", wrap=True))
        info.addSpacing(10)

        btns = QHBoxLayout()
        btns.setSpacing(10)
        primary, act = action_button(app, busy, can_open, large=True)
        if primary is not None:
            primary.clicked.connect(lambda: self.action.emit(act, app.name))
            btns.addWidget(primary)
        if app.installed is not None:
            rm = QPushButton(t("btn_remove"), objectName="secondary_lg")
            rm.setCursor(Qt.CursorShape.PointingHandCursor)
            rm.setEnabled(not busy)
            rm.clicked.connect(lambda: self.action.emit("remove", app.name))
            btns.addWidget(rm)
        if app.pkg.url.startswith("https://") and "invalid" not in app.pkg.url:
            web = QPushButton(t("lbl_website"), objectName="ghost")
            web.setIcon(glyph("external", 15, "#bdbdc2"))
            web.setIconSize(QSize(15, 15))
            web.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            web.setCursor(Qt.CursorShape.PointingHandCursor)
            web.setToolTip(app.pkg.url)
            web.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(app.pkg.url)))
            btns.addWidget(web)
        btns.addStretch(1)
        info.addLayout(btns)
        info.addStretch(1)
        head.addLayout(info, 1)
        outer.addWidget(head_frame)

        # ── facts ────────────────────────────────────────────────────────
        stats = [(t("lbl_version"), app.pkg.version)]
        if app.installed is not None and app.installed != app.pkg.version:
            stats.append((t("lbl_installed_ver"), app.installed))
        stats += [(t("lbl_download"), human_size(app.pkg.csize)),
                  (t("lbl_size"), human_size(app.pkg.isize)),
                  (t("lbl_license"), ", ".join(app.pkg.licenses) or "—")]
        if app.pkg.builddate:
            stats.append((t("lbl_built"),
                          time.strftime("%Y-%m-%d", time.localtime(app.pkg.builddate))))
        outer.addWidget(StatsBar(stats))

        # ── about + command, side by side when there is room ─────────────
        about = GlassFrame(radius=20)
        av = QVBoxLayout(about)
        av.setContentsMargins(22, 20, 22, 20)
        av.setSpacing(8)
        av.addWidget(label(t("lbl_about"), "section"))
        av.addWidget(label(app.pkg.desc or app.tagline(language()), "body", wrap=True))
        mono = label(app.name, "mono")
        mono.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        av.addWidget(mono)
        if app.pkg.depends:
            av.addSpacing(8)
            av.addWidget(label(t("lbl_depends"), "section"))
            av.addWidget(label("  ·  ".join(app.pkg.depends), "mono", wrap=True))
        if app.pkg.optdepends:
            av.addSpacing(8)
            av.addWidget(label(t("lbl_optdepends"), "section"))
            av.addWidget(label("\n".join(app.pkg.optdepends), "mono", wrap=True))
        outer.addWidget(about)

        cmd_frame = GlassFrame(radius=20)
        cv = QVBoxLayout(cmd_frame)
        cv.setContentsMargins(22, 20, 22, 20)
        cv.setSpacing(12)
        installing = app.state in ("available", "update")
        head_row = QHBoxLayout()
        ti = QLabel()
        ti.setPixmap(glyph("terminal", 16, "#9a9a9f").pixmap(16, 16))
        head_row.addWidget(ti)
        head_row.addWidget(label(t("lbl_command" if installing else "lbl_command_remove"), "section"))
        head_row.addStretch(1)
        cv.addLayout(head_row)
        cmd = display_command("install" if installing else "remove", [app.name])
        row = QHBoxLayout()
        row.setSpacing(10)
        cmd_lbl = label("$ " + cmd, "command")
        cmd_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        row.addWidget(cmd_lbl, 1)
        copy = QPushButton(t("btn_copy"), objectName="secondary")
        copy.setIcon(glyph("copy", 15))
        copy.setIconSize(QSize(15, 15))
        copy.setCursor(Qt.CursorShape.PointingHandCursor)

        def _copy() -> None:
            QGuiApplication.clipboard().setText(cmd)
            copy.setText(t("btn_copied"))
            QTimer.singleShot(1400, lambda: copy.setText(t("btn_copy")))
        copy.clicked.connect(_copy)
        row.addWidget(copy)
        cv.addLayout(row)
        if installing:
            cv.addWidget(label(t("cmd_note"), "tagline", wrap=True))
        outer.addWidget(cmd_frame)

        outer.addStretch(1)
        self.setWidget(page)
        self.verticalScrollBar().setValue(0)

    @property
    def current(self) -> str | None:
        return self._app.name if self._app else None
