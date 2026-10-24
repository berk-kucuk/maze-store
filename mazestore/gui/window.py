"""Main window: title bar, category sidebar, app grid / detail page, status line.

Frameless with its own title bar, like Maze Guard and Maze Cloak: a 50px header
that drags the window (startSystemMove, so it works on Wayland), double-click
to maximise, and minimise / maximise / close on the right. Resizing from the
edges is handled here too, since dropping the system frame drops its borders.
"""
from __future__ import annotations

from PyQt6.QtCore import QEvent, QFileSystemWatcher, QObject, QProcess, QSize, QTimer, Qt, QUrl
from PyQt6.QtGui import QAction, QCursor, QKeySequence, QShortcut
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLabel, QLineEdit,
                             QMainWindow, QMessageBox, QPushButton, QScrollArea,
                             QApplication, QStackedWidget, QVBoxLayout, QWidget)

from mazestore import __version__
from mazestore.core import actions, local, model, repo, settings
from mazestore.core.catalog import CATEGORIES
from mazestore.core.dbparse import MAX_DB_BYTES
from mazestore.gui.flow import FlowLayout
from mazestore.gui.glass import GlassBackground, GlassFrame
from mazestore.gui.glyphs import glyph, glyph_pixmap
from mazestore.gui.i18n import t
from mazestore.gui.icons import app_logo, logo_pixmap
from mazestore.gui.pill import Pill
from mazestore.gui.switch import Switch
from mazestore.gui.widgets import AppRow, DetailPage, FeaturedCard, SectionHeader, label

_LIBRARY = ["installed", "updates"]
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
        self._fetching = False
        self._offline = False
        self._net = QNetworkAccessManager(self)

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
        self._search.textChanged.connect(lambda _t: self._render())
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
        fh.addWidget(label("[mazelinux]", "statusbar"))
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
        # A busy package whose terminal has gone is no longer busy.
        for name, proc in list(self._busy.items()):
            if proc.state() == QProcess.ProcessState.NotRunning:
                del self._busy[name]
        self._apps = model.build(self._catalogue.packages, installed)
        self._render()

    def refresh(self) -> None:
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
        self._fetching = False
        self._refresh_btn.setEnabled(True)
        ok = False
        if reply.error() == QNetworkReply.NetworkError.NoError:
            try:
                repo.save_cache(bytes(reply.readAll()))
                ok = True
            except (ValueError, OSError):
                ok = False
        reply.deleteLater()
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
        self._update_all.setText(" " + t("btn_update_all", n=len(updates)))
        self._update_all.setVisible(bool(updates))
        self._nav_buttons["updates"].set_count(len(updates))
        self._nav_buttons["installed"].set_count(len(installed))

        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(30, 26, 30, 30)
        v.setSpacing(14)

        shown = model.select(self._apps, self._view, query)
        browsing = self._view == "all" and not query.strip()

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
                self._detail.show_app(app, app.name in self._busy, self._can_open(app.name))
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

    def _grid(self, apps: list[model.App], card_cls, min_w: int) -> QWidget:
        w = QWidget()
        flow = FlowLayout(w, spacing=14, min_item_width=min_w)
        for app in apps:
            card = card_cls(app, app.name in self._busy, self._can_open(app.name))
            card.opened.connect(self._open_detail)
            card.action.connect(self._on_action)
            flow.addWidget(card)
        return w

    def _open_detail(self, name: str) -> None:
        app = self._find(name)
        if app is None:
            return
        self._detail.show_app(app, name in self._busy, self._can_open(name))
        self._stack.setCurrentIndex(1)

    def _find(self, name: str) -> model.App | None:
        return next((a for a in self._apps if a.name == name), None)

    def _update_status(self) -> None:
        live = not self._fetching and not self._offline and self._catalogue.source != "none"
        self._dot.setStyleSheet(
            "background: %s; border-radius: 3px;" % ("#f2f2f4" if live else "#4a4a4f"))
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
    def _can_open(self, name: str) -> bool:
        return any(local.exec_argv(d) for d in local.desktop_entries(name))

    def _on_action(self, action: str, name: str) -> None:
        if action == "open":
            self._launch(name)
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
        proc.finished.connect(lambda *_: (proc.deleteLater(), self._reload_timer.start()))
        proc.errorOccurred.connect(lambda *_: self._reload_timer.start())
        proc.start()
        for n in packages or ["__upgrade__"]:
            self._busy[n] = proc
        self._render()
