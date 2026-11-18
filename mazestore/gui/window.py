"""Main window: title bar, category sidebar, app grid / detail page, status line.

The Maze catalogue is the front page. Below the library, "More sources" opens
two search pages — the Arch repositories and the AUR — that reuse the header
search box: there it searches that source instead of filtering Maze apps.

Frameless with its own title bar, like Maze Guard and Maze Cloak: a 50px header
that drags the window (startSystemMove, so it works on Wayland), double-click
to maximise, and minimise / maximise / close on the right. Resizing from the
edges is handled here too, since dropping the system frame drops its borders.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PyQt6 import sip
from PyQt6.QtCore import QEvent, QFileSystemWatcher, QObject, QProcess, QSize, QTimer, Qt, QUrl
from PyQt6.QtGui import QAction, QCursor, QKeySequence, QShortcut
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLabel, QLineEdit,
                             QMainWindow, QMessageBox, QPushButton, QScrollArea,
                             QApplication, QStackedWidget, QVBoxLayout, QWidget)

from mazestore import __version__
from mazestore.core import actions, external, local, model, repo, settings, syscheck
from mazestore.core.catalog import CATEGORIES
from mazestore.core.dbparse import MAX_DB_BYTES
from mazestore.gui.flow import FlowLayout
from mazestore.gui.glass import GlassBackground, GlassFrame
from mazestore.gui.glyphs import glyph, glyph_pixmap
from mazestore.gui.i18n import t
from mazestore.gui.icons import app_logo, logo_pixmap
from mazestore.gui.pill import Pill
from mazestore.gui.switch import Switch
from mazestore.gui.widgets import (AppRow, DetailPage, ExtRow, FeaturedCard, SectionHeader,
                                   label)

_LIBRARY = ["installed", "updates"]
_EXT = ["arch", "aur"]
# Cards built per search: a broad AUR term matches thousands of packages, and
# a widget per result would stall the window. The rest is a search away.
_EXT_SHOWN = 120
_RESIZE_MARGIN = 6


class TitleBar(QWidget):
    """Draggable header. startSystemMove() is what makes this work on Wayland."""

    def __init__(self, window: QMainWindow):
        super().__init__(objectName="header")
        self._window = window
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self._window.windowHandle()
            if handle:
                handle.startSystemMove()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._window.showNormal() if self._window.isMaximized() else self._window.showMaximized()
        super().mouseDoubleClickEvent(event)


class WindowButton(QPushButton):
    """─ □ ✕ as drawn glyphs; the close button inverts to black on white."""

    def __init__(self, kind: str, tooltip: str):
        super().__init__(objectName="win_close" if kind == "win_close" else "win_btn")
        self._kind = kind
        self.setToolTip(tooltip)
        self.setIconSize(QSize(16, 16))
        self._paint(False)

    def set_kind(self, kind: str) -> None:
        self._kind = kind
        self._paint(self.underMouse())

    def _paint(self, hover: bool) -> None:
        colour = "#000000" if hover and self._kind == "win_close" else (
            "#f2f2f4" if hover else "#9a9aa0")
        self.setIcon(glyph(self._kind, 16, colour))

    def enterEvent(self, ev) -> None:
        self._paint(True)
        super().enterEvent(ev)

    def leaveEvent(self, ev) -> None:
        self._paint(False)
        super().leaveEvent(ev)


class _EdgeResizer(QObject):
    """Resize a frameless window from its edges.

    Watches mouse events application-wide, because the edges are covered by
    the sidebar, scroll areas and footer, none of which know they sit there.
    """

    def __init__(self, window: QMainWindow):
        super().__init__(window)
        self._w = window
        self._cursor_set = False

    def _edges(self, gpos) -> Qt.Edge:
        if self._w.isMaximized() or self._w.isFullScreen():
            return Qt.Edge(0)
        r = self._w.frameGeometry()
        m = _RESIZE_MARGIN
        e = Qt.Edge(0)
        if gpos.x() - r.left() < m:
            e |= Qt.Edge.LeftEdge
        if r.right() - gpos.x() < m:
            e |= Qt.Edge.RightEdge
        if gpos.y() - r.top() < m:
            e |= Qt.Edge.TopEdge
        if r.bottom() - gpos.y() < m:
            e |= Qt.Edge.BottomEdge
        return e

    @staticmethod
    def _shape(e: Qt.Edge) -> Qt.CursorShape | None:
        L, R, T, B = Qt.Edge.LeftEdge, Qt.Edge.RightEdge, Qt.Edge.TopEdge, Qt.Edge.BottomEdge
        if e in (L | T, R | B):
            return Qt.CursorShape.SizeFDiagCursor
        if e in (R | T, L | B):
            return Qt.CursorShape.SizeBDiagCursor
        if e & (L | R):
            return Qt.CursorShape.SizeHorCursor
        if e & (T | B):
            return Qt.CursorShape.SizeVerCursor
        return None

    def eventFilter(self, obj, ev) -> bool:
        t_ = ev.type()
        if t_ not in (QEvent.Type.MouseMove, QEvent.Type.MouseButtonPress, QEvent.Type.HoverMove):
            return False
        if not isinstance(obj, QWidget) or obj.window() is not self._w:
            return False
        gpos = QCursor.pos()
        edges = self._edges(gpos)
        shape = self._shape(edges)
        if t_ == QEvent.Type.MouseButtonPress and shape is not None \
                and ev.button() == Qt.MouseButton.LeftButton:
            handle = self._w.windowHandle()
            if handle and handle.startSystemResize(edges):
                return True
        if shape is not None:
            if not self._cursor_set:
                QApplication.setOverrideCursor(shape)
                self._cursor_set = True
            else:
                QApplication.changeOverrideCursor(shape)
        elif self._cursor_set:
            QApplication.restoreOverrideCursor()
            self._cursor_set = False
        return False


class NavItem(QPushButton):
    """Sidebar entry: glyph, name, and an optional count on the right.

    The labels inside a QPushButton cannot follow its :checked state through
    QSS, so the colours are switched here when the button toggles.
    """

    def __init__(self, key: str, text: str):
        super().__init__(objectName="nav")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(38)
        self._key = key
        h = QHBoxLayout(self)
        h.setContentsMargins(12, 0, 12, 0)
        h.setSpacing(11)
        self._icon = QLabel()
        self._text = QLabel(text, objectName="nav_text")
        self._count = QLabel("", objectName="nav_count")
        for w in (self._icon, self._text, self._count):
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        h.addWidget(self._icon)
        h.addWidget(self._text, 1)
        h.addWidget(self._count)
        self.toggled.connect(self._restyle)
        self._restyle(False)

    def set_count(self, n: int) -> None:
        self._count.setText(str(n) if n else "")

    def _restyle(self, on: bool) -> None:
        colour = "#f2f2f4" if on else "#8f8f95"
        self._icon.setPixmap(glyph_pixmap(self._key, 18, colour))
        self._text.setStyleSheet(f"color: {colour}; font-weight: {'600' if on else '400'};")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Maze Store")
        self.setWindowIcon(app_logo())
        self.resize(1240, 820)
        self.setMinimumSize(820, 560)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setMouseTracking(True)
        self._resizer = _EdgeResizer(self)
        QApplication.instance().installEventFilter(self._resizer)

        self._catalogue = repo.Catalogue({}, "none", 0.0)
        self._apps: list[model.App] = []
        self._view = "all"
        self._busy: dict[str, QProcess] = {}      # package → its terminal
        # Every pending repository update (syscheck, run in a child process):
        # name → {old, new, repo, url, depends}. None until the first check
        # answers or when it failed. `_checking`: packages whose install
        # waits on a running check, so their dependencies can be looked at.
        self._pending: dict[str, dict] | None = None
        self._check_proc: QProcess | None = None
        self._checking: list[str] = []
        # AUR builds (pacman -Qm) that the AUR has a newer version of.
        self._aur_updates: list[external.ExtPackage] = []
        self._aur_checking = 0
        self._fetching = False
        self._offline = False
        self._net = QNetworkAccessManager(self)
        self._installed: dict[str, str] = {}
        # Per source: results, what was searched, and "idle" / "short" /
        # "searching" / "done" / "error" (+ the error text).
        self._ext: dict[str, list[external.ExtPackage]] = {k: [] for k in _EXT}
        self._ext_query: dict[str, str] = {k: "" for k in _EXT}
        self._ext_state: dict[str, tuple[str, str]] = {k: ("idle", "") for k in _EXT}
        self._ext_proc: QProcess | None = None
        self._ext_reply: QNetworkReply | None = None
        self._ext_timer = QTimer(self, singleShot=True, interval=350)
        self._ext_timer.timeout.connect(self._ext_search)

        self._build_ui()

        # pacman rewrites /var/lib/pacman/local on every install/remove: watching
        # it is how the store notices a transaction finished, whatever terminal
        # (or other tool) ran it. Debounced — one transaction is many events.
        self._reload_timer = QTimer(self, singleShot=True, interval=700)
        self._reload_timer.timeout.connect(self._reload_local)
        self._watcher = QFileSystemWatcher(self)
        for d in (str(local.LOCAL_DB), str(repo.SYNC_DB.parent)):
            self._watcher.addPath(d)
        self._watcher.directoryChanged.connect(lambda _p: self._reload_timer.start())

        self._age_timer = QTimer(self, interval=30_000)
        self._age_timer.timeout.connect(self._update_status)
        self._age_timer.start()

        self._reload_local()
        self.refresh()
        # Typing should search, but a focused field on launch hides the
        # placeholder and draws the focus ring before the user did anything.
        self._grid_scroll.setFocus()

    # ── layout ─────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        root = GlassBackground()
        v = QVBoxLayout(root)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        header = TitleBar(self)
        header.setFixedHeight(50)
        h = QHBoxLayout(header)
        h.setContentsMargins(16, 0, 0, 0)
        h.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(logo_pixmap(28))
        h.addWidget(logo)
        h.addWidget(label("MAZE STORE", "wordmark"))
        h.addStretch(1)
        self._search = QLineEdit(objectName="search")
        self._search.setPlaceholderText(t("search"))
        self._search.setClearButtonEnabled(True)
        self._search.setFixedWidth(380)
        self._search.addAction(QAction(glyph("search", 16, "#8f8f95"), "", self._search),
                               QLineEdit.ActionPosition.LeadingPosition)
        self._search.textChanged.connect(self._on_search_text)
        h.addWidget(self._search)
        h.addStretch(1)
        self._update_all = QPushButton(objectName="get")
        self._update_all.setIcon(glyph("updates", 15, "#000000"))
        self._update_all.setIconSize(QSize(15, 15))
        self._update_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_all.clicked.connect(lambda: self._run("upgrade", []))
        h.addWidget(self._update_all)
        self._refresh_btn = QPushButton(objectName="round")
        self._refresh_btn.setIcon(glyph("updates", 17))
        self._refresh_btn.setIconSize(QSize(17, 17))
        self._refresh_btn.setFixedSize(32, 32)
        self._refresh_btn.setToolTip(t("btn_refresh") + "  (F5)")
        self._refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_btn.clicked.connect(self.refresh)
        h.addWidget(self._refresh_btn)
        h.addSpacing(10)
        sep = QFrame(objectName="vline")
        sep.setFixedSize(1, 22)
        h.addWidget(sep)
        self._min_btn = WindowButton("win_min", t("tip_minimize"))
        self._min_btn.clicked.connect(self.showMinimized)
        self._max_btn = WindowButton("win_max", t("tip_maximize"))
        self._max_btn.clicked.connect(
            lambda: self.showNormal() if self.isMaximized() else self.showMaximized())
        self._close_btn = WindowButton("win_close", t("tip_close"))
        self._close_btn.clicked.connect(self.close)
        for b in (self._min_btn, self._max_btn, self._close_btn):
            h.addWidget(b)
        v.addWidget(header)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        side = QWidget(objectName="sidebar")
        side.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        side.setFixedWidth(232)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(14, 10, 14, 14)
        sv.setSpacing(3)
        self._nav = QButtonGroup(self)
        self._nav.setExclusive(True)
        self._nav_buttons: dict[str, NavItem] = {}
        sv.addWidget(label(t("nav_browse"), "navlabel"))
        for cat in CATEGORIES:
            sv.addWidget(self._nav_button(cat, t(f"cat_{cat}")))
        sv.addSpacing(8)
        sv.addWidget(label(t("nav_library"), "navlabel"))
        for lib in _LIBRARY:
            sv.addWidget(self._nav_button(lib, t(f"lib_{lib}")))
        sv.addSpacing(8)
        sv.addWidget(label(t("nav_sources"), "navlabel"))
        for src in _EXT:
            sv.addWidget(self._nav_button(src, t(f"src_{src}")))
        sv.addStretch(1)
        notif = GlassFrame(radius=14)
        nl = QHBoxLayout(notif)
        nl.setContentsMargins(12, 10, 12, 10)
        nl.setSpacing(10)
        txt = QVBoxLayout()
        txt.setSpacing(1)
        txt.addWidget(label(t("notify_title"), "nav_text"))
        hint = label(t("notify_hint"), "meta", wrap=True)
        txt.addWidget(hint)
        nl.addLayout(txt, 1)
        self._notify_switch = Switch(settings.load()["notify_updates"])
        self._notify_switch.toggled.connect(
            lambda on: settings.save({"notify_updates": on}))
        nl.addWidget(self._notify_switch, 0, Qt.AlignmentFlag.AlignVCenter)
        sv.addWidget(notif)
        sv.addSpacing(8)
        sv.addWidget(label(f"Maze Store {__version__}", "meta"))
        self._nav_buttons["all"].setChecked(True)
        body.addWidget(side)

        self._stack = QStackedWidget()
        self._grid_scroll = QScrollArea()
        self._grid_scroll.setWidgetResizable(True)
        self._grid_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._grid_scroll.viewport().setAutoFillBackground(False)
        self._stack.addWidget(self._grid_scroll)
        self._detail = DetailPage()
        self._detail.back.connect(self._show_grid)
        self._detail.action.connect(self._on_action)
        self._stack.addWidget(self._detail)
        body.addWidget(self._stack, 1)
        v.addLayout(body, 1)

        footer = QWidget(objectName="footer")
        footer.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        footer.setFixedHeight(30)
        fh = QHBoxLayout(footer)
        fh.setContentsMargins(22, 0, 22, 0)
        self._dot = QLabel(objectName="dot")
        self._dot.setFixedSize(7, 7)
        fh.addWidget(self._dot)
        fh.addSpacing(4)
        self._status = label("", "statusbar")
        fh.addWidget(self._status)
        fh.addStretch(1)
        self._src_label = label("[mazelinux]", "statusbar")
        fh.addWidget(self._src_label)
        v.addWidget(footer)

        self.setCentralWidget(root)

        QShortcut(QKeySequence("Ctrl+F"), self, activated=self._search.setFocus)
        QShortcut(QKeySequence("F5"), self, activated=self.refresh)
        QShortcut(QKeySequence("Esc"), self, activated=self._on_escape)

    def _nav_button(self, key: str, text: str) -> NavItem:
        b = NavItem(key, text)
        b.clicked.connect(lambda: self._set_view(key))
        self._nav.addButton(b)
        self._nav_buttons[key] = b
        return b

    def changeEvent(self, ev) -> None:
        if ev.type() == QEvent.Type.WindowStateChange:
            self._max_btn.set_kind("win_restore" if self.isMaximized() else "win_max")
        super().changeEvent(ev)

    # ── data ───────────────────────────────────────────────────────────────
    def _reload_local(self) -> None:
        cat = repo.load_local()
        # Keep a network copy we already hold if the disk has nothing newer.
        if cat.source != "none" and (self._catalogue.source == "none"
                                     or cat.mtime >= self._catalogue.mtime):
            if self._catalogue.source == "network" and cat.source == "cache":
                cat.source = "network"
            self._catalogue = cat
        installed = local.installed()
        self._installed = installed
        for pkgs in self._ext.values():
            external.mark_installed(pkgs, installed)
        self._apps = model.build(self._catalogue.packages, installed)
        self._render()

    def refresh(self) -> None:
        self._check_pending()
        self._check_aur()
        if self._fetching:
            return
        self._fetching = True
        self._refresh_btn.setEnabled(False)
        self._update_status()
        req = QNetworkRequest(QUrl(repo.fetch_url()))
        req.setTransferTimeout(20_000)
        req.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                         QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy)
        req.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, f"maze-store/{__version__}")
        reply = self._net.get(req)

        def _progress(received: int, _total: int) -> None:
            if received > MAX_DB_BYTES:
                reply.abort()
        reply.downloadProgress.connect(_progress)
        reply.finished.connect(lambda: self._on_fetched(reply))

    def _on_fetched(self, reply: QNetworkReply) -> None:
        # The db first, then its signature; nothing is cached until both are
        # in and the signature checks out (repo.save_cache, audit ST1).
        if reply.error() != QNetworkReply.NetworkError.NoError:
            reply.deleteLater()
            self._fetch_done(False)
            return
        data = bytes(reply.readAll())
        reply.deleteLater()
        req = QNetworkRequest(QUrl(repo.sig_url()))
        req.setTransferTimeout(20_000)
        req.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                         QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy)
        req.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, f"maze-store/{__version__}")
        sig_reply = self._net.get(req)
        sig_reply.downloadProgress.connect(
            lambda received, _t: sig_reply.abort() if received > 64 * 1024 else None)
        sig_reply.finished.connect(lambda: self._on_sig_fetched(sig_reply, data))

    def _on_sig_fetched(self, reply: QNetworkReply, data: bytes) -> None:
        ok = False
        if reply.error() == QNetworkReply.NetworkError.NoError:
            try:
                repo.save_cache(data, bytes(reply.readAll()))
                ok = True
            except (ValueError, OSError):
                ok = False
        reply.deleteLater()
        self._fetch_done(ok)

    def _fetch_done(self, ok: bool) -> None:
        self._fetching = False
        self._refresh_btn.setEnabled(True)
        self._offline = not ok
        self._reload_local()
        if ok:
            self._catalogue.source = "network"
        self._update_status()

    # ── rendering ──────────────────────────────────────────────────────────
    def set_view(self, key: str) -> None:
        if key in self._nav_buttons:
            self._set_view(key)

    def _set_view(self, key: str) -> None:
        self._view = key
        self._nav_buttons[key].setChecked(True)
        self._search.setPlaceholderText(t(f"search_{key}") if key in _EXT else t("search"))
        self._src_label.setText({"arch": "core · extra · multilib",
                                 "aur": "aur.archlinux.org"}.get(key, "[mazelinux]"))
        if key in _EXT and self._ext_query[key] != self._search.text().strip():
            self._ext_search()
        self._show_grid()
        self._grid_scroll.verticalScrollBar().setValue(0)
        self._render()

    def _show_grid(self) -> None:
        self._stack.setCurrentIndex(0)

    def _on_escape(self) -> None:
        if self._stack.currentIndex() == 1:
            self._show_grid()
        elif self._search.text():
            self._search.clear()

    def _render(self) -> None:
        query = self._search.text()
        updates = [a for a in self._apps if a.state == "update"]
        installed = [a for a in self._apps if a.installed is not None]
        arch_updates = self._arch_updates()
        n_all = len(updates) + len(arch_updates) + len(self._aur_updates)
        self._update_all.setText(" " + t("btn_update_all", n=n_all))
        self._update_all.setVisible(bool(n_all))
        self._update_all.setEnabled("__upgrade__" not in self._busy)
        self._nav_buttons["updates"].set_count(n_all)
        self._nav_buttons["installed"].set_count(len(installed))

        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(30, 26, 30, 30)
        v.setSpacing(14)

        if self._view in _EXT:
            self._ext_page(v)
            v.addStretch(1)
            pos = self._grid_scroll.verticalScrollBar().value()
            self._grid_scroll.setWidget(page)
            self._grid_scroll.verticalScrollBar().setValue(pos)
            self._update_status()
            return

        shown = model.select(self._apps, self._view, query)
        browsing = self._view == "all" and not query.strip()

        if self._view == "updates":
            self._updates_page(v, shown, arch_updates, query)
            v.addStretch(1)
            pos = self._grid_scroll.verticalScrollBar().value()
            self._grid_scroll.setWidget(page)
            self._grid_scroll.verticalScrollBar().setValue(pos)
            self._update_status()
            return

        if browsing:
            v.addWidget(self._hero(len(self._apps), len(installed), len(updates)))
            featured = [a for a in shown if a.entry.featured]
            rest = [a for a in shown if not a.entry.featured]
            if featured:
                v.addWidget(SectionHeader(t("sec_featured"), t("sec_featured_sub")))
                v.addWidget(self._grid(featured, FeaturedCard, 430))
            if rest:
                v.addWidget(SectionHeader(t("sec_all"), t("sec_all_sub")))
                v.addWidget(self._grid(rest, AppRow, 330))
        else:
            if query.strip():
                title = t("sec_results")
            elif self._view in CATEGORIES:
                title = t(f"cat_{self._view}")
            else:
                title = t(f"lib_{self._view}")
            v.addWidget(SectionHeader(title, t("count_apps", n=len(shown)) if shown else ""))
            if shown:
                v.addWidget(self._grid(shown, AppRow, 330))

        if not shown:
            if not self._apps:
                msg = t("empty_repo")
            elif query.strip():
                msg = t("empty_search", q=query.strip())
            elif self._view == "installed":
                msg = t("empty_installed")
            elif self._view == "updates":
                msg = t("empty_updates")
            else:
                msg = ""
            if msg:
                e = label(msg, "empty", wrap=True)
                e.setAlignment(Qt.AlignmentFlag.AlignCenter)
                v.addSpacing(70)
                v.addWidget(e)
        v.addStretch(1)

        pos = self._grid_scroll.verticalScrollBar().value()
        self._grid_scroll.setWidget(page)
        self._grid_scroll.verticalScrollBar().setValue(pos)

        # Keep an open detail page in step with the new state.
        if self._stack.currentIndex() == 1 and self._detail.current:
            app = self._find(self._detail.current)
            if app is not None:
                self._detail.show_app(app, self._is_busy(app.name), self._can_open(app.name))
        self._update_status()

    def _hero(self, n_apps: int, n_installed: int, n_updates: int) -> QFrame:
        hero = GlassFrame(radius=28, tint="#ffffff", strength=1.1)
        hero.setMinimumHeight(200)
        h = QHBoxLayout(hero)
        h.setContentsMargins(38, 34, 38, 34)
        h.setSpacing(30)
        col = QVBoxLayout()
        col.setSpacing(10)
        col.addWidget(label(t("hero_eyebrow"), "eyebrow"))
        col.addWidget(label(t("hero_title"), "hero_title", wrap=True))
        col.addWidget(label(t("hero_sub"), "hero_sub", wrap=True))
        col.addSpacing(6)
        chips = QHBoxLayout()
        chips.setSpacing(8)
        chips.addWidget(Pill(t("count_apps", n=n_apps), "chip", size="large"))
        chips.addWidget(Pill(t("chip_installed", n=n_installed), "chip", size="large"))
        if n_updates:
            chips.addWidget(Pill(t("chip_updates", n=n_updates), "update", size="large"))
        chips.addStretch(1)
        col.addLayout(chips)
        h.addLayout(col, 1)
        logo = QLabel()
        logo.setPixmap(logo_pixmap(136))
        h.addWidget(logo, 0, Qt.AlignmentFlag.AlignVCenter)
        return hero

    # ── Arch repositories / AUR ────────────────────────────────────────────
    def _on_search_text(self, _text: str) -> None:
        if self._view in _EXT:
            self._ext_timer.start()
        else:
            self._render()

    def _ext_search(self) -> None:
        """Search the current source for what is in the box. Results that
        arrive for an older query are dropped, so fast typing never shows a
        stale list."""
        src = self._view
        if src not in _EXT:
            return
        query = self._search.text().strip()
        words = external.clean_query(query)
        self._ext_query[src] = query
        if src == "arch" and self._ext_proc is not None:
            self._ext_proc.kill()
            self._ext_proc = None
        if src == "aur" and self._ext_reply is not None:
            self._ext_reply.abort()
            self._ext_reply = None
        if not words:
            self._ext[src], self._ext_state[src] = [], ("idle", "")
        elif src == "aur" and len(external.aur_term(words)) < external.AUR_MIN_TERM:
            self._ext[src], self._ext_state[src] = [], ("short", "")
        else:
            self._ext_state[src] = ("searching", "")
            (self._search_arch if src == "arch" else self._search_aur)(query, words)
        self._render()

    def _ext_done(self, src: str, query: str, pkgs: list[external.ExtPackage] | None,
                  error: str = "") -> None:
        if self._ext_query[src] != query:
            return
        if pkgs is None:
            self._ext[src], self._ext_state[src] = [], ("error", error)
        else:
            external.mark_installed(pkgs, self._installed)
            self._ext[src] = external.rank(pkgs, external.clean_query(query))
            self._ext_state[src] = ("done", "")
        if self._view == src:
            self._render()

    def _search_arch(self, query: str, words: list[str]) -> None:
        proc = QProcess(self)
        self._ext_proc = proc
        proc.setProgram("pacman")
        proc.setArguments(external.pacman_search_argv(words)[1:])

        def _finished(*_a) -> None:
            if self._ext_proc is proc:
                self._ext_proc = None
            # pacman -Ss exits 1 when nothing matches: an empty list, not an error.
            out = bytes(proc.readAllStandardOutput()).decode("utf-8", "replace")
            proc.deleteLater()
            self._ext_done("arch", query, external.parse_pacman_ss(out))

        def _failed(err) -> None:
            if err == QProcess.ProcessError.FailedToStart:
                if self._ext_proc is proc:
                    self._ext_proc = None
                proc.deleteLater()
                self._ext_done("arch", query, None, "pacman")
        proc.finished.connect(_finished)
        proc.errorOccurred.connect(_failed)
        proc.start()

    def _search_aur(self, query: str, words: list[str]) -> None:
        req = QNetworkRequest(QUrl(external.aur_search_url(words)))
        req.setTransferTimeout(20_000)
        req.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                         QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy)
        req.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, f"maze-store/{__version__}")
        reply = self._net.get(req)
        self._ext_reply = reply
        reply.downloadProgress.connect(
            lambda received, _t: reply.abort() if received > external.MAX_AUR_BYTES else None)

        def _finished() -> None:
            if self._ext_reply is reply:
                self._ext_reply = None
            err = reply.error()
            data = bytes(reply.readAll())
            why = reply.errorString()
            reply.deleteLater()
            if err == QNetworkReply.NetworkError.OperationCanceledError:
                return  # superseded by a newer search
            if err != QNetworkReply.NetworkError.NoError:
                self._ext_done("aur", query, None, why)
                return
            try:
                self._ext_done("aur", query, external.parse_aur(data, words))
            except ValueError as exc:
                self._ext_done("aur", query, None, str(exc))
        reply.finished.connect(_finished)

    def _ext_page(self, v: QVBoxLayout) -> None:
        src = self._view
        helper = actions.aur_helper()
        hero = GlassFrame(radius=24, tint="#ffffff", strength=0.9)
        hl = QHBoxLayout(hero)
        hl.setContentsMargins(30, 24, 30, 24)
        hl.setSpacing(22)
        ic = QLabel()
        ic.setPixmap(glyph_pixmap(src, 56, "#f2f2f4"))
        hl.addWidget(ic, 0, Qt.AlignmentFlag.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(6)
        col.addWidget(label(t(f"{src}_eyebrow"), "eyebrow"))
        col.addWidget(label(t(f"{src}_title"), "feature_title"))
        col.addWidget(label(t(f"{src}_sub", helper=helper or "paru"), "hero_sub", wrap=True))
        if src == "aur" and helper is None:
            col.addSpacing(4)
            row = QHBoxLayout()
            row.setSpacing(12)
            row.addWidget(label(t("aur_no_helper"), "tagline", wrap=True), 1)
            get = QPushButton(t("btn_get_paru"), objectName="get")
            get.setCursor(Qt.CursorShape.PointingHandCursor)
            get.setEnabled(not self._is_busy("paru"))
            get.clicked.connect(lambda: self._run("install", ["paru"]))
            row.addWidget(get, 0, Qt.AlignmentFlag.AlignVCenter)
            col.addLayout(row)
        hl.addLayout(col, 1)
        v.addWidget(hero)

        state, why = self._ext_state[src]
        pkgs = self._ext[src]
        if state == "done" and pkgs:
            v.addWidget(SectionHeader(t("sec_results"), t("count_pkgs", n=len(pkgs))))
            w = QWidget()
            flow = FlowLayout(w, spacing=14, min_item_width=420)
            for pkg in pkgs[:_EXT_SHOWN]:
                card = ExtRow(pkg, self._is_busy(pkg.name))
                card.action.connect(self._on_action)
                flow.addWidget(card)
            v.addWidget(w)
            if len(pkgs) > _EXT_SHOWN:
                more = label(t("ext_more", shown=_EXT_SHOWN, n=len(pkgs)), "meta")
                more.setAlignment(Qt.AlignmentFlag.AlignCenter)
                v.addWidget(more)
            return
        msg = {
            "idle": t("ext_hint"),
            "short": t("ext_short", n=external.AUR_MIN_TERM),
            "searching": t("ext_searching"),
            "error": t("ext_error", why=why),
            "done": t("empty_search", q=self._ext_query[src]),
        }[state]
        e = label(msg, "empty", wrap=True)
        e.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addSpacing(60)
        v.addWidget(e)

    # ── updates from every source ──────────────────────────────────────────
    def _arch_updates(self) -> list[external.ExtPackage]:
        """Pending updates from the Arch repositories (Maze ones are cards)."""
        if not self._pending:
            return []
        return [external.ExtPackage(n, d["new"], d.get("desc", ""), "arch",
                                    repo=d.get("repo", ""), installed=d["old"])
                for n, d in sorted(self._pending.items())
                if d.get("repo") != repo.REPO]

    def _updates_page(self, v: QVBoxLayout, maze: list[model.App],
                      arch: list[external.ExtPackage], query: str) -> None:
        q = query.casefold().strip()

        def match(p: external.ExtPackage) -> bool:
            return all(w in f"{p.name} {p.desc}".casefold() for w in q.split())
        arch = [p for p in arch if match(p)]
        aur = [p for p in self._aur_updates if match(p)]
        # AUR before Arch: a few cards, not buried under a long Arch list.
        sections = [
            ("Maze", maze, t("upd_maze_sub"), None),
            ("AUR", aur, t("upd_aur_sub"),
             t("upd_checking") if self._aur_checking else None),
            (t("src_arch"), arch, t("upd_arch_sub"),
             t("upd_checking") if self._check_proc is not None and self._pending is None
             else t("upd_check_failed") if self._pending is None else None),
        ]
        any_shown = False
        for title, items, sub, note in sections:
            if not items and not note:
                continue
            any_shown = True
            v.addWidget(SectionHeader(title, (t("count_pkgs", n=len(items)) + " · " + sub)
                                      if items else sub))
            if items and isinstance(items[0], model.App):
                v.addWidget(self._grid(items, AppRow, 330))
            elif items:
                w = QWidget()
                flow = FlowLayout(w, spacing=14, min_item_width=420)
                # Every update is listed: a pending one must not hide.
                for pkg in items:
                    card = ExtRow(pkg, self._is_busy(pkg.name))
                    card.action.connect(self._on_action)
                    flow.addWidget(card)
                v.addWidget(w)
            else:
                v.addWidget(label(note, "meta"))
        if not any_shown:
            e = label(t("empty_search", q=query.strip()) if q else t("empty_updates"),
                      "empty", wrap=True)
            e.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v.addSpacing(70)
            v.addWidget(e)

    def _check_pending(self) -> None:
        if self._check_proc is not None:
            return
        main = Path(__file__).resolve().parents[2] / "main.py"
        proc = QProcess(self)
        proc.setProgram(sys.executable)
        proc.setArguments([str(main), "--pending-upgrades"])
        self._check_proc = proc

        def _done(*_a) -> None:
            # Also fires while the window is being torn down, proc already gone.
            if self._check_proc is not proc or sip.isdeleted(proc):
                return
            self._check_proc = None
            ok = (proc.exitStatus() == QProcess.ExitStatus.NormalExit
                  and proc.exitCode() == 0)
            out = bytes(proc.readAllStandardOutput()).decode("utf-8", "replace")
            proc.deleteLater()
            items = syscheck.parse_output(out) if ok else None
            self._pending = None if items is None else {i["name"]: i for i in items}
            waiting, self._checking = self._checking, []
            self._render()
            for name in waiting:
                self._install_one(name)
        proc.finished.connect(_done)
        proc.errorOccurred.connect(
            lambda err: _done() if err == QProcess.ProcessError.FailedToStart else None)
        proc.start()
        self._render()

    def _check_aur(self) -> None:
        if self._aur_checking:
            return
        try:
            out = subprocess.run(external.foreign_argv(), capture_output=True, text=True,
                                 timeout=15, env={**os.environ, "LC_ALL": "C"}).stdout
        except (OSError, subprocess.SubprocessError):
            return
        foreign = external.parse_foreign(out)
        urls = external.aur_info_urls(list(foreign))
        if not urls:
            self._aur_updates = []
            return
        found: list[external.ExtPackage] = []
        self._aur_checking = len(urls)
        for url in urls:
            req = QNetworkRequest(QUrl(url))
            req.setTransferTimeout(20_000)
            req.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                             QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy)
            req.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader,
                          f"maze-store/{__version__}")
            reply = self._net.get(req)

            def _finished(reply=reply) -> None:
                if reply.error() == QNetworkReply.NetworkError.NoError:
                    try:
                        found.extend(external.parse_aur(bytes(reply.readAll()), []))
                    except ValueError:
                        pass
                reply.deleteLater()
                self._aur_checking -= 1
                if self._aur_checking == 0:
                    self._aur_updates = external.aur_updates(found, self._installed or foreign)
                    self._render()
            reply.finished.connect(_finished)

    def _grid(self, apps: list[model.App], card_cls, min_w: int) -> QWidget:
        w = QWidget()
        flow = FlowLayout(w, spacing=14, min_item_width=min_w)
        for app in apps:
            card = card_cls(app, self._is_busy(app.name), self._can_open(app.name))
            card.opened.connect(self._open_detail)
            card.action.connect(self._on_action)
            flow.addWidget(card)
        return w

    def _open_detail(self, name: str) -> None:
        app = self._find(name)
        if app is None:
            return
        self._detail.show_app(app, self._is_busy(name), self._can_open(name))
        self._stack.setCurrentIndex(1)

    def _find(self, name: str) -> model.App | None:
        return next((a for a in self._apps if a.name == name), None)

    def _update_status(self) -> None:
        live = not self._fetching and not self._offline and self._catalogue.source != "none"
        self._dot.setStyleSheet(
            "background: %s; border-radius: 3px;" % ("#f2f2f4" if live else "#4a4a4f"))
        if self._checking:
            self._status.setText(t("upd_checking"))
            return
        if self._view in _EXT:
            self._status.setText(t("status_ext", src=t(f"src_{self._view}"),
                                   n=len(self._ext[self._view])))
            return
        if self._fetching:
            self._status.setText(t("src_fetching"))
            return
        cat = self._catalogue
        src = t(f"src_{cat.source}")
        if self._offline:
            src += f" ({t('src_offline')})"
        age = repo.age_seconds(cat)
        if age < 90:
            a = t("age_now")
        elif age < 3600:
            a = t("age_min", n=int(age // 60))
        elif age < 86400:
            a = t("age_hour", n=int(age // 3600))
        else:
            a = t("age_day", n=int(age // 86400))
        self._status.setText(t("status_line", src=src, n=len(self._apps), age=a))

    # ── actions ────────────────────────────────────────────────────────────
    def _is_busy(self, name: str) -> bool:
        return name in self._busy or name in self._checking

    def _can_open(self, name: str) -> bool:
        return any(local.exec_argv(d) for d in local.desktop_entries(name))

    def _on_action(self, action: str, name: str) -> None:
        if action == "open":
            self._launch(name)
            return
        if action == "aur-install":
            helper = actions.aur_helper()
            if helper is None:
                ans = QMessageBox.question(self, t("paru_title"), t("paru_body"))
                if ans == QMessageBox.StandardButton.Yes:
                    self._run("install", ["paru"])
                return
            ans = QMessageBox.warning(
                self, t("aur_confirm_title"), t("aur_confirm_body", name=name, helper=helper),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if ans != QMessageBox.StandardButton.Yes:
                return
        if action == "remove":
            app = self._find(name)
            if app is not None and app.entry.core:
                ans = QMessageBox.warning(
                    self, t("core_title"), t("core_body", name=app.entry.title),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No)
                if ans != QMessageBox.StandardButton.Yes:
                    return
        self._run(action, [name])

    def _launch(self, name: str) -> None:
        for d in local.desktop_entries(name):
            argv = local.exec_argv(d)
            if argv and QProcess.startDetached(argv[0], argv[1:])[0]:
                return
        QMessageBox.information(self, "Maze Store", t("open_fail"))

    def _run(self, action: str, packages: list[str]) -> None:
        if action == "install" and len(packages) == 1:
            self._install_one(packages[0])
        elif action == "upgrade":
            # With AUR updates and a helper, one `paru -Syu` covers both.
            if self._aur_updates and actions.aur_helper():
                self._start_terminal("full-upgrade", [])
            else:
                self._start_terminal("upgrade", [])
        else:
            self._start_terminal(action, packages)

    def _install_one(self, name: str) -> None:
        """Install or update just this package.

        A Maze app or a pending repository update is installed from its file
        (`pacman -U <url>`), without refreshing the system's databases. If any
        of its dependencies has a pending update itself, the new build may
        need it, so the user picks: just this, or the whole system.
        A package with no file to point at (a new Arch package) is installed
        from the databases as they are (`pacman -S --needed`).
        """
        app = self._find(name)
        pend = (self._pending or {}).get(name)
        url, deps = "", []
        if app is not None and app.state in ("available", "update") and app.pkg.filename:
            url, deps = repo.package_url(app.pkg.filename), [
                syscheck.dep_name(d) for d in app.pkg.depends]
        elif pend and pend.get("url"):
            url, deps = pend["url"], list(pend.get("depends") or [])
        if not url:
            self._start_terminal("install-only", [name])
            return
        if self._pending is None and self._check_proc is not None:
            # The dependency check is still running: finish it first.
            if name not in self._checking:
                self._checking.append(name)
            self._render()
            return
        stale = [(d, self._pending[d]) for d in deps if self._pending and d in self._pending]
        if not stale:
            self._start_terminal("install-file", [url], busy=[name])
            return
        listed = "\n".join(f"{d}  {i['old']} → {i['new']}" for d, i in stale[:8])
        if len(stale) > 8:
            listed += "\n…"
        box = QMessageBox(QMessageBox.Icon.Question, t("one_title"),
                          t("one_body", name=name, list=listed), parent=self)
        only = box.addButton(t("one_only"), QMessageBox.ButtonRole.AcceptRole)
        whole = box.addButton(t("one_all"), QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.setDefaultButton(only)
        box.exec()
        if box.clickedButton() is only:
            self._start_terminal("install-file", [url], busy=[name])
        elif box.clickedButton() is whole:
            self._start_terminal("install", [name])

    def _start_terminal(self, action: str, packages: list[str],
                        busy: list[str] | None = None) -> None:
        try:
            argv = actions.terminal_argv(action, packages)
        except (RuntimeError, ValueError) as exc:
            cmd = actions.display_command(action, packages) if action in actions.ACTIONS else ""
            QMessageBox.critical(self, t("err_title"),
                                 t("err_body", why=str(exc), cmd=cmd))
            return
        proc = QProcess(self)
        proc.setProgram(argv[0])
        proc.setArguments(argv[1:])

        def _gone(*_a) -> None:
            # Drop every reference before the QProcess is deleted: touching it
            # afterwards raises in a Qt slot, and PyQt aborts the whole app.
            for n in [n for n, p in self._busy.items() if p is proc]:
                del self._busy[n]
            proc.deleteLater()
            self._reload_timer.start()
            # Whatever ran changed what is pending.
            self._check_pending()
            self._check_aur()
        proc.finished.connect(_gone)
        proc.errorOccurred.connect(
            lambda err: _gone() if err == QProcess.ProcessError.FailedToStart else None)
        proc.start()
        for n in busy or packages or ["__upgrade__"]:
            self._busy[n] = proc
        self._render()
