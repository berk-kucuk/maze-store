"""Entry point. Single instance per user, like the other Maze apps."""
from __future__ import annotations

import os
import sys

from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication

from mazestore.gui.i18n import set_language
from mazestore.gui.icons import app_logo
from mazestore.gui.theme import stylesheet
from mazestore.gui.window import MainWindow

_RUNTIME_DIR = os.environ.get("XDG_RUNTIME_DIR", "")
_SINGLETON = (os.path.join(_RUNTIME_DIR, "maze-store-singleton")
              if _RUNTIME_DIR and os.path.isdir(_RUNTIME_DIR)
              else f"maze-store-singleton-{os.getuid()}")


def _requested_view(argv: list[str]) -> str:
    for arg in argv:
        if arg.startswith("--view="):
            return arg.split("=", 1)[1]
    return ""


def _activate_running_instance(view: str) -> bool:
    sock = QLocalSocket()
    sock.connectToServer(_SINGLETON)
    if sock.waitForConnected(300):
        # Only a known view name is ever sent; the receiver checks it again.
        sock.write(b"show" + (b" " + view.encode() if view.isalpha() else b""))
        sock.flush()
        sock.waitForBytesWritten(300)
        sock.disconnectFromServer()
        return True
    return False


def run() -> int:
    if os.geteuid() == 0:
        # The whole design is that the store has no privileges and sudo asks in
        # a terminal. Running it as root would silently throw that away.
        print("maze-store: do not run as root — it asks for your password when needed.",
              file=sys.stderr)
        return 1
    for arg in sys.argv[1:]:
        if arg.startswith("--lang="):
            set_language(arg.split("=", 1)[1])

    app = QApplication(sys.argv)
    app.setApplicationName("Maze Store")
    app.setApplicationDisplayName("Maze Store")
    app.setOrganizationName("maze")
    app.setDesktopFileName("maze-store")
    app.setWindowIcon(app_logo())

    view = _requested_view(sys.argv[1:])
    if _activate_running_instance(view):
        return 0
    QLocalServer.removeServer(_SINGLETON)
    singleton = QLocalServer()
    singleton.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
    singleton.listen(_SINGLETON)

    app.setStyleSheet(stylesheet())
    window = MainWindow()

    def _raise() -> None:
        conn = singleton.nextPendingConnection()
        if conn is not None:
            conn.waitForReadyRead(200)
            msg = bytes(conn.readAll()).decode("ascii", "ignore").split()
            if len(msg) == 2 and msg[0] == "show":
                window.set_view(msg[1])
            conn.disconnectFromServer()
        window.showNormal()
        window.raise_()
        window.activateWindow()
    singleton.newConnection.connect(_raise)

    if view:
        window.set_view(view)
    window.show()
    return app.exec()
